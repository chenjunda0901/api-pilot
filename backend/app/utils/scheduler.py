import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, delete
from datetime import UTC

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler()

# 回收站保留天数
RECYCLE_RETENTION_DAYS = 30
# 到期预警天数（提前 N 天通知）
RECYCLE_WARN_DAYS = 3


async def init_scheduler():
    if not scheduler.running:
        from app.database import async_session_factory
        async with async_session_factory() as db:
            from app.models.test_scene import TestScene
            result = await db.execute(
                select(TestScene).where(TestScene.schedule_enabled == 1))
            scenes = result.scalars().all()
            for scene in scenes:
                if scene.schedule_cron:
                    try:
                        scheduler.add_job(
                            _run_scheduled_scene,
                            CronTrigger.from_crontab(scene.schedule_cron),
                            args=[scene.id, scene.env_id],
                            id=f"scene_{scene.id}",
                            replace_existing=True,
                            misfire_grace_time=300,
                        )
                        logger.info(f"Scheduled scene {scene.id}: {scene.schedule_cron}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to schedule scene {scene.id}: {e}")

        from app.config import settings
        scheduler.add_job(
            _clean_old_reports,
            CronTrigger.from_crontab("0 3 * * *"),
            args=[settings.REPORT_RETENTION_DAYS],
            id="clean_old_reports",
            replace_existing=True,
        )
        logger.info("Report cleanup job scheduled (daily at 3am)")

        # 每天凌晨 3:15 清理过期的 RevokedToken 记录
        scheduler.add_job(
            _cleanup_expired_tokens,
            CronTrigger.from_crontab("15 3 * * *"),
            id="cleanup_expired_tokens",
            replace_existing=True,
        )
        logger.info("Token cleanup job scheduled (daily at 3:15am)")

        # 每天凌晨 3:30 清理回收站（软删除超过 30 天的资源永久删除）
        scheduler.add_job(
            _cleanup_recycle_bin,
            CronTrigger.from_crontab("30 3 * * *"),
            id="cleanup_recycle_bin",
            replace_existing=True,
        )
        logger.info("Recycle bin cleanup job scheduled (daily at 3:30am)")

        # 每天凌晨 3:20 发送回收站到期预警通知
        scheduler.add_job(
            _notify_expiring_resources,
            CronTrigger.from_crontab("20 3 * * *"),
            id="notify_expiring_resources",
            replace_existing=True,
        )
        logger.info("Recycle bin expiry notification job scheduled (daily at 3:20am)")

        scheduler.start()


async def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shutdown")


async def _run_scheduled_scene(scene_id: int, env_id: int):
    from app.database import async_session_factory
    async with async_session_factory() as db:
        from app.services.executor.linear_executor import LinearExecutor
        engine = LinearExecutor(db)
        try:
            report_id = await engine.execute(scene_id, env_id or 1, 1)
            logger.info(f"Scheduled scene {scene_id} completed, report #{report_id}")
        except (ValueError, RuntimeError) as e:
            logger.error(f"Scheduled scene {scene_id} failed: {e}")


async def _clean_old_reports(days: int):
    from app.database import async_session_factory
    async with async_session_factory() as db:
        from app.services.report_service import ReportService
        await ReportService(db).clean_old(days)


async def _cleanup_expired_tokens():
    """
    清理超过 7 天的 RevokedToken 记录。
    RevokedToken 模型有 revoked_at 字段，用于判断过期时间。
    """
    from datetime import datetime, timedelta
    from app.database import async_session_factory
    from app.models.revoked_token import RevokedToken
    from sqlalchemy import delete

    async with async_session_factory() as session:
        cutoff = datetime.now(UTC) - timedelta(days=7)
        result = await session.execute(
            delete(RevokedToken).where(RevokedToken.revoked_at < cutoff)
        )
        await session.commit()
        logger.info(f"Cleaned up {result.rowcount} expired revoked tokens")


