"""APScheduler 异步集成。

提供 ``SchedulerService`` —— 基于 ``apscheduler[asyncio]`` 的 ``AsyncIOScheduler``
薄封装，承担测试计划的定时触发与立即触发。

典型用法::

    scheduler = SchedulerService()
    await scheduler.start()
    await scheduler.add_job(
        schedule_id=1,
        cron="0 2 * * *",
        timezone="Asia/Shanghai",
        func=run_plan_callback,
        args=(plan_id,),
    )
    # 立即执行（CI 触发）
    await scheduler.trigger_now(1)
    await scheduler.shutdown()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Any
from collections.abc import Awaitable, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

if TYPE_CHECKING:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("service.scheduler")


# ── 异常 ────────────────────────────────────────────────────────────────


class SchedulerError(Exception):
    """调度器错误基类。"""


class InvalidCronError(SchedulerError):
    """cron 表达式不合法。"""


class InvalidTimezoneError(SchedulerError):
    """时区标识不合法。"""


class JobNotFoundError(SchedulerError):
    """调度作业不存在。"""


# ── 数据结构 ────────────────────────────────────────────────────────────


@dataclass
class JobInfo:
    """调度作业的可序列化描述。"""

    id: str
    schedule_id: int
    name: str
    cron: str
    timezone: str
    next_run: str | None = None
    pending: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


# ── 服务实现 ────────────────────────────────────────────────────────────


class SchedulerService:
    """APScheduler 异步服务（单例友好）。

    设计要点：
      - 内部仅持有一个 ``AsyncIOScheduler``，由调用方决定何时 ``start`` / ``shutdown``
      - 作业 ID 以 ``"schedule-{schedule_id}"`` 命名，确保幂等新增
      - 时区解析使用 ``zoneinfo``（Python 3.9+ 标准库），无需 pytz
    """

    JOB_ID_PREFIX = "schedule-"

    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None
        self._started: bool = False

    # ── 生命周期 ────────────────────────────────────────────────

    async def start(self) -> None:
        """启动调度器（幂等）。"""
        if self._started:
            return
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
        except ImportError as exc:
            raise SchedulerError(
                "未安装 apscheduler，请执行 `pip install apscheduler[asyncio]`"
            ) from exc

        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._scheduler.start()
        self._started = True
        logger.info("Scheduler started")

    async def shutdown(self, wait: bool = True) -> None:
        """关闭调度器。"""
        if not self._started or self._scheduler is None:
            return
        try:
            self._scheduler.shutdown(wait=wait)
        except Exception as exc:  # noqa: BLE001 —— 关闭阶段尽量吞错
            logger.warning("Scheduler shutdown error: %s", exc)
        finally:
            self._started = False
            self._scheduler = None
            logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        """调度器是否处于运行状态。"""
        return self._started and self._scheduler is not None

    # ── 作业管理 ────────────────────────────────────────────────

    def _job_id(self, schedule_id: int) -> str:
        return f"{self.JOB_ID_PREFIX}{schedule_id}"

    def _validate(self, cron: str, timezone: str) -> tuple[Any, ZoneInfo]:
        """校验 cron + 时区，返回 ``(trigger, tz)``。"""
        if not cron or not isinstance(cron, str):
            raise InvalidCronError("cron 表达式不能为空")
        try:
            from apscheduler.triggers.cron import CronTrigger

            trigger = CronTrigger.from_crontab(cron)
        except Exception as exc:
            raise InvalidCronError(f"cron 表达式不合法: {cron}") from exc

        try:
            tz = ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise InvalidTimezoneError(f"时区标识不存在: {timezone}") from exc

        # 触发器套上时区
        try:
            trigger = CronTrigger.from_crontab(cron, timezone=tz)
        except Exception as exc:
            raise SchedulerError(f"cron 与时区组合失败: {exc}") from exc
        return trigger, tz

    def add_job(
        self,
        schedule_id: int,
        cron: str,
        timezone: str,
        func: Callable[..., Awaitable[Any]],
        args: tuple[Any, ...] = (),
        name: str | None = None,
        replace_existing: bool = True,
    ) -> str:
        """注册 cron 作业。

        参数：
            schedule_id: 业务侧调度 ID（与数据库 ``schedules.id`` 对齐）
            cron: 标准 5 段 cron 表达式
            timezone: IANA 时区名（如 ``Asia/Shanghai``）
            func: 异步可调用对象
            args: 传给 ``func`` 的位置参数
            name: 可读名
            replace_existing: 已存在时是否覆盖
        """
        if not self._started or self._scheduler is None:
            raise SchedulerError("调度器未启动，请先调用 start()")
        if not callable(func):
            raise SchedulerError("func 必须是可调用对象")

        trigger, _tz = self._validate(cron, timezone)
        job_id = self._job_id(schedule_id)

        try:
            job = self._scheduler.add_job(
                func,
                trigger=trigger,
                args=args,
                id=job_id,
                name=name or job_id,
                replace_existing=replace_existing,
                misfire_grace_time=60,
            )
        except Exception as exc:
            raise SchedulerError(f"添加作业失败: {exc}") from exc

        logger.info("Job %s added (cron=%s tz=%s)", job_id, cron, timezone)
        return job.id

    def remove_job(self, schedule_id: int) -> None:
        """移除 cron 作业；不存在时抛 ``JobNotFoundError``。"""
        if not self._started or self._scheduler is None:
            raise SchedulerError("调度器未启动")
        job_id = self._job_id(schedule_id)
        job = self._scheduler.get_job(job_id)
        if job is None:
            raise JobNotFoundError(f"作业 {job_id} 不存在")
        try:
            self._scheduler.remove_job(job_id)
        except Exception as exc:
            raise SchedulerError(f"移除作业失败: {exc}") from exc
        logger.info("Job %s removed", job_id)

    def list_jobs(self) -> list[JobInfo]:
        """列出当前已注册的所有作业。"""
        if not self._started or self._scheduler is None:
            return []
        out: list[JobInfo] = []
        for job in self._scheduler.get_jobs():
            try:
                schedule_id = int(job.id.removeprefix(self.JOB_ID_PREFIX))
            except ValueError:
                schedule_id = -1
            trigger = job.trigger
            cron_str = ""
            try:
                cron_str = str(trigger)
            except Exception:  # noqa: BLE001
                cron_str = ""
            out.append(
                JobInfo(
                    id=job.id,
                    schedule_id=schedule_id,
                    name=job.name or job.id,
                    cron=cron_str,
                    timezone=str(getattr(trigger, "timezone", "") or "UTC"),
                    next_run=job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                    pending=bool(getattr(job, "pending", False)),
                )
            )
        return out

    async def trigger_now(self, schedule_id: int) -> None:
        """立即触发某个 schedule（CI 触发场景）。"""
        if not self._started or self._scheduler is None:
            raise SchedulerError("调度器未启动")
        job_id = self._job_id(schedule_id)
        job = self._scheduler.get_job(job_id)
        if job is None:
            raise JobNotFoundError(f"作业 {job_id} 不存在")
        try:
            # 使用 reschedule_job 把下次执行时间设为立即
            self._scheduler.reschedule_job(
                job_id,
                trigger=job.trigger,
                next_run_time=datetime.now(UTC),
            )
        except Exception as exc:
            logger.exception("reschedule_job 失败，尝试直接执行 func: %s", exc)
            # 退化方案：直接拿到 func 异步执行
            func = job.func
            args = job.args or ()
            kwargs = job.kwargs or {}
            try:
                await func(*args, **kwargs)
            except Exception as exc2:  # noqa: BLE001
                logger.exception("Manual trigger %s fallback failed: %s", job_id, exc2)
                raise
        logger.info("Job %s triggered manually", job_id)

    # ── 内部工具 ────────────────────────────────────────────────

    def get_scheduler(self) -> Any:
        """返回底层 APScheduler 实例（谨慎使用）。"""
        return self._scheduler
