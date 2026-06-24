from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import time

from app.database import get_db
from app.limiter import limiter
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.project import Project
from app.models.environment import Environment
from app.services.executor.linear_executor import LinearExecutor
from app.services.metrics import MetricsCollector
from app.services.permission_service import check_read_access, check_write_access
from app.utils.response import success
from app.core.exceptions import raise_biz, ErrorCodes

logger = logging.getLogger("run")

router = APIRouter(prefix="/projects/{project_id}/run", tags=["Test Execution"])


async def _validate_env(db: AsyncSession, env_id: int):
    """验证环境 ID 对应记录存在"""
    if env_id <= 0:
        raise_biz(ErrorCodes.ENV_REQUIRED)
    env = await db.get(Environment, env_id)
    if not env:
        raise_biz(ErrorCodes.ENV_NOT_FOUND)


@router.post(
    "/scene/{scene_id}",
    summary="执行场景",
    description="执行指定场景的所有步骤，生成测试报告",
)
@limiter.limit("10/minute")
async def run_scene(
    project_id: int,
    scene_id: int,
    request: Request,
    env_id: int = Query(0),
    step_ids: str = Query("", description="可选，逗号分隔的步骤 ID，仅执行指定步骤"),
    dataset_id: int = Query(0, description="可选，数据集 ID，启用数据驱动执行"),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Execute a scene using the linear executor.

    阶段 4 增强：执行前后调用 ``MetricsCollector`` 记录耗时与错误。
    支持数据驱动：指定 dataset_id 时，遍历数据集每一行作为变量注入执行上下文。
    """
    await _validate_env(db, env_id)
    engine = None
    started = time.perf_counter()
    status_code = 200
    error_type = ""
    try:
        engine = LinearExecutor(db)
        if dataset_id:
            report_ids = await engine.execute_data_driven(
                scene_id, env_id, current_user.id, dataset_id, step_ids=step_ids
            )
            return success(
                {
                    "report_ids": report_ids,
                    "status": "running",
                    "data_driven": True,
                    "count": len(report_ids),
                }
            )
        report_id = await engine.execute(
            scene_id, env_id, current_user.id, step_ids=step_ids
        )
        return success({"report_id": report_id, "status": "running"})
    except ValueError as e:
        status_code = 404
        error_type = "ValueError"
        msg = str(e)
        if "not found" in msg.lower():
            raise_biz(ErrorCodes.SCENE_NOT_FOUND, msg)
        status_code = 500
        error_type = "InternalValueError"
        raise_biz(ErrorCodes.INTERNAL_ERROR, msg)
    except Exception:
        status_code = 500
        error_type = "InternalError"
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            collector = MetricsCollector(db)
            await collector.record_duration("scene", scene_id, elapsed_ms, project_id)
            if status_code >= 400:
                await collector.record_error(
                    "scene", scene_id, error_type or "unknown", project_id
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("记录 metrics 失败: %s", exc)
        if engine is not None:
            try:
                await engine.close()
            except (RuntimeError, ConnectionError, OSError) as e:
                logger.warning(f"引擎关闭异常: {e}")


@router.post(
    "/scene/{scene_id}/stress",
    summary="压测场景",
    description="并发压测执行场景，使用 thread_count 控制并发数，loop_count 控制总请求数",
)
@limiter.limit("5/minute")
async def run_scene_stress(
    project_id: int,
    scene_id: int,
    request: Request,
    env_id: int = Query(0),
    thread_count: int = Query(1, ge=1, le=20, description="并发线程数"),
    loop_count: int = Query(1, ge=1, description="总循环次数"),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Execute a scene in stress (concurrent) mode."""
    await _validate_env(db, env_id)
    engine = None
    try:
        engine = LinearExecutor(db)
        # 注意：当前 LinearExecutor.execute 尚未支持 thread_count/loop_count 参数，
        # 此处先接收参数供 API 兼容，待引擎支持后再传递
        report_id = await engine.execute(
            scene_id, env_id, current_user.id, concurrent=True
        )
        return success({"report_id": report_id, "status": "running", "thread_count": thread_count, "loop_count": loop_count, "stress_note": "thread_count/loop_count 参数暂未实现，当前为单线程顺序执行"})
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise_biz(ErrorCodes.SCENE_NOT_FOUND, msg)
        raise_biz(ErrorCodes.INTERNAL_ERROR, msg)
    finally:
        if engine is not None:
            try:
                await engine.close()
            except (RuntimeError, ConnectionError, OSError) as e:
                logger.warning(f"引擎关闭异常: {e}")


@router.post(
    "/step/{step_id}",
    summary="执行单步",
    description="调试执行场景中的单个步骤，不生成报告",
)
@limiter.limit("20/minute")
async def run_step(
    project_id: int,
    step_id: int,
    request: Request,
    env_id: int = Query(0),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Execute a single step."""
    await _validate_env(db, env_id)
    engine = None
    try:
        engine = LinearExecutor(db)
        result = await engine.execute_step(step_id, env_id, current_user.id)
        return success(result)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise_biz(ErrorCodes.SCENE_NOT_FOUND, msg)
        raise_biz(ErrorCodes.INTERNAL_ERROR, msg)
    finally:
        if engine is not None:
            try:
                await engine.close()
            except (RuntimeError, ConnectionError, OSError) as e:
                logger.warning(f"引擎关闭异常: {e}")


@router.post("/case/{case_id}", summary="执行用例", description="独立执行单条测试用例")
@limiter.limit("10/minute")
async def run_case(
    project_id: int,
    case_id: int,
    request: Request,
    env_id: int = Query(0),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Execute a single test case."""
    await _validate_env(db, env_id)
    engine = None
    try:
        engine = LinearExecutor(db)
        result = await engine.execute_case(case_id, env_id, current_user.id)
        return success(result)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise_biz(ErrorCodes.SCENE_NOT_FOUND, msg)
        raise_biz(ErrorCodes.INTERNAL_ERROR, msg)
    finally:
        if engine is not None:
            try:
                await engine.close()
            except (RuntimeError, ConnectionError, OSError) as e:
                logger.warning(f"引擎关闭异常: {e}")


@router.post("/all", summary="执行全部", description="批量执行项目下的所有场景")
@limiter.limit("5/minute")
async def run_all(
    project_id: int,
    request: Request,
    env_id: int = Query(0),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """Execute all scenes in a project."""
    await _validate_env(db, env_id)
    engine = None
    try:
        engine = LinearExecutor(db)
        report_ids = await engine.execute_all(project_id, env_id, current_user.id)
        return success({"report_ids": report_ids, "count": len(report_ids)})
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise_biz(ErrorCodes.SCENE_NOT_FOUND, msg)
        raise_biz(ErrorCodes.INTERNAL_ERROR, msg)
    except Exception:
        raise_biz(ErrorCodes.INTERNAL_ERROR, "批量执行场景时发生内部错误")
    finally:
        if engine is not None:
            try:
                await engine.close()
            except (RuntimeError, ConnectionError, OSError) as e:
                logger.warning(f"引擎关闭异常: {e}")


@router.get(
    "/cases/{case_id}/last-run",
    summary="获取上次执行",
    description="获取用例最近一次的执行结果",
)
async def get_case_last_run(
    project_id: int,
    case_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    """Get the last execution result for a case (for status icon display).

    通过用例关联的 api_id 查询 ApiTestHistory 表，返回最近一次执行记录。
    """
    from sqlalchemy import select
    from app.models.test_case import TestCase
    from app.models.api_test_history import ApiTestHistory

    # 查询用例获取关联的 api_id
    case_result = await db.execute(
        select(TestCase.api_id).where(
            TestCase.id == case_id,
            TestCase.project_id == project_id,
        )
    )
    api_id = case_result.scalar_one_or_none()
    if not api_id:
        return success({"found": False, "message": "用例不存在或未关联接口"})

    # 查询该接口最近一次测试历史
    history_result = await db.execute(
        select(ApiTestHistory)
        .where(ApiTestHistory.api_id == api_id)
        .order_by(ApiTestHistory.created_at.desc())
        .limit(1)
    )
    history = history_result.scalar_one_or_none()
    if not history:
        return success({"found": False, "message": "暂无执行记录"})

    return success({
        "found": True,
        "id": history.id,
        "api_id": history.api_id,
        "environment_id": history.environment_id,
        "request_url": history.request_url,
        "request_method": history.request_method,
        "response_status": history.response_status,
        "duration": history.duration,
        "status": history.status,
        "error": history.error,
        "created_at": str(history.created_at) if history.created_at else None,
    })