async def add_scene_job(scene_id: int, cron: str, env_id: int | None = None) -> None:
    """添加或更新场景的定时任务（运行时动态同步）"""
    if not scheduler.running:
        logger.warning("Scheduler 未运行，无法添加定时任务")
        return
    try:
        trigger = CronTrigger.from_crontab(cron)
        scheduler.add_job(
            _run_scheduled_scene,
            trigger,
            args=[scene_id, env_id or 1],
            id=f"scene_{scene_id}",
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info(f"场景 {scene_id} 定时任务已更新: {cron}")
    except (ValueError, TypeError) as e:
        logger.error(f"更新 scene {scene_id} 定时任务失败: {e}")


async def remove_scene_job(scene_id: int) -> None:
    """移除场景的定时任务（运行时动态同步）"""
    if not scheduler.running:
        return
    job_id = f"scene_{scene_id}"
    job = scheduler.get_job(job_id)
    if job:
        scheduler.remove_job(job_id)
        logger.info(f"已移除场景 {scene_id} 的定时任务")


async def sync_scene_schedule(scene_id: int, cron: str, enabled: bool, env_id: int | None = None) -> None:
    """统一的定时任务同步入口，根据 enabled 和 cron 决定 add 或 remove"""
    if enabled and cron:
        await add_scene_job(scene_id, cron, env_id)
    else:
        await remove_scene_job(scene_id)


async def _cleanup_recycle_bin():
    """永久删除软删除超过 30 天的资源。

    涉及模型：ApiDefinition、TestScene、TestCase。
    """
    from datetime import datetime, timedelta
    from app.database import async_session_factory
    from app.models.api_definition import ApiDefinition
    from app.models.test_scene import TestScene
    from app.models.test_case import TestCase

    cutoff = datetime.now(UTC) - timedelta(days=RECYCLE_RETENTION_DAYS)

    async with async_session_factory() as session:
        total = 0
        for model, label in [
            (ApiDefinition, "接口"),
            (TestScene, "场景"),
            (TestCase, "用例"),
        ]:
            result = await session.execute(
                delete(model).where(model.deleted_at.isnot(None), model.deleted_at < cutoff)
            )
            count = result.rowcount
            total += count
            if count:
                logger.info(f"Recycle bin: permanently deleted {count} {label}(s)")
        await session.commit()
        if total:
            logger.info(f"Recycle bin cleanup completed: {total} resources permanently deleted")
        else:
            logger.info("Recycle bin cleanup: no expired resources found")


async def _notify_expiring_resources():
    """查找即将在 3 天后过期的软删除资源，通知项目成员。

    通知通过 Notification 模型写入，由 SSE 推送给用户。
    """
    from datetime import datetime, timedelta
    from app.database import async_session_factory
    from app.models.api_definition import ApiDefinition
    from app.models.test_scene import TestScene
    from app.models.test_case import TestCase
    from app.models.project_member import ProjectMember
    from app.models.notification import Notification

    now = datetime.now(UTC)
    warn_start = now + timedelta(days=RECYCLE_RETENTION_DAYS - RECYCLE_WARN_DAYS)
    warn_end = now + timedelta(days=RECYCLE_RETENTION_DAYS)

    async with async_session_factory() as session:
        # 收集即将过期的资源，按 project_id 分组
        expiring_by_project: dict[int, list[str]] = {}

        for model, label in [
            (ApiDefinition, "接口"),
            (TestScene, "场景"),
            (TestCase, "用例"),
        ]:
            result = await session.execute(
                select(model).where(
                    model.deleted_at.isnot(None),
                    model.deleted_at >= warn_start,
                    model.deleted_at < warn_end,
                )
            )
            for obj in result.scalars().all():
                project_id = obj.project_id
                name = getattr(obj, "name", f"#{obj.id}")
                expiring_by_project.setdefault(project_id, []).append(
                    f"{label}「{name}」"
                )

        if not expiring_by_project:
            logger.info("Recycle bin expiry notification: no resources expiring soon")
            return

        # 为每个项目的成员创建通知
        for project_id, items in expiring_by_project.items():
            # 查询项目成员
            members = await session.execute(
                select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)
            )
            user_ids = [row[0] for row in members.all()]
            if not user_ids:
                continue

            item_text = "、".join(items[:10])
            if len(items) > 10:
                item_text += f" 等 {len(items)} 项"
            title = "回收站资源即将永久删除"
            content = f"以下资源将在 {RECYCLE_WARN_DAYS} 天后被永久删除：{item_text}。如需恢复，请及时操作。"

            for uid in user_ids:
                session.add(Notification(
                    user_id=uid,
                    type="system",
                    title=title,
                    content=content,
                    link=f"/projects/{project_id}",
                ))

        await session.commit()
        logger.info(
            f"Recycle bin expiry notification: notified for {len(expiring_by_project)} project(s), "
            f"{sum(len(v) for v in expiring_by_project.values())} resource(s) expiring"
        )
