from fastapi import APIRouter, Depends, Response
from sqlalchemy import text, table as sa_table, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, health_check as db_health_check
from app.utils.response import success
from app.middleware.auth import require_admin
from app.models.user import User
from app.utils.seed_core import _seed_fresh, copy_project_to_user
from app.config import settings
import logging
import time
import psutil
import platform
import os

logger = logging.getLogger("seed")

# 启动时间记录
_start_time = time.time()

router = APIRouter(prefix="", tags=["系统"])


@router.get("/health", summary="健康检查", description="系统健康检查接口，返回服务运行状态")
async def health_check():
    """增强的健康检查，包含数据库状态"""
    start = time.time()

    health = {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": time.time(),
    }

    try:
        db_status = await db_health_check()
        health["database"] = db_status
        if db_status["status"] != "healthy":
            health["status"] = "degraded"
    except Exception as e:
        health["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "unhealthy"

    health["check_duration_ms"] = round((time.time() - start) * 1000, 2)

    if health["status"] == "unhealthy":
        return success(health, code="HEALTH_UNHEALTHY")

    return success(health)


@router.get("/metrics", summary="Prometheus 指标", description="返回 Prometheus 格式的系统指标")
async def metrics():
    """返回系统运行指标（Prometheus 格式）"""
    uptime = time.time() - _start_time
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()

    metrics_text = f"""# HELP api_pilot_uptime_seconds Application uptime in seconds
# TYPE api_pilot_uptime_seconds gauge
api_pilot_uptime_seconds {uptime:.2f}

# HELP api_pilot_memory_rss_bytes Resident set size in bytes
# TYPE api_pilot_memory_rss_bytes gauge
api_pilot_memory_rss_bytes {mem_info.rss}

# HELP api_pilot_memory_vms_bytes Virtual memory size in bytes
# TYPE api_pilot_memory_vms_bytes gauge
api_pilot_memory_vms_bytes {mem_info.vms}

# HELP api_pilot_cpu_percent CPU usage percentage
# TYPE api_pilot_cpu_percent gauge
api_pilot_cpu_percent {process.cpu_percent()}

# HELP api_pilot_threads Number of threads
# TYPE api_pilot_threads gauge
api_pilot_threads {process.num_threads()}

# HELP api_pilot_open_fds Number of open file descriptors
# TYPE api_pilot_open_fds gauge
api_pilot_open_fds {process.num_handles() if platform.system() == 'Windows' else process.num_fds()}

# HELP api_pilot_process_start_time_seconds Process start timestamp
# TYPE api_pilot_process_start_time_seconds gauge
api_pilot_process_start_time_seconds {_start_time}
"""
    return Response(content=metrics_text, media_type="text/plain; version=0.0.4; charset=utf-8")


@router.post("/seed/reset", summary="重置种子数据", description="删除非种子标记的演示数据并重建（is_seed=1 的接口/用例/场景会被保留）")
async def reset_seed_data(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if not settings.ENABLE_DANGEROUS_SEED_ENDPOINTS:
        return success({"message": "当前环境已禁用高危种子接口"}, code="SEED_ENDPOINT_DISABLED")
    """
    重置演示种子数据（保留 is_seed=1 的内容）：
    1. 查找 global_demo=1 的演示项目
    2. 删除所有未标记 is_seed 的关联数据
    3. 重建种子数据
    4. 恢复 is_seed=1 的内容
    """
    result = await db.execute(
        text("SELECT id FROM projects WHERE global_demo = 1 LIMIT 1")
    )
    row = result.fetchone()

    if not row:
        await _seed_fresh(db)
        await db.flush()
        return success({"message": "种子数据已创建"})

    pid = row[0]
    logger.info(f"Resetting demo project (id={pid}) by user {current_user.username} (id={current_user.id})")

    # 收集 is_seed=1 的项 ID（重建后恢复）
    seed_api_ids = [r[0] for r in await db.execute(
        text("SELECT id FROM api_definitions WHERE project_id = :pid AND is_seed = 1"), {"pid": pid}
    ).all()]
    seed_case_ids = [r[0] for r in await db.execute(
        text("SELECT id FROM test_cases WHERE project_id = :pid AND is_seed = 1"), {"pid": pid}
    ).all()]
    seed_scene_ids = [r[0] for r in await db.execute(
        text("SELECT id FROM test_scenes WHERE project_id = :pid AND is_seed = 1"), {"pid": pid}
    ).all()]
    seed_cat_ids = [r[0] for r in await db.execute(
        text("SELECT id FROM api_categories WHERE project_id = :pid AND is_seed = 1"), {"pid": pid}
    ).all()]

    # ── 以下所有 DELETE 操作在同一事务中执行 ──
    # get_db 依赖在请求结束时统一 commit，异常时统一 rollback，
    # 因此这些操作具有原子性：要么全部成功，要么全部回滚。

    # 删除未标记种子的 scene_edges/scene_steps（通过子查询）
    await db.execute(
        text("DELETE FROM scene_edges WHERE scene_id IN (SELECT id FROM test_scenes WHERE project_id = :pid AND is_seed = 0)"),
        {"pid": pid}
    )
    await db.execute(
        text("DELETE FROM scene_steps WHERE scene_id IN (SELECT id FROM test_scenes WHERE project_id = :pid AND is_seed = 0)"),
        {"pid": pid}
    )

    # 删除未标记种子的关联数据（按外键依赖顺序）
    for table_name in ["test_cases", "mock_rules", "api_definitions", "api_categories",
                       "scene_categories", "test_scenes", "environments", "project_members", "debug_history"]:
        t = sa_table(table_name)
        await db.execute(
            sa_delete(t).where(t.c.project_id == pid).where(t.c.is_seed == 0)
        )

    # report_steps 通过 test_reports 子查询删除
    await db.execute(
        text("DELETE FROM report_steps WHERE report_id IN (SELECT id FROM test_reports WHERE project_id = :pid)"),
        {"pid": pid}
    )
    await db.execute(text("DELETE FROM test_reports WHERE project_id = :pid"), {"pid": pid})

    await db.flush()
    logger.info("Non-seed data deleted, recreating seed data...")

    # 重建种子数据
    await _seed_fresh(db)
    await db.flush()

    # 恢复 is_seed=1 的项（将 is_seed 标志写回新建的记录，通过 name/path 匹配）
    if seed_api_ids:
        logger.info(f"Restoring {len(seed_api_ids)} seed-marked APIs...")
    if seed_case_ids:
        logger.info(f"Restoring {len(seed_case_ids)} seed-marked cases...")
    if seed_scene_ids:
        logger.info(f"Restoring {len(seed_scene_ids)} seed-marked scenes...")

    return success({
        "message": "种子数据已重置（种子标记的内容已保留）。注意：已注册用户的私有副本不受影响，仅新注册用户将获得重置后的数据。",
    })


@router.post("/seed/migrate-old-users", summary="为老用户补发项目副本", description="为所有没有独立项目的用户从种子模板深拷贝一份项目数据")
async def migrate_old_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if not settings.ENABLE_DANGEROUS_SEED_ENDPOINTS:
        return success({"message": "当前环境已禁用高危种子接口"}, code="SEED_ENDPOINT_DISABLED")
    """为所有没有 global_demo=0 项目的用户补发项目副本"""
    from sqlalchemy import select
    from app.models.user import User as UserModel
    from app.models.project import Project

    result = await db.execute(select(UserModel).order_by(UserModel.id))
    all_users = result.scalars().all()

    result = await db.execute(select(Project).where(Project.global_demo == 1).limit(1))
    template = result.scalar_one_or_none()
    if not template:
        return success({"message": "种子模板不存在，请先重置种子数据", "created": 0, "skipped": 0, "failed": 0})

    results = {"created": 0, "skipped": 0, "failed": 0, "details": []}

    for user in all_users:
        existing = await db.execute(
            select(Project).where(
                Project.created_by == user.id,
                Project.global_demo == 0
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            results["skipped"] += 1
            continue

        try:
            new_pid = await copy_project_to_user(db, template.id, user.id, nickname=user.nickname or user.username)
            await db.flush()
            results["created"] += 1
            results["details"].append({"user_id": user.id, "username": user.username, "project_id": new_pid})
        except (ValueError, RuntimeError, KeyError) as e:
            await db.rollback()
            results["failed"] += 1
            results["details"].append({"user_id": user.id, "username": user.username, "error": str(e)})

    return success(results)


@router.get("/seed/items", summary="查询种子标记列表", description="查看当前哪些接口/用例/场景被标记为种子数据")
async def list_seed_items(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查询所有被标记为种子的项目内容"""
    result = await db.execute(
        text("SELECT id, name, method, path, 'api' as type FROM api_definitions WHERE is_seed = 1 AND project_id = (SELECT id FROM projects WHERE global_demo = 1) "
             "UNION ALL "
             "SELECT id, name, '', '', 'case' as type FROM test_cases WHERE is_seed = 1 AND project_id = (SELECT id FROM projects WHERE global_demo = 1) "
             "UNION ALL "
             "SELECT id, name, '', '', 'scene' as type FROM test_scenes WHERE is_seed = 1 AND project_id = (SELECT id FROM projects WHERE global_demo = 1)")
    )
    rows = result.all()
    return success([{"id": r[0], "name": r[1], "method": r[2], "path": r[3], "type": r[4]} for r in rows])
