async def resolve_dataset_variables(dataset_id: int, db_session) -> list[dict]:
    """Load dataset rows for parameterized execution"""
    from sqlalchemy import select
    from app.models.test_dataset import TestDatasetRow
    import json

    result = await db_session.execute(
        select(TestDatasetRow)
        .where(TestDatasetRow.dataset_id == dataset_id, TestDatasetRow.is_enabled)
        .order_by(TestDatasetRow.row_index)
    )
    rows = []
    for row in result.scalars().all():
        try:
            row_data = json.loads(row.data) if isinstance(row.data, str) else row.data
            rows.append(row_data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Dataset row %d JSON parse failed: %s", row.id, e)
            rows.append({})
    return rows


"""场景执行引擎 — 线性执行器。

核心职责：
1. 按步骤顺序执行场景（支持条件跳过/循环/失败停止）
2. 变量渲染：从环境变量和步骤提取变量中构建执行上下文
3. 断言执行：调用 AssertionEngine 验证响应
4. 报告生成：每一步的执行结果写入 ReportStep

支持三种执行模式：
- execute：完整场景执行，生成测试报告
- execute_step：单步骤执行（调试用），不生成报告
- execute_all：项目下所有场景批量执行

关键设计：
- 顺序模式下循环体的变量通过快照隔离，防止跨迭代污染
- wait_duration 使用 asyncio.sleep 避免阻塞事件循环
- simpleeval 条件评估完全沙箱化，异常不中断执行流
"""

import asyncio
import copy
import json
import logging
import os
import re
import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_scene import TestScene
from app.models.scene_step import SceneStep
from app.models.environment import Environment
from app.models.test_report import TestReport
from app.models.report_step import ReportStep
from app.models.api_definition import ApiDefinition
from app.models.test_case import TestCase
from app.models.project import Project
from app.services.executor.variable_renderer import (
    render_template,
    find_undefined_variables,
    format_undefined_error,
)
from app.services.executor.assertion_engine import (
    run_assertions,
    jsonpath_get,
    _safe_re_search,
)
from app.services.executor.request_builder import (
    build_url,
    build_headers,
    parse_body,
    truncate_response,
)
from app.utils.http_client import get_http_client
from app.core.exceptions import raise_biz, ErrorCodes
from app.utils.url_validator import validate_request_url
from app.utils.json_helpers import safe_json_load

try:
    from simpleeval import NameNotDefined, InvalidExpression
except ImportError:
    NameNotDefined = Exception  # type: ignore
    InvalidExpression = Exception  # type: ignore

logger = logging.getLogger("executor")

from app.services.ws_manager import ws_manager

# 响应体最大存储大小（超过此值截断，避免内存爆炸）
_MAX_RESPONSE_SIZE = 100 * 1024  # 100KB

# 敏感变量名匹配：持久化时跳过包含这些关键字的变量，避免凭据被写回
_SENSITIVE_NAME_PATTERN = re.compile(
    r"(?i)(password|passwd|secret|private_key|client_secret|token|api[_-]?key|access[_-]?key|"
    r"refresh_token|session|jwt|passcode|pin|signature|hmac|auth|authorization|cookie|credential)"
)

# 每步执行超时（秒），防止慢请求长时间挂起
_STEP_TIMEOUT_SECONDS = int(os.getenv("API_PILOT_STEP_TIMEOUT", "30"))

# 场景总执行超时（秒），防止整个场景执行时间过长
_TOTAL_TIMEOUT_SECONDS = int(os.getenv("API_PILOT_TOTAL_TIMEOUT", "300"))
# 批量执行总超时（秒），防止 execute_all 挂起过久（默认 30 分钟）
_EXECUTE_ALL_TIMEOUT_SECONDS = int(os.getenv("API_PILOT_EXECUTE_ALL_TIMEOUT", "1800"))


def _sanitize_error_message(exc: Exception) -> str:
    """对写入报告的异常信息做脱敏处理，避免敏感信息泄露。"""
    exc_name = type(exc).__name__
    # 只保留异常类型和通用信息，不包含 str(exc) 的完整内容（可能含路径/连接串）
    return f"{exc_name}: 步骤执行异常，详情请查看服务端日志"


class LinearExecutor:
    """场景线性执行器 — 按步骤顺序执行，支持条件、循环、变量提取。

    执行流程：
    1. 加载场景和环境配置
    2. 构建变量上下文（环境变量 + 全局配置）
    3. 遍历步骤列表，对每个步骤：
       a. 检查条件表达式（条件不满足则跳过）
       b. 渲染请求模板变量
       c. 发送 HTTP 请求
       d. 执行断言
       e. 提取变量供后续步骤使用
    4. 生成测试报告
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # 使用全局 HTTPClient（含指数退避重试 + 熔断保护），避免每个实例创建独立连接池
        self._client = get_http_client()

    async def _load_project_globals(self, project_id: int) -> tuple[dict, list]:
        """预加载项目全局变量和全局 Headers（N+1 优化）。

        Returns:
            (variables_dict, headers_list) 二元组
        """
        project_global_vars = {}
        project_global_headers = []
        if project_id:
            proj_result = await self.db.execute(
                select(Project.global_variables, Project.global_params).where(
                    Project.id == project_id
                )
            )
            row = proj_result.first()
            if row:
                raw_vars = row[0]
                raw_params = row[1]
                if raw_vars:
                    for v in safe_json_load(raw_vars, []):
                        if (
                            isinstance(v, dict)
                            and v.get("key")
                            and v.get("enabled", True)
                        ):
                            project_global_vars[v["key"]] = v.get("value", "")
                if raw_params:
                    gp = safe_json_load(raw_params, {})
                    if isinstance(gp, dict):
                        for h in gp.get("headers", []):
                            if (
                                isinstance(h, dict)
                                and h.get("key")
                                and h.get("enabled", True)
                            ):
                                project_global_headers.append(h)
        return project_global_vars, project_global_headers

    async def execute_data_driven(
        self,
        scene_id: int,
        env_id: int,
        user_id: int,
        dataset_id: int,
        step_ids: str = "",
    ) -> list[int]:
        """数据驱动执行：遍历数据集每一行，每行作为变量注入场景执行上下文。

        每行数据生成一个独立的测试报告，返回所有报告 ID 列表。

        Args:
            scene_id: 场景 ID
            env_id: 环境 ID
            user_id: 执行者用户 ID
            dataset_id: 数据集 ID
            step_ids: 可选，逗号分隔的步骤 ID

        Returns:
            所有生成的测试报告 ID 列表
        """
        from app.models.scene_dataset import SceneDataset

        ds = await self.db.get(SceneDataset, dataset_id)
        if not ds:
            raise_biz(ErrorCodes.DATASET_NOT_FOUND, f"数据集 {dataset_id} 不存在")

        rows = safe_json_load(ds.data, [])
        if not rows:
            raise_biz(ErrorCodes.DATASET_NOT_FOUND, f"数据集 {dataset_id} 无有效数据行")

        report_ids: list[int] = []
        for row_index, row_data in enumerate(rows):
            if not isinstance(row_data, dict):
                logger.warning("数据集 %d 第 %d 行非 dict，跳过", dataset_id, row_index)
                continue
            # 将数据行作为变量注入，key 前缀 __dataset_ 避免与环境变量冲突
            # 同时将整行数据存入 __dataset_row 供模板引用
            extra_vars = {f"__dataset_{k}": v for k, v in row_data.items()}
            extra_vars["__dataset_row"] = row_data
            extra_vars["__dataset_row_index"] = row_index

            report_id = await self.execute(
                scene_id,
                env_id,
                user_id,
                step_ids=step_ids,
                _extra_variables=extra_vars,
            )
            report_ids.append(report_id)

        return report_ids

    async def execute(
        self,
        scene_id: int,
        env_id: int,
        user_id: int,
        concurrent: bool = False,
        step_ids: str = "",
        _extra_variables: dict | None = None,
    ) -> int:
        """执行完整场景，返回测试报告 ID。

        按 sort_order 升序执行场景的所有已启用步骤。
        支持功能：
        - 条件跳过（condition_expression）
        - 循环执行（loop_count）
        - 失败停止（on_failure="stop"）
        - 变量提取和传递

        Args:
            scene_id: 场景 ID
            env_id: 环境 ID
            user_id: 执行者用户 ID

        Returns:
            生成的测试报告 ID

        Raises:
            BizError: 场景或环境不存在时
        """
        scene = await self.db.get(TestScene, scene_id)
        if not scene:
            raise_biz(ErrorCodes.SCENE_NOT_FOUND, f"scene {scene_id}")

        env = await self.db.get(Environment, env_id)
        if not env:
            raise_biz(ErrorCodes.ENV_REQUIRED)

        # 预加载项目全局变量和全局 Headers，避免每步查询 Project 表（N+1 优化）
        project_global_vars, project_global_headers = await self._load_project_globals(
            scene.project_id
        )

        variables = await self._build_variables(
            env, project_id=scene.project_id, _project_global_vars=project_global_vars
        )
        # 数据驱动：注入数据行变量
        if _extra_variables:
            variables.update(_extra_variables)
        # 初始变量快照：用于执行结束后计算变更集（新增/修改的变量）
        initial_vars_snapshot = dict(variables)
        env_headers = safe_json_load(env.headers, []) if env else []
        # 全局公共 Headers 合并到环境级 Headers（后续 build_headers 会与环境级+步骤级合并）
        if project_global_headers:
            env_headers = project_global_headers + env_headers

        report = TestReport(
            project_id=scene.project_id,
            scene_id=scene_id,
            environment_id=env_id,
            name=f"{scene.name} - {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
            status="running",
            total_count=0,
            executor_id=user_id,
        )
        self.db.add(report)
        await self.db.flush()
        report_id = report.id

        result = await self.db.execute(
            select(SceneStep)
            .where(SceneStep.scene_id == scene_id, SceneStep.enabled == 1)
            .order_by(SceneStep.sort_order)
        )
        steps = result.scalars().all()

        # 按 step_ids 过滤：只运行选中的步骤
        if step_ids:
            id_set = set()
            for sid in step_ids.split(","):
                sid = sid.strip()
                if not sid:
                    continue
                try:
                    id_set.add(int(sid))
                except ValueError:
                    pass  # 跳过非数字输入（含全角数字、字母等）
            if id_set:
                steps = [s for s in steps if s.id in id_set]

        # 空场景检查
        if not steps:
            report.status = "empty"
            report.total_count = 0
            self.db.add(report)
            await self.db.flush()
            return report.id

        scene_loop_count = scene.loop_count or 1
        report.total_count = len(steps) * scene_loop_count
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_duration = 0.0

        # 总超时控制
        execution_start_time = time.time()

        # 预加载 API 定义，避免逐个步骤查询
        api_ids = [s.api_id for s in steps if s.api_id]
        api_defs: dict[int, tuple[str, str]] = {}
        api_scripts: dict[int, dict] = {}
        if api_ids:
            r = await self.db.execute(
                select(ApiDefinition).where(ApiDefinition.id.in_(api_ids))
            )
            for a in r.scalars().all():
                api_defs[a.id] = (a.method, a.path)
                api_scripts[a.id] = {
                    "pre_script": a.pre_script or "",
                    "post_script": a.post_script or "",
                    "extract_vars": a.extract_vars or "[]",
                }

        # 用例导入步骤：批量加载关联 api_id 的 method/path（避免 N+1）
        case_ids = [s.test_case_id for s in steps if not s.api_id and s.test_case_id]
        case_defs: dict[int, dict] = {}
        if case_ids:
            cases_result = await self.db.execute(
                select(TestCase).where(TestCase.id.in_(case_ids))
            )
            for c in cases_result.scalars().all():
                case_defs[c.id] = {
                    "id": c.id,
                    "name": c.name,
                    "api_id": c.api_id,
                    "assertions": c.assertions,
                    "extract_vars": c.extract_vars,
                }
            case_api_ids = [c["api_id"] for c in case_defs.values() if c.get("api_id")]
            if case_api_ids:
                api_result = await self.db.execute(
                    select(ApiDefinition).where(ApiDefinition.id.in_(case_api_ids))
                )
                for a in api_result.scalars().all():
                    api_defs[a.id] = (a.method, a.path)

        # 按 parallel_group 分组：相同组 >0 的步骤并发执行
        parallel_groups: dict[int, list] = {}
        sequential_steps: list = []
        for s in steps:
            if s.parallel_group and s.parallel_group > 0:
                parallel_groups.setdefault(s.parallel_group, []).append(s)
            else:
                sequential_steps.append(s)

        # 展平为执行序列：顺序组 + 并行组（用 None 分隔表示并发块）
        # 每个元素是单个步骤或一组步骤
        execution_plan: list[tuple] = []
        for s in sequential_steps:
            execution_plan.append(("single", s))
        for pg_id, pg_steps in sorted(parallel_groups.items()):
            execution_plan.append(("parallel", pg_steps))

        # 基础步骤索引：顺序步骤的数量（并行组从此值开始递增）
        base_step_index = len(sequential_steps)

        # 失败策略：stop / continue / ignore

        # ── 场景级循环：重复执行整个步骤序列 scene_loop_count 次 ──
        scene_aborted = False
        for scene_iter in range(scene_loop_count):
            if scene_aborted:
                break
            # ── 执行计划遍历 ──
            parallel_step_index = 0
            for plan_item in execution_plan:
                # 总超时检查
                if time.time() - execution_start_time > _TOTAL_TIMEOUT_SECONDS:
                    logger.warning(
                        "场景 %d 执行总超时（%d秒），提前终止",
                        scene_id,
                        _TOTAL_TIMEOUT_SECONDS,
                    )
                    report.status = "timeout"
                    report.error_message = (
                        f"执行总超时（超过 {_TOTAL_TIMEOUT_SECONDS} 秒）"
                    )
                    scene_aborted = True
                    break

                mode, steps_batch = plan_item

                if mode == "parallel":
                    # ── 并行组执行 ──
                    # 不同行的步骤并发执行，使用独立变量快照防止交叉污染
                    # 记录各并行步骤索引，确保完成广播使用正确值（跨组累计）
                    parallel_step_indices: dict[int, int] = {}

                    async def _exec_one_parallel(pstep: SceneStep) -> dict:
                        pvars = copy.deepcopy(variables)
                        presult = await self._execute_step(
                            pstep,
                            pvars,
                            env,
                            env_headers,
                            api_defs,
                            case_defs,
                            api_scripts,
                        )
                        return {"step": pstep, "result": presult}

                    for ps in steps_batch:
                        parallel_step_index += 1
                        parallel_step_indices[ps.id] = parallel_step_index
                        p_label = (
                            ps.label
                            or api_defs.get(ps.api_id, (None, None))[1]
                            or f"Step {ps.id}"
                        )
                        await ws_manager.broadcast_step_progress(
                            report_id=report_id,
                            step_index=base_step_index + parallel_step_index,
                            total_steps=len(steps),
                            step_id=ps.id,
                            step_name=p_label,
                            status="running",
                        )
                    p_results = await asyncio.gather(
                        *[_exec_one_parallel(ps) for ps in steps_batch]
                    )
                    # 收集并行步骤变量提取结果，按 step_index 排序后合并，
                    # 确保合并顺序与步骤定义顺序一致（而非异步完成顺序），保证合并结果确定性
                    parallel_extracts: list[tuple[int, dict]] = []
                    for pdata in p_results:
                        ps = pdata["step"]
                        result_dict = pdata["result"]
                        # 收集变量提取结果（稍后按 step_index 排序后合并）
                        if result_dict.get("status") == "success" and result_dict.get(
                            "extracted"
                        ):
                            step_idx = parallel_step_indices.get(ps.id, 0)
                            parallel_extracts.append(
                                (step_idx, result_dict["extracted"])
                            )
                        rs = self._create_report_step(report_id, ps, result_dict)
                        self.db.add(rs)
                        total_duration += result_dict.get("duration", 0)
                        if result_dict.get("status") == "success":
                            total_passed += 1
                        else:
                            total_failed += 1
                        step_has_failure_parallel = (
                            result_dict.get("status") != "success"
                        )
                        # 广播并行步骤完成
                        p_label = (
                            ps.label
                            or api_defs.get(ps.api_id, (None, None))[1]
                            or f"Step {ps.id}"
                        )
                        step_completion_idx = parallel_step_indices.get(
                            ps.id, parallel_step_index
                        )
                        await ws_manager.broadcast_step_progress(
                            report_id=report_id,
                            step_index=base_step_index + step_completion_idx,
                            total_steps=len(steps),
                            step_id=ps.id,
                            step_name=p_label,
                            status="failed" if step_has_failure_parallel else "success",
                        )
                    # 按 step_index 排序后合并变量，确保合并顺序确定性
                    parallel_extracts.sort(key=lambda x: x[0])
                    for _, extracted in parallel_extracts:
                        variables.update(extracted)
                    continue

                # 顺序执行单个步骤
                step = steps_batch
                # 广播步骤开始
                step_label = (
                    step.label
                    or api_defs.get(step.api_id, (None, None))[1]
                    or f"Step {step.id}"
                )
                await ws_manager.broadcast_step_progress(
                    report_id=report_id,
                    step_index=steps.index(step),
                    total_steps=len(steps),
                    step_id=step.id,
                    step_name=step_label,
                    status="running",
                )

                # 记录执行日志
                logger.info(
                    "[场景%d] 开始执行步骤 %d: %s", scene_id, step.id, step_label
                )

                if step.condition_expression:
                    if not self._eval(step.condition_expression, variables):
                        logger.info(
                            f"Step {step.id} condition not met, skipping: {step.condition_expression}"
                        )
                        rs = self._create_report_step(
                            report_id, step, {"status": "skipped", "duration": 0}
                        )
                        self.db.add(rs)
                        total_skipped += 1
                        # 广播跳过
                        await ws_manager.broadcast_step_progress(
                            report_id=report_id,
                            step_index=steps.index(step),
                            total_steps=len(steps),
                            step_id=step.id,
                            step_name=step_label,
                            status="skipped",
                        )
                        continue

                loop_count = step.loop_count or 1
                step_has_failure = False
                scene_should_stop = False

                if concurrent and loop_count > 1:
                    # ── 并发执行模式 ──
                    # 使用 asyncio.Semaphore 控制并发数（thread_count 决定最大并发）
                    sem = asyncio.Semaphore(scene.thread_count or 1)

                    async def _run_one(i: int) -> dict:
                        async with sem:
                            # 并发模式下变量不跨迭代级联，使用深拷贝确保嵌套结构完全隔离
                            v = copy.deepcopy(variables)
                            v["__loop_index"] = i
                            return await self._execute_step(
                                step,
                                v,
                                env,
                                env_headers,
                                api_defs,
                                case_defs,
                                api_scripts,
                            )

                    tasks = [_run_one(i) for i in range(loop_count)]
                    results = await asyncio.gather(*tasks)

                    for result_dict in results:
                        rs = self._create_report_step(report_id, step, result_dict)
                        self.db.add(rs)

                        total_duration += result_dict.get("duration", 0)

                        is_success = result_dict.get("status") == "success"
                        if is_success:
                            total_passed += 1
                        else:
                            total_failed += 1
                            step_has_failure = True

                else:
                    # ── 顺序执行模式（原始逻辑，保持兼容） ──
                    actual_loop_count = 0
                    for i in range(loop_count):
                        # 快照隔离：每次迭代从父上下文深拷贝，防止循环体内变量污染
                        loop_vars = copy.deepcopy(variables)
                        loop_vars["__loop_index"] = i

                        result_dict = await self._execute_step(
                            step,
                            loop_vars,
                            env,
                            env_headers,
                            api_defs,
                            case_defs=case_defs,
                            api_scripts=api_scripts,
                        )
                        logger.debug(
                            "step result: step_id=%s status=%s extracted=%s",
                            step.id,
                            result_dict.get("status"),
                            result_dict.get("extracted"),
                        )

                        rs = self._create_report_step(report_id, step, result_dict)
                        self.db.add(rs)

                        total_duration += result_dict.get("duration", 0)

                        # 每次成功迭代都将提取的变量合并到父上下文（后写入覆盖前值）
                        if result_dict.get("status") == "success" and result_dict.get(
                            "extracted"
                        ):
                            variables.update(result_dict["extracted"])

                        is_success = result_dict.get("status") == "success"
                        if is_success:
                            total_passed += 1
                        else:
                            total_failed += 1
                            step_has_failure = True

                        if not is_success and scene.on_failure == "stop":
                            scene_should_stop = True
                            break

                        actual_loop_count = i + 1

                    # 记录实际执行的循环次数（追加到已有 metadata，避免覆盖前一个循环步骤的记录）
                    if loop_count > 1:
                        _loop_configs = []
                        if report.metadata:
                            try:
                                existing = json.loads(report.metadata)
                                if isinstance(existing, list):
                                    _loop_configs = existing
                                elif (
                                    isinstance(existing, dict)
                                    and "loop_configs" in existing
                                ):
                                    _loop_configs = existing["loop_configs"]
                            except (json.JSONDecodeError, TypeError):
                                pass
                        _loop_configs.append(
                            {
                                "count": loop_count,
                                "on_failure": scene.on_failure,
                                "actual_count": actual_loop_count,
                            }
                        )
                        report.metadata = json.dumps({"loop_configs": _loop_configs})

                if scene_should_stop:
                    scene_aborted = True
                    break

                # 广播步骤完成
                step_final_status = "failed" if step_has_failure else "success"
                await ws_manager.broadcast_step_progress(
                    report_id=report_id,
                    step_index=steps.index(step),
                    total_steps=len(steps),
                    step_id=step.id,
                    step_name=step_label,
                    status=step_final_status,
                )

        report.pass_count = total_passed
        report.fail_count = total_failed
        report.skip_count = total_skipped
        report.status = "success" if total_failed == 0 else "failed"
        report.duration = total_duration
        await self.db.flush()

        # 变量持久化：将本次执行新增/修改的变量写回 environment 或 global
        try:
            persist_target = (
                getattr(scene, "var_persist_target", "environment") or "environment"
            )
            if persist_target != "none":
                # 计算变更集：新增或值发生变化的变量，过滤掉内部变量（以 __ 开头）
                changed_vars = {
                    k: v
                    for k, v in variables.items()
                    if not k.startswith("__")
                    and not _SENSITIVE_NAME_PATTERN.match(k)
                    and not (isinstance(v, dict) and v.get("__secret__"))
                    and (
                        k not in initial_vars_snapshot
                        or str(initial_vars_snapshot[k]) != str(v)
                    )
                }
                if changed_vars:
                    if persist_target == "global":
                        proj = await self.db.get(Project, scene.project_id)
                        if proj:
                            existing_vars = safe_json_load(proj.global_variables, [])
                            self._merge_persisted_vars(existing_vars, changed_vars)
                            proj.global_variables = json.dumps(
                                existing_vars, ensure_ascii=False
                            )
                    else:
                        env_vars = safe_json_load(env.variables, [])
                        self._merge_persisted_vars(env_vars, changed_vars)
                        env.variables = json.dumps(env_vars, ensure_ascii=False)
                    await self.db.flush()
        except Exception as e:  # noqa: BLE001 — 持久化失败不阻断报告生成
            logger.warning(
                "变量持久化失败（不阻断报告生成）: %s: %s", type(e).__name__, e
            )

        # 广播报告完成
        await ws_manager.broadcast_report_done(
            report_id=report_id,
            status=report.status,
            pass_count=total_passed,
            fail_count=total_failed,
            total_count=report.total_count,
        )

        # SSE 通知推送：执行完成
        try:
            from app.services.sse_manager import sse_manager

            title = f"场景「{scene.name}」执行{'成功' if report.status == 'success' else '失败'}"
            content = (
                f"通过 {total_passed}/{report.total_count}，耗时 {report.duration:.1f}s"
            )
            await sse_manager.publish_notification(
                user_id=user_id,
                notif_id=report_id,
                title=title,
                content=content,
                notif_type="report" if report.status == "success" else "alert",
                link=f"/projects/{scene.project_id}/reports/{report_id}",
            )
        except Exception:
            logger.warning("SSE notification push failed (non-critical)", exc_info=True)
        return report_id

    def _create_report_step(
        self, report_id: int, step: SceneStep, result_dict: dict
    ) -> ReportStep:
        """统一创建 ReportStep，消除三处重复构造。"""
        # 合并前置和后置脚本输出
        script_parts = []
        if result_dict.get("pre_script_output"):
            script_parts.append("[前置脚本] " + result_dict["pre_script_output"])
        if result_dict.get("post_script_output"):
            script_parts.append("[后置脚本] " + result_dict["post_script_output"])

        script_error_parts = []
        if result_dict.get("pre_script_error"):
            script_error_parts.append("[前置脚本] " + result_dict["pre_script_error"])
        if result_dict.get("post_script_error"):
            script_error_parts.append("[后置脚本] " + result_dict["post_script_error"])

        return ReportStep(
            report_id=report_id,
            scene_step_id=step.id,
            api_id=step.api_id,
            sort_order=step.sort_order,
            status=result_dict.get("status", "error"),
            duration=result_dict.get("duration", 0),
            request_url=result_dict.get("request_url", ""),
            request_method=result_dict.get("request_method", ""),
            request_headers=json.dumps(result_dict.get("request_headers", {})),
            request_body=result_dict.get("request_body", ""),
            response_status=result_dict.get("response_status", 0),
            response_headers=json.dumps(result_dict.get("response_headers", {})),
            response_body=result_dict.get("response_body", ""),
            assertions=json.dumps(result_dict.get("assertions", [])),
            error_message=result_dict.get("error_message"),
            script_output="\n".join(script_parts) if script_parts else None,
            script_error="\n".join(script_error_parts) if script_error_parts else None,
        )

    @staticmethod
    def _merge_persisted_vars(existing_vars: list, changed_vars: dict) -> None:
        """将变更变量合并到已有的变量列表（就地更新）。

        key 已存在则更新 value，不存在则追加。
        """
        for key, value in changed_vars.items():
            found = False
            for v in existing_vars:
                if isinstance(v, dict) and v.get("key") == key:
                    v["value"] = value
                    found = True
                    break
            if not found:
                existing_vars.append({"key": key, "value": value, "enabled": True})

    async def execute_step(self, step_id: int, env_id: int, user_id: int) -> dict:
        """执行单一步骤（调试模式），不持久化报告。

        与 execute 不同，此方法只返回执行结果字典，
        不创建 ReportStep 记录。用于步骤调试场景。

        Args:
            step_id: 步骤 ID
            env_id: 环境 ID
            user_id: 当前用户 ID

        Returns:
            包含请求/响应/断言结果的字典
        """
        step = await self.db.get(SceneStep, step_id)
        if not step:
            raise_biz(ErrorCodes.SCENE_STEP_NOT_FOUND, f"step {step_id}")

        # 通过 step.scene_id 反查 TestScene 获取 project_id
        scene = await self.db.get(TestScene, step.scene_id)
        project_id = scene.project_id if scene else None

        # 预加载项目全局变量和全局 Headers（避免 _build_variables 中重复查询）
        project_global_vars, project_global_headers = await self._load_project_globals(
            project_id
        )

        env = await self.db.get(Environment, env_id)
        if not env:
            raise_biz(ErrorCodes.ENV_REQUIRED)
        variables = await self._build_variables(
            env, project_id=project_id, _project_global_vars=project_global_vars
        )
        env_headers = safe_json_load(env.headers, []) if env else []
        if project_global_headers:
            env_headers = project_global_headers + env_headers

        api_defs: dict[int, tuple[str, str]] = {}
        api_scripts: dict[int, dict] = {}
        if step.api_id:
            api = await self.db.get(ApiDefinition, step.api_id)
            if api:
                api_defs[api.id] = (api.method, api.path)
                api_scripts[api.id] = {
                    "pre_script": api.pre_script or "",
                    "post_script": api.post_script or "",
                    "extract_vars": api.extract_vars or "[]",
                }

        return await self._execute_step(
            step, variables, env, env_headers, api_defs, api_scripts=api_scripts
        )

    async def execute_case(self, case_id: int, env_id: int, user_id: int) -> dict:
        """执行单条测试用例（独立执行），不生成报告。

        将 TestCase 包装为 SceneStep 后执行，支持用例级断言和变量提取。
        用例的 request_body 直接使用，headers 从 API 定义获取。

        Args:
            case_id: 测试用例 ID
            env_id: 环境 ID
            user_id: 当前用户 ID

        Returns:
            包含请求/响应/断言结果的字典
        """
        case = await self.db.get(TestCase, case_id)
        if not case:
            raise_biz(ErrorCodes.CASE_NOT_FOUND, f"case {case_id}")

        env = await self.db.get(Environment, env_id)
        if not env:
            raise_biz(ErrorCodes.ENV_REQUIRED)
        project_global_vars, project_global_headers = await self._load_project_globals(
            case.project_id
        )
        variables = await self._build_variables(
            env, project_id=case.project_id, _project_global_vars=project_global_vars
        )
        env_headers = safe_json_load(env.headers, []) if env else []
        if project_global_headers:
            env_headers = project_global_headers + env_headers

        api_headers = []
        api_params = []
        api_defs: dict[int, tuple[str, str]] = {}
        api_scripts: dict[int, dict] = {}
        if case.api_id:
            api = await self.db.get(ApiDefinition, case.api_id)
            if api:
                api_defs[api.id] = (api.method, api.path)
                api_scripts[api.id] = {
                    "pre_script": api.pre_script or "",
                    "post_script": api.post_script or "",
                    "extract_vars": api.extract_vars or "[]",
                }
                api_headers = safe_json_load(api.headers, [])
                api_params = safe_json_load(api.params, [])

        # 用例 body_report 兼容 {content: ...} 包装格式
        case_body_report = case.request_body or ""
        if case_body_report and case_body_report.startswith("{"):
            try:
                body_report_obj = json.loads(case_body_report)
                if isinstance(body_report_obj, dict) and "content" in body_report_obj:
                    case_body_report = body_report_obj["content"]
            except (json.JSONDecodeError, TypeError):
                pass
        step_data = {
            "id": 0,
            "api_id": case.api_id,
            "sort_order": 0,
            "loop_count": 1,
            "condition_expression": None,
            "headers": api_headers,
            "query_params": api_params,
            "request_body": case_body_report,
            "assertions": safe_json_load(case.assertions, []),
            "extract_vars": safe_json_load(case.extract_vars, []),
        }
        step = SceneStep(**step_data)
        return await self._execute_step(
            step, variables, env, env_headers, api_defs, api_scripts=api_scripts
        )

    async def execute_all(
        self, project_id: int, env_id: int, user_id: int
    ) -> list[int]:
        """批量执行项目下所有场景。

        遍历场景列表逐个执行，某个场景失败不影响其他场景执行。
        失败场景的错误会被记录日志，不阻断流程。

        Args:
            project_id: 项目 ID
            env_id: 环境 ID
            user_id: 执行者用户 ID

        Returns:
            所有成功生成的报告 ID 列表
        """
        result = await self.db.execute(
            select(TestScene).where(TestScene.project_id == project_id)
        )
        scenes = result.scalars().all()
        report_ids = []
        execute_all_start = time.time()
        for scene in scenes:
            # 总超时检查：超过 _EXECUTE_ALL_TIMEOUT_SECONDS 则终止后续执行
            if time.time() - execute_all_start > _EXECUTE_ALL_TIMEOUT_SECONDS:
                logger.warning(
                    "execute_all 执行总超时（%d秒），已执行 %d 个场景后提前终止",
                    _EXECUTE_ALL_TIMEOUT_SECONDS,
                    len(report_ids),
                )
                break
            try:
                report_id = await self.execute(scene.id, env_id, user_id)
                report_ids.append(report_id)
            except (ValueError, KeyError, OSError, httpx.HTTPError) as e:
                logger.error(
                    "Scene %d execution failed: %s: %s", scene.id, type(e).__name__, e
                )
            except Exception as e:  # noqa: BLE001 — 批量执行需隔离单场景故障
                logger.error(
                    "Scene %d execution failed with unexpected error: %s: %s",
                    scene.id,
                    type(e).__name__,
                    e,
                    exc_info=True,
                )
        return report_ids

    async def _execute_step(
        self,
        step: SceneStep,
        variables: dict,
        env: Environment | None,
        env_headers: list,
        api_defs: dict[int, tuple[str, str]],
        case_defs: dict[int, dict] | None = None,
        api_scripts: dict[int, dict] | None = None,
        retry_count: int = 0,
    ) -> dict:
        """内部：执行一步完整的 HTTP 请求周期。

        处理流程：
        1. 确定 HTTP 方法（从 API 定义）
        2. 构建请求头（环境头 + 步骤头，变量渲染）
        3. 构建 URL（base_url + path + query params）
        4. 发送请求（httpx.AsyncClient，30s 超时）
        5. 执行断言
        6. 变量提取

        Args:
            step: 场景步骤对象
            variables: 当前变量上下文
            env: 环境配置
            env_headers: 环境级请求头
            api_defs: API 定义缓存 {api_id: (method, path)}

        Returns:
            包含完整执行结果的字典
        """
        start = time.time()
        try:
            # 检测未定义变量
            undefined_vars = []
            # 检查请求体
            if step.request_body:
                undefined_vars.extend(
                    find_undefined_variables(step.request_body, variables)
                )
            # 检查路径（从 API 定义获取）
            api_path = api_defs.get(step.api_id, ("", ""))[1] if step.api_id else ""
            if api_path:
                undefined_vars.extend(find_undefined_variables(api_path, variables))
            # 检查查询参数
            if step.query_params:
                for param in safe_json_load(step.query_params, []):
                    if isinstance(param, dict):
                        if param.get("key"):
                            undefined_vars.extend(
                                find_undefined_variables(str(param["key"]), variables)
                            )
                        if param.get("value"):
                            undefined_vars.extend(
                                find_undefined_variables(str(param["value"]), variables)
                            )

            # 如果有未定义变量，返回失败结果
            if undefined_vars:
                error_msg = "; ".join(
                    [format_undefined_error(var) for var in set(undefined_vars)]
                )
                logger.warning("步骤 %s 存在未定义变量: %s", step.label, error_msg)
                return {
                    "status": "failed",
                    "duration": time.time() - start,
                    "error_message": error_msg,
                    "request_url": "",
                    "request_method": step.method or "GET",
                    "response_status": 0,
                    "response_body": "",
                    "response_headers": {},
                    "assertions": [],
                }

            method = "GET"
            if step.api_id and step.api_id in api_defs:
                method = api_defs[step.api_id][0]

            # 构建请求头（环境级+步骤级合并，已渲染变量）
            headers = build_headers(
                safe_json_load(step.headers, []),
                env_headers,
                variables,
            )

            # 确定 base_url：优先使用 env.base_url，其次从 services 获取
            base_url = ""
            if env:
                if getattr(env, "base_url", None):
                    base_url = env.base_url
                else:
                    services = safe_json_load(env.services, [])
                    base_url = services[0].get("url", "") if services else ""

            # 对 base_url 进行变量渲染（支持 {{base_url}} 等变量引用）
            if base_url:
                base_url = render_template(base_url, variables)

            # 组装 URL
            path = "/"
            if step.api_id and step.api_id in api_defs:
                path = api_defs[step.api_id][1]
            elif step.test_case_id:
                case_info = (
                    (case_defs or {}).get(step.test_case_id)
                    if case_defs is not None
                    else None
                )
                if not case_info:
                    case_info = await self.db.get(TestCase, step.test_case_id)
                    case_info = (
                        {
                            "id": case_info.id,
                            "name": case_info.name,
                            "api_id": case_info.api_id,
                        }
                        if case_info
                        else None
                    )
                if (
                    case_info
                    and case_info.get("api_id")
                    and case_info["api_id"] in api_defs
                ):
                    path = api_defs[case_info["api_id"]][1]
            url = build_url(
                base_url,
                path,
                safe_json_load(step.query_params, []),
                variables,
            )

            # 注入环境认证配置
            if env and getattr(env, "auth_config", None):
                auth_config = env.auth_config
                if isinstance(auth_config, dict):
                    auth_type = auth_config.get("type", "")
                    if auth_type == "bearer" and auth_config.get("token"):
                        headers["Authorization"] = f"Bearer {auth_config['token']}"
                    elif auth_type == "basic" and auth_config.get("username"):
                        import base64

                        cred = (
                            f"{auth_config['username']}:"
                            f"{auth_config.get('password', '')}"
                        )
                        encoded = base64.b64encode(cred.encode()).decode()
                        headers["Authorization"] = f"Basic {encoded}"
                    elif auth_type == "apikey":
                        key_name = auth_config.get("key", "X-API-Key")
                        key_value = auth_config.get("value", "")
                        key_location = auth_config.get("in", "header")
                        if key_location == "header":
                            headers[key_name] = key_value
                        elif key_location == "query":
                            sep = "&" if "?" in url else "?"
                            url = f"{url}{sep}{key_name}={key_value}"

            try:
                await validate_request_url(url)
            except ValueError as e:
                duration = time.time() - start
                return {
                    "status": "failed",
                    "duration": duration,
                    "request_url": url,
                    "request_method": method,
                    "response_status": 0,
                    "error_message": str(e),
                    "request_headers": dict(headers),
                    "request_body": "",
                    "response_headers": {},
                    "response_body": "",
                    "assertions": [],
                    "extracted": {},
                }

            # 解析请求体
            body_report_raw = render_template(step.request_body or "", variables)
            body_report_send, data_send, files_send = parse_body(
                body_report_raw, variables
            )
            # 报告用 body_report（data_send 还原为 JSON 字符串）
            body_report_report = (
                json.dumps(data_send) if data_send else (body_report_send or "")
            )

            # 用 try/finally 确保文件句柄在任何异常路径下都被关闭
            try:
                # 执行前置脚本（如果 API 定义中配置了 pre_script）
                pre_script = ""
                pre_script_output = None
                pre_script_error = None
                if step.api_id and api_scripts and step.api_id in api_scripts:
                    pre_script = api_scripts[step.api_id].get("pre_script", "")
                if pre_script.strip():
                    try:
                        from app.services.executor.script_executor import (
                            execute_pre_script,
                        )

                        step_headers_list = safe_json_load(step.headers, [])
                        step_params_list = safe_json_load(step.query_params, [])
                        step_body = safe_json_load(
                            step.request_body or "", {"type": "none", "content": ""}
                        )
                        pre_result = await execute_pre_script(
                            pre_script,
                            method,
                            path,
                            step_headers_list,
                            step_params_list,
                            step_body,
                            {"type": "none"},
                            variables,
                        )
                        if pre_result:
                            # 提取脚本输出
                            pre_script_output = pre_result.pop("script_output", None)
                            pre_script_error = pre_result.pop("script_error", None)
                            # 处理修改后的请求
                            if pre_result.get("modified_request"):
                                modified_request = pre_result["modified_request"]
                                method = modified_request.get("method", method)
                                path = modified_request.get("path", path)
                                if modified_request.get("headers"):
                                    headers_list_updated = modified_request["headers"]
                                    headers = build_headers(
                                        headers_list_updated, env_headers, variables
                                    )
                                if modified_request.get("params"):
                                    url = build_url(
                                        base_url,
                                        path,
                                        modified_request["params"],
                                        variables,
                                    )
                                if modified_request.get("body"):
                                    new_body = modified_request["body"]
                                    body_report_raw = (
                                        json.dumps(new_body)
                                        if isinstance(new_body, dict)
                                        else str(new_body)
                                    )
                                    body_report_send, data_send, files_send = (
                                        parse_body(body_report_raw, variables)
                                    )
                                    body_report_report = (
                                        json.dumps(data_send)
                                        if data_send
                                        else (body_report_send or "")
                                    )
                    except Exception as e:  # noqa: BLE001 — 脚本执行失败不中断请求
                        logger.warning(
                            "pre-script 执行失败（不中断请求）: %s: %s",
                            type(e).__name__,
                            e,
                        )
                        pre_script_error = f"{type(e).__name__}: {e}"

                # wait_duration
                wait = getattr(step, "wait_duration", None) or 0
                wait_mode = getattr(step, "wait_mode", None) or "fixed"
                if wait_mode == "random":
                    import random

                    wait_min = getattr(step, "wait_min", None) or 0
                    wait_max = getattr(step, "wait_max", None) or 1000
                    wait = random.randint(wait_min, wait_max) / 1000.0  # ms to seconds
                    if wait > 0:
                        await asyncio.sleep(wait)
                elif wait and wait > 0:
                    await asyncio.sleep(wait / 1000.0)  # ms to seconds

                request_headers_snapshot = dict(headers)
                # asyncio.timeout 强制终止超时请求（防止慢请求挂起整个执行流）
                # Python 3.11+，若超时则抛出 asyncio.TimeoutError
                try:
                    async with asyncio.timeout(_STEP_TIMEOUT_SECONDS):
                        if method in ("POST", "PUT", "PATCH"):
                            if files_send:
                                resp = await self._client.request(
                                    method=method,
                                    url=url,
                                    headers=headers,
                                    data=data_send,
                                    files=files_send,
                                )
                            elif data_send is not None:
                                resp = await self._client.request(
                                    method=method,
                                    url=url,
                                    headers=headers,
                                    data=data_send,
                                )
                            else:
                                json_data = None
                                if body_report_send:
                                    try:
                                        json_data = json.loads(body_report_send)
                                    except (json.JSONDecodeError, TypeError):
                                        pass
                                if json_data is not None:
                                    resp = await self._client.request(
                                        method=method,
                                        url=url,
                                        headers=headers,
                                        json=json_data,
                                    )
                                else:
                                    resp = await self._client.request(
                                        method=method,
                                        url=url,
                                        headers=headers,
                                        content=body_report_send,
                                    )
                        else:
                            resp = await self._client.request(
                                method=method, url=url, headers=headers
                            )
                except asyncio.TimeoutError:
                    if method.upper() in ("GET", "HEAD") and retry_count == 0:
                        result_dict = await self._execute_step(
                            step=step,
                            variables=variables,
                            env=env,
                            env_headers=env_headers,
                            api_defs=api_defs,
                            case_defs=case_defs,
                            api_scripts=api_scripts,
                            retry_count=1,
                        )
                        return result_dict

                    duration = time.time() - start
                    return {
                        "status": "failed",
                        "duration": duration,
                        "request_url": url,
                        "request_method": method,
                        "response_status": 0,
                        "error_message": f"请求超时（超过 {_STEP_TIMEOUT_SECONDS} 秒）",
                        "request_headers": request_headers_snapshot,
                        "request_body": body_report_report,
                        "response_headers": {},
                        "response_body": "",
                        "assertions": [],
                        "extracted": {},
                    }
            finally:
                # parse_body 中文件以 (filename, file_handle) 元组存储
                # finally 确保无论请求成功/失败/异常，文件句柄始终被关闭
                if files_send:
                    for _fh in files_send.values():
                        try:
                            if isinstance(_fh, tuple) and len(_fh) >= 2:
                                _fh[1].close()
                        except (OSError, AttributeError):
                            pass

            duration = time.time() - start
            # 截断响应体（使用字节切片，避免全量加载）
            _resp_stored_body_report, response_body = truncate_response(
                resp.content[: _MAX_RESPONSE_SIZE + 1]
            )

            # 执行后置脚本（如果 API 定义中配置了 post_script）
            post_script = ""
            post_script_output = None
            post_script_error = None
            if step.api_id and api_scripts and step.api_id in api_scripts:
                post_script = api_scripts[step.api_id].get("post_script", "")
            if post_script.strip():
                try:
                    from app.services.executor.script_executor import (
                        execute_post_script,
                    )

                    script_response = {
                        "response_status": resp.status_code,
                        "response_body": _resp_stored_body_report,
                        "response_headers": dict(resp.headers),
                        "duration": duration,
                    }
                    script_vars = await execute_post_script(
                        post_script,
                        script_response,
                        variables,
                    )
                    # 提取脚本输出（非变量字段）
                    post_script_output = script_vars.pop("script_output", None)
                    post_script_error = script_vars.pop("script_error", None)
                    if script_vars:
                        variables.update(script_vars)
                except Exception as e:  # noqa: BLE001 — 脚本执行失败不中断请求
                    logger.warning(
                        "post-script 执行失败（不中断请求）: %s: %s",
                        type(e).__name__,
                        e,
                    )
                    post_script_error = f"{type(e).__name__}: {e}"

            # 用例导入步骤：从用例加载断言和变量提取（步骤未覆写时）
            case_ref = None
            if getattr(step, "test_case_id", None):
                case_ref = (
                    (case_defs or {}).get(step.test_case_id)
                    if case_defs is not None
                    else None
                )
                if not case_ref:
                    case_row = await self.db.get(TestCase, step.test_case_id)
                    case_ref = (
                        {
                            "id": case_row.id,
                            "name": case_row.name,
                            "api_id": case_row.api_id,
                            "assertions": case_row.assertions,
                            "extract_vars": case_row.extract_vars,
                        }
                        if case_row
                        else None
                    )

            assertions_raw = safe_json_load(step.assertions, [])
            if not assertions_raw and case_ref:
                assertions_raw = safe_json_load(case_ref.get("assertions", []), [])

            # 提取 cookies 用于 Cookie 断言
            response_cookies = dict(resp.cookies) if hasattr(resp, "cookies") else {}

            assertion_results = run_assertions(
                assertions_raw,
                resp.status_code,
                response_body,
                dict(resp.headers),
                duration,
                response_cookies,
            )

            extracted = {}
            extract_rules = safe_json_load(step.extract_vars, [])
            logger.debug(
                "extract: step_id=%s step.extract_vars=%r parsed=%s",
                step.id,
                step.extract_vars,
                extract_rules,
            )
            if not extract_rules and case_ref:
                extract_rules = safe_json_load(case_ref.get("extract_vars", []), [])
            # 也从 API 定义中加载 extract_vars（步骤未配置时使用 API 级规则）
            if (
                not extract_rules
                and step.api_id
                and api_scripts
                and step.api_id in api_scripts
            ):
                extract_rules = safe_json_load(
                    api_scripts[step.api_id].get("extract_vars", "[]"), []
                )
            for rule in extract_rules:
                if not isinstance(rule, dict):
                    continue
                variable = rule.get("variable") or rule.get("var_name")
                if not variable:
                    continue

                source = rule.get(
                    "source", "body"
                )  # 默认从 body 提取，显式 source 可覆盖
                rule_type = rule.get("type", "jsonpath")
                expression = rule.get("expression") or rule.get("path", "")
                val = None

                try:
                    if source == "header":
                        header_name = expression or rule.get("header_name", "")
                        if header_name:
                            val = resp.headers.get(header_name)
                    elif source == "status":
                        val = resp.status_code
                    else:
                        # body 提取
                        if rule_type == "regex" and expression:
                            try:
                                body_text = (
                                    response_body
                                    if isinstance(response_body, str)
                                    else json.dumps(response_body)
                                )
                                match = _safe_re_search(expression, body_text)
                                if match:
                                    try:
                                        val = match.group(1)
                                    except IndexError:
                                        val = match.group(0)
                            except re.error as e:
                                logger.warning(
                                    "提取变量正则表达式无效: %s: %s", expression, e
                                )
                        elif expression:
                            val = jsonpath_get(response_body, expression)
                except Exception as e:
                    logger.warning("提取规则 %s 失败: %s", variable, e)

                if val is not None:
                    extracted[variable] = val

            all_passed = all(a.get("passed", False) for a in assertion_results)
            return {
                "status": "success" if all_passed else "failed",
                "duration": duration,
                "request_url": url,
                "request_method": method,
                "request_headers": request_headers_snapshot,
                "request_body": body_report_report,
                "response_status": resp.status_code,
                "response_headers": dict(resp.headers),
                "response_body": _resp_stored_body_report,
                "assertions": assertion_results,
                "error_message": None,
                "extracted": extracted,
                "pre_script_output": pre_script_output,
                "pre_script_error": pre_script_error,
                "post_script_output": post_script_output,
                "post_script_error": post_script_error,
            }
        except Exception as e:  # noqa: BLE001 — 步骤执行需捕获所有异常以记录失败状态
            duration = time.time() - start
            sanitized_msg = _sanitize_error_message(e)
            logger.warning("Step execution failed: %s", sanitized_msg, exc_info=True)
            return {
                "status": "error",
                "duration": duration,
                "request_url": locals().get("url", ""),
                "request_method": locals().get("method", ""),
                "response_status": 0,
                "error_message": sanitized_msg,
                "request_headers": locals().get("headers", {}),
                "request_body": locals().get("body_report_report", ""),
                "response_headers": {},
                "response_body": "",
                "assertions": [],
                "extracted": {},
            }

    async def close(self):
        """executor close: do NOT close the global HTTP client (managed by app lifecycle)."""
        pass

    def _eval(self, expression: str, variables: dict) -> bool:
        """安全评估条件表达式。

        使用 simpleeval 库执行仅支持基本运算和变量引用的安全评估，
        不执行任意 Python 代码。解析异常时安全返回 False，
        不中断执行流程。

        Args:
            expression: 条件表达式字符串，如 "status == 200"
            variables: 当前变量上下文

        Returns:
            条件是否成立
        """
        try:
            from simpleeval import SimpleEval

            s = SimpleEval(
                names=copy.deepcopy(variables),
                functions=None,  # 禁止所有函数调用
            )
            # 沙箱加固：禁止属性访问、类型遍历、方法调用
            s.types = []  # 禁止类型引用（如 __class__）
            s.max_call_depth = 0  # 禁止函数调用链
            return bool(s.eval(expression))
        except (
            NameNotDefined,
            InvalidExpression,
            TypeError,
            ValueError,
            SyntaxError,
        ) as e:
            logger.warning(
                "Condition evaluation failed, skipping step: %s (%s: %s)",
                expression,
                type(e).__name__,
                e,
            )
            return False

    async def _build_variables(
        self,
        env: Environment | None,
        project_id: int = None,
        _project_global_vars: dict = None,
    ) -> dict:
        """从环境配置构建变量字典。

        _project_global_vars: 可选，预加载的项目全局变量（避免重复查询 Project 表）。

        Returns:
            变量键值字典
        """
        vars_dict = {}
        # 1. 加载项目全局变量（优先使用预加载结果，避免 N+1 查询）
        if project_id and _project_global_vars:
            vars_dict.update(_project_global_vars)
        elif project_id:
            # 兜底：未预加载时仍按需查询（仅首次调用）
            try:
                proj_result = await self.db.execute(
                    select(Project).where(Project.id == project_id)
                )
                proj = proj_result.scalar_one_or_none()
                if proj and proj.global_variables:
                    for v in safe_json_load(proj.global_variables, []):
                        if (
                            isinstance(v, dict)
                            and v.get("key")
                            and v.get("enabled", True)
                        ):
                            vars_dict[v["key"]] = v.get("value", "")
            except (OSError, ValueError) as e:
                logger.warning("加载项目全局变量失败: %s: %s", type(e).__name__, e)
        # 2. 环境变量覆盖同名全局变量
        if env:
            for v in safe_json_load(env.variables, []):
                if isinstance(v, dict) and v.get("key"):
                    vars_dict[v["key"]] = v.get("value", "")
        return vars_dict
