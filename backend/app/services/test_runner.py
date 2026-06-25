"""并发测试执行器。

封装 ``asyncio.Semaphore`` 控制并发，遍历 ``ApiTestPlanStep``，调度 ``SceneStep``
请求并收集 ``ReportStep``，最终汇总为 ``TestReport``。

设计原则：
  - 不依赖 FastAPI Request
  - 不直接执行 HTTP 调用（委托给现有 ``executor.linear_executor.LinearExecutor``）
  - 支持 ``failure_strategy`` = ``stop_all`` / ``continue``
  - 完成后调用 notifier 派发
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory

logger = logging.getLogger("service.test_runner")


# ── 数据结构 ────────────────────────────────────────────────────────────


@dataclass
class StepResult:
    """单个步骤执行结果。"""

    step_id: int
    sort_order: int
    status: str = "pending"  # pending / passed / failed / skipped
    duration_ms: float = 0.0
    status_code: int = 0
    error_message: str = ""
    response_excerpt: str = ""
    assertions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TestReport:
    """整份计划的执行报告。"""

    report_id: int | None
    plan_id: int
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"  # running / passed / failed / cancelled
    total_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    skip_count: int = 0
    duration_ms: float = 0.0
    step_results: list[StepResult] = field(default_factory=list)


# ── 异常 ────────────────────────────────────────────────────────────────


class TestRunnerError(Exception):
    """执行器错误。"""


class PlanNotFoundError(TestRunnerError):
    """计划不存在。"""


# ── 服务实现 ────────────────────────────────────────────────────────────


class TestRunner:
    """并发测试执行器。

    使用::

        runner = TestRunner(concurrency=4)
        report = await runner.run_plan(plan_id=12, db=db)
    """

    def __init__(
        self,
        concurrency: int = 4,
        timeout_seconds: int = 30,
        step_executor: Callable[[int, AsyncSession], Awaitable[StepResult]] | None = None,
    ) -> None:
        if concurrency < 1:
            raise TestRunnerError("concurrency 必须 >= 1")
        if timeout_seconds < 1:
            raise TestRunnerError("timeout_seconds 必须 >= 1")
        self.concurrency = concurrency
        self.timeout_seconds = timeout_seconds
        # 默认 step 执行器为线性 executor（延迟导入避免循环依赖）
        self._step_executor = step_executor
        self._semaphore: asyncio.Semaphore | None = None

    # ── 公共方法 ────────────────────────────────────────────────

    async def run_plan(self, plan_id: int, db: AsyncSession) -> TestReport:
        """执行整个测试计划，返回 ``TestReport``。"""
        from app.models.api_test_plan import ApiTestPlan, ApiTestPlanStep

        plan = await db.get(ApiTestPlan, plan_id)
        if plan is None:
            raise PlanNotFoundError(f"计划 {plan_id} 不存在")

        # 取所有启用步骤
        steps_q = await db.execute(
            select(ApiTestPlanStep)
            .where(ApiTestPlanStep.plan_id == plan_id, ApiTestPlanStep.enabled == 1)  # type: ignore[arg-type]
            .order_by(ApiTestPlanStep.order_index)
        )
        plan_steps = steps_q.scalars().all()
        if not plan_steps:
            return TestReport(
                report_id=None,
                plan_id=plan_id,
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                status="passed",
                duration_ms=0.0,
            )

        # 更新并发（允许运行时调整）
        self.concurrency = max(1, plan.concurrency or self.concurrency)
        self.timeout_seconds = plan.timeout_seconds or self.timeout_seconds
        self._semaphore = asyncio.Semaphore(self.concurrency)

        # 创建 report 行
        from app.models.test_report import TestReport as ReportModel

        report_row = ReportModel(
            project_id=plan.project_id,
            status="running",
            total_count=len(plan_steps),
            pass_count=0,
            fail_count=0,
            skip_count=0,
            duration=0.0,
        )
        db.add(report_row)
        await db.flush()
        await db.refresh(report_row)

        report = TestReport(
            report_id=report_row.id,
            plan_id=plan_id,
            started_at=datetime.now(UTC),
            total_count=len(plan_steps),
        )

        # 执行步骤
        step_tasks = [self._run_step_safe(ps, db, report) for ps in plan_steps]
        tasks = [asyncio.create_task(t) for t in step_tasks]
        try:
            # 阶段 4：用 plan.timeout_seconds 包裹整次执行（WebSocket/调度器场景）
            await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Plan %s 整体执行超时（>%ss）", plan_id, self.timeout_seconds,
            )
            # 取消所有尚未完成的任务
            for t in tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            report.status = "failed"
        except Exception as exc:
            logger.exception("Plan %s execution crashed: %s", plan_id, exc)
            report.status = "failed"

        # 汇总
        report.finished_at = datetime.now(UTC)
        report.duration_ms = (report.finished_at - report.started_at).total_seconds() * 1000
        if report.status != "failed":
            report.status = "passed" if report.fail_count == 0 else "failed"
        report_row.status = report.status
        report_row.pass_count = report.pass_count
        report_row.fail_count = report.fail_count
        report_row.skip_count = report.skip_count
        report_row.duration = report.duration_ms
        await db.flush()

        # 阶段 4：性能基线告警 + 指标记录
        await self._record_metrics_and_alert(plan, report, db)

        # 通知（失败不阻塞）
        await self._notify_safely(report, db)
        return report

    async def run_step(
        self,
        plan_step_id: int,
        db: AsyncSession,
    ) -> StepResult:
        """单独跑一个 plan_step。"""
        from app.models.api_test_plan import ApiTestPlanStep

        ps = await db.get(ApiTestPlanStep, plan_step_id)
        if ps is None:
            raise TestRunnerError(f"plan_step {plan_step_id} 不存在")
        report = TestReport(
            report_id=None,
            plan_id=ps.plan_id,
            started_at=datetime.now(UTC),
        )
        result = await self._run_step_inner(ps, db, report)
        report.step_results = [result]
        return result

    # ── 内部 ────────────────────────────────────────────────────

    async def _run_step_safe(
        self,
        plan_step: Any,
        db: AsyncSession,
        report: TestReport,
    ) -> StepResult:
        """带信号量与超时的步骤包装，使用独立 db session 隔离并发访问。"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.concurrency)
        async with self._semaphore:
            # 为每个并发步骤创建独立的 db session，避免共享 session 的并发问题
            async with async_session_factory() as step_db:
                try:
                    result = await asyncio.wait_for(
                        self._run_step_inner(plan_step, step_db, report),
                        timeout=self.timeout_seconds,
                    )
                    await step_db.commit()
                    return result
                except asyncio.TimeoutError:
                    result = StepResult(
                        step_id=plan_step.step_id,
                        sort_order=plan_step.order_index,
                        status="failed",
                        error_message=f"步骤执行超时（>{self.timeout_seconds}s）",
                    )
                    self._record_step(report, result)
                    if self._should_stop(report):
                        # 仅在 stop_all 时升格
                        report.status = "failed"
                    return result
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Step %s crashed: %s", plan_step.id, exc)
                    result = StepResult(
                        step_id=plan_step.step_id,
                        sort_order=plan_step.order_index,
                        status="failed",
                        error_message=str(exc),
                    )
                    self._record_step(report, result)
                    return result

    async def _run_step_inner(
        self,
        plan_step: Any,
        db: AsyncSession,
        report: TestReport,
    ) -> StepResult:
        """执行单个步骤（委托给注入的 step_executor）。"""
        from app.models.api_test_plan import ApiTestPlan

        plan = await db.get(ApiTestPlan, plan_step.plan_id)
        failure_strategy = (plan.failure_strategy if plan else "continue") or "continue"

        started = time.perf_counter()
        result = StepResult(
            step_id=plan_step.step_id,
            sort_order=plan_step.order_index,
        )

        try:
            if self._step_executor is not None:
                result = await self._step_executor(plan_step.id, db)
                result.step_id = plan_step.step_id
                result.sort_order = plan_step.order_index
            else:
                result = await self._default_step_executor(plan_step, db)
        except Exception as exc:  # noqa: BLE001
            result.status = "failed"
            result.error_message = str(exc)

        result.duration_ms = (time.perf_counter() - started) * 1000
        self._record_step(report, result)

        # 失败策略
        if result.status == "failed" and failure_strategy == "stop_all":
            # 通过抛异常让 gather 取消其他任务
            logger.info("Plan %s hits stop_all, aborting", plan_step.plan_id)
            raise TestRunnerError("stop_all triggered")
        return result

    async def _default_step_executor(
        self,
        plan_step: Any,
        db: AsyncSession,
    ) -> StepResult:
        """默认 step 执行器：调用现有 linear_executor 跑场景。"""
        from app.services.executor.linear_executor import LinearExecutor

        from app.models.test_scene import TestScene
        from app.models.environment import Environment
        from app.models.report_step import ReportStep
        from app.models.api_test_plan import ApiTestPlan

        result = StepResult(
            step_id=plan_step.step_id,
            sort_order=plan_step.order_index,
        )
        if plan_step.step_type == "scene":
            scene = await db.get(TestScene, plan_step.step_id)
            if scene is None:
                result.status = "failed"
                result.error_message = "关联场景不存在"
                return result

            # 确定执行环境：取项目默认环境，无默认则取第一个环境
            env_q = await db.execute(
                select(Environment)
                .where(
                    Environment.project_id == scene.project_id,
                    Environment.is_default.is_(True),
                )
                .limit(1)
            )
            env = env_q.scalar_one_or_none()
            if env is None:
                env_q = await db.execute(
                    select(Environment)
                    .where(Environment.project_id == scene.project_id)
                    .order_by(Environment.id)
                    .limit(1)
                )
                env = env_q.scalar_one_or_none()
            if env is None:
                result.status = "failed"
                result.error_message = "项目下无可用环境"
                return result

            # 确定执行者：取计划创建者
            plan = await db.get(ApiTestPlan, plan_step.plan_id)
            user_id = plan.created_by or 0

            executor = LinearExecutor(db)
            try:
                report_id = await executor.execute(
                    scene_id=scene.id,
                    env_id=env.id,
                    user_id=user_id,
                )
                # 查询报告步骤判断执行结果
                steps_q = await db.execute(
                    select(ReportStep).where(
                        ReportStep.report_id == report_id,
                    )
                )
                report_steps = steps_q.scalars().all()
                if not report_steps:
                    result.status = "passed"
                else:
                    failed_steps = [s for s in report_steps if s.status != "passed"]
                    result.status = "failed" if failed_steps else "passed"
                    if failed_steps:
                        result.error_message = failed_steps[0].error or "步骤失败"
            except Exception as exc:  # noqa: BLE001
                result.status = "failed"
                result.error_message = str(exc)
            finally:
                await executor.close()
        else:  # case 暂按 scene 之外做兜底标记
            result.status = "skipped"
            result.error_message = f"step_type={plan_step.step_type} 暂未支持"
        return result

    def _record_step(self, report: TestReport, result: StepResult) -> None:
        """记录步骤结果并维护计数。"""
        report.step_results.append(result)
        if result.status == "passed":
            report.pass_count += 1
        elif result.status == "failed":
            report.fail_count += 1
        else:
            report.skip_count += 1

    def _should_stop(self, report: TestReport) -> bool:
        return report.fail_count > 0 and any(
            r.status == "failed" for r in report.step_results
        )

    async def _notify_safely(self, report: TestReport, db: AsyncSession) -> None:
        """派发通知（失败不抛）。"""
        try:
            from app.services.notifier import NotifierDispatcher

            dispatcher = NotifierDispatcher(db)
            payload = {
                "event": "plan.run.completed" if report.status == "passed" else "plan.run.failed",
                "plan_id": report.plan_id,
                "report_id": report.report_id,
                "status": report.status,
                "pass_count": report.pass_count,
                "fail_count": report.fail_count,
                "skip_count": report.skip_count,
                "duration_ms": report.duration_ms,
            }
            # 默认派发到 webhooks 表，channel 派发由 dispatcher 内部决定
            await dispatcher.dispatch_event(payload, db)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Notify failed: %s", exc)

    async def _record_metrics_and_alert(
        self,
        plan: Any,
        report: TestReport,
        db: AsyncSession,
    ) -> None:
        """阶段 4：性能基线告警 + 指标记录。

        - 把 plan 维度的总耗时写入 ``metrics_snapshots``（scope=plan）
        - 调用 ``check_baseline_alert`` 校验 p95 是否超出阈值
        - 超出时写 ``notification_dispatches``（通过 NotifierDispatcher 派发）
        """
        try:
            from app.services.metrics import MetricsCollector

            collector = MetricsCollector(db)
            # 1. 写入 plan 维度指标
            await collector.record_duration(
                "plan", report.plan_id, report.duration_ms, plan.project_id,
            )

            # 2. 对每个被执行的 step 关联的 api 检查基线
            from app.models.test_scene import TestScene
            step_ids = [s.step_id for s in report.step_results if s.step_id]
            if not step_ids:
                return

            # 基线阈值（可后续从配置读取）
            threshold_ms = 1500.0
            # 只对 scene 类型 step 中的 api_id 做检查
            unique_api_ids: set[int] = set()
            for sid in step_ids:
                scene = await db.get(TestScene, sid)
                if scene and getattr(scene, "api_id", None):
                    unique_api_ids.add(int(scene.api_id))

            for api_id in unique_api_ids:
                alerts = await collector.check_baseline_alert(
                    api_id=api_id, threshold_ms=threshold_ms, days=1,
                )
                for alert in alerts:
                    logger.warning(
                        "性能基线告警: api=%d p95=%.1fms > %.1fms",
                        api_id, alert.current_ms, alert.threshold_ms,
                    )
                    # 写 notification_dispatches（best-effort）
                    try:
                        from app.services.notifier import NotifierDispatcher
                        dispatcher = NotifierDispatcher(db)
                        await dispatcher.dispatch_event(
                            {
                                "event": "metrics.baseline_alert",
                                "api_id": api_id,
                                "current_p95_ms": alert.current_ms,
                                "threshold_ms": alert.threshold_ms,
                                "message": alert.message,
                            },
                            db,
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.debug("基线告警派发失败: %s", exc)
        except Exception as exc:  # noqa: BLE001
            # 任何指标/告警异常都不应阻塞主流程
            logger.warning("记录指标或基线检查失败: %s", exc)


def safe_json_dumps(data: Any) -> str:
    """统一 JSON 序列化。"""
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(data)
