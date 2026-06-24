"""Mock 规则管理与 Mock 请求入口"""

import asyncio
import hashlib
import json
import time
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.project import Project
from app.schemas.mock import MockRuleCreate, MockRuleUpdate, MockTestRequest, SchemaMockRequest
from app.services.mock_service import MockService
from app.services.permission_service import check_read_access, check_write_access
from app.utils.json_helpers import safe_json_load
from app.utils.response import success, fail

router = APIRouter(prefix="/projects/{project_id}/mock-rules", tags=["Mock Rules"])


@router.post("/generate-from-api/{api_id}", summary="从 API 生成 Mock 规则", description="基于 API 定义自动生成 Mock 规则（响应示例、匹配路径）")
async def generate_from_api(
    project_id: int,
    api_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    return success(s.to_dict(await s.generate_from_api(project_id, api_id)))


@router.post("/batch-generate", summary="批量生成 Mock 规则", description="从项目所有（或指定）API 批量生成 Mock 规则，跳过已有规则的 API")
async def batch_generate(
    project_id: int,
    api_ids: list[int] | None = None,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    count = await s.batch_generate_from_apis(project_id, api_ids)
    return success({"generated_count": count})


@router.get("", summary="Mock 规则列表", description="获取项目的 Mock 规则列表")
async def list_rules(
    project_id: int,
    method: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    items, total = await s.list(project_id, method, page, page_size)
    return success(
        {"items": items, "total": total, "page": page, "page_size": page_size}
    )


@router.get(
    "/statistics", summary="Mock 服务统计", description="获取项目的 Mock 规则命中统计"
)
async def get_statistics(
    project_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    stats = await s.get_statistics(project_id)
    return success(stats)


@router.post(
    "/generate-from-schema",
    summary="从 JSON Schema 生成 Mock 数据",
    description="根据 JSON Schema 自动生成符合约束的 Mock 数据",
)
async def generate_from_schema(
    project_id: int,
    req: SchemaMockRequest,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    data = MockService.generate_mock_from_schema(req.json_schema)
    return success(data)


@router.get(
    "/call-logs",
    summary="Mock 调用日志",
    description="获取项目的 Mock 调用日志列表，支持分页和过滤",
)
async def list_call_logs(
    project_id: int,
    rule_id: int = Query(None, description="按规则 ID 过滤"),
    start_date: str = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(None, description="结束日期 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    items, total = await s.list_call_logs(
        project_id, rule_id=rule_id, start_date=start_date,
        end_date=end_date, page=page, page_size=page_size,
    )
    return success({"items": items, "total": total, "page": page, "page_size": page_size})


@router.delete(
    "/call-logs",
    summary="清除 Mock 调用日志",
    description="清除项目的所有 Mock 调用日志",
)
async def clear_call_logs(
    project_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    count = await s.clear_call_logs(project_id)
    return success({"deleted_count": count})


@router.get(
    "/statistics/call-trend",
    summary="Mock 调用趋势",
    description="获取最近 7 天的 Mock 调用趋势数据",
)
async def get_call_trend(
    project_id: int,
    days: int = Query(7, ge=1, le=30),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    trend = await s.get_call_trend(project_id, days)
    return success(trend)


@router.get(
    "/statistics/match-rate",
    summary="Mock 匹配率",
    description="获取 Mock 规则匹配率统计",
)
async def get_match_rate(
    project_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    rate = await s.get_match_rate(project_id)
    return success(rate)


mock_test_router = APIRouter(prefix="/mock", tags=["Mock Test"])


@mock_test_router.post(
    "/test",
    summary="测试 Mock 规则匹配",
    description="测试 Mock 规则匹配并返回模拟响应",
)
async def mock_test(req: MockTestRequest, db: AsyncSession = Depends(get_db)):
    from app.services.mock_service import MockService

    service = MockService(db)
    result = await service.test_mock(req)
    return success(result)


@router.post(
    "",
    summary="创建 Mock 规则",
    description="新建 Mock 规则（匹配条件、响应内容、脚本）",
)
async def create_rule(
    project_id: int,
    req: MockRuleCreate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    result = s.to_dict(await s.create(project_id, req))
    return success(result)


@router.put(
    "/{rule_id}",
    summary="更新 Mock 规则",
    description="修改 Mock 规则的匹配条件、响应配置、脚本等",
)
async def update_rule(
    project_id: int,
    rule_id: int,
    req: MockRuleUpdate,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    result = s.to_dict(await s.update(rule_id, req))
    return success(result)


@router.delete(
    "/{rule_id}", summary="删除 Mock 规则", description="删除指定的 Mock 规则"
)
async def delete_rule(
    project_id: int,
    rule_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = MockService(db)
    await s.delete(rule_id)
    return success(message="规则已删除")


mock_request_router = APIRouter(prefix="/mock", tags=["Mock Request Entry"])


from app.limiter import limiter


@mock_request_router.api_route(
    "/{project_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
@limiter.limit("60/minute")
async def mock_entry(
    project_id: int, path: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Mock 请求入口（支持条件匹配 + 脚本响应）"""
    start_time = time.time()
    project = await db.get(Project, project_id)
    if not project:
        return fail(404, "Project not found")

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        from app.middleware.auth import decode_token

        token = auth_header[len("Bearer ") :]
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            from sqlalchemy import select

            user_id = int(payload["sub"])
            from app.models.user import User as UserModel

            user_result = await db.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                from app.services.permission_service import PermissionService

                try:
                    await PermissionService(db).check_project_access(
                        project_id, user, require_write=False
                    )
                except (PermissionError, ValueError):
                    return fail(403, "您没有该 Mock 项目的访问权限")
            else:
                # 用户不存在或 token 无效，私有项目拒绝访问
                if not project.is_public:
                    return fail(403, "私有项目的 Mock 服务需要认证")
        else:
            # token 无效或非 access 类型，私有项目拒绝访问
            if not project.is_public:
                return fail(403, "私有项目的 Mock 服务需要认证")
    else:
        # 未携带 Authorization 头
        if not project.is_public:
            return fail(403, "私有项目的 Mock 服务需要认证")

    s = MockService(db)

    # 构建请求数据供条件匹配
    from urllib.parse import parse_qs

    query_data = {}
    if request.url.query:
        qs = parse_qs(request.url.query)
        query_data = {k: v[0] if len(v) == 1 else v for k, v in qs.items()}

    # 提取请求头（排除内部头）
    request_headers = {
        k: v for k, v in dict(request.headers).items()
        if k.lower() not in ("authorization", "host", "content-length")
    }

    request_data = {
        "query": query_data,
        "headers": dict(request.headers),
    }

    # 尝试解析 body
    try:
        body_bytes = await request.body()
        if body_bytes:
            import json as _json

            request_data["body"] = _json.loads(body_bytes)
    except (ValueError, UnicodeDecodeError):
        request_data["body"] = None

    rule = await s.match(project_id, request.method, f"/{path}", request_data)

    # 计算响应
    if not rule:
        duration_ms = int((time.time() - start_time) * 1000)
        # 记录未命中日志
        try:
            await s.record_call_log(
                project_id=project_id,
                mock_rule_id=None,
                request_method=request.method,
                request_path=f"/{path}",
                request_headers=request_headers,
                request_query=query_data,
                matched_rule_name=None,
                response_status=404,
                response_body_hash=None,
                duration_ms=duration_ms,
            )
        except Exception:
            pass  # 日志记录失败不影响响应
        return fail(404, "No matching mock rule")

    if rule.response_delay > 0:
        await asyncio.sleep(rule.response_delay / 1000.0)

    headers = safe_json_load(rule.response_headers, {})
    resp_body = s.build_response_body(rule, request_data)

    duration_ms = int((time.time() - start_time) * 1000)

    # 计算响应体哈希
    resp_body_str = json.dumps(resp_body, ensure_ascii=False) if isinstance(resp_body, (dict, list)) else str(resp_body)
    resp_body_hash = hashlib.sha256(resp_body_str.encode()).hexdigest()

    # 记录命中日志
    try:
        await s.record_call_log(
            project_id=project_id,
            mock_rule_id=rule.id,
            request_method=request.method,
            request_path=f"/{path}",
            request_headers=request_headers,
            request_query=query_data,
            matched_rule_name=rule.name,
            response_status=rule.response_status,
            response_body_hash=resp_body_hash,
            duration_ms=duration_ms,
        )
    except Exception:
        pass  # 日志记录失败不影响响应

    from fastapi.responses import JSONResponse, Response

    content_type = headers.get("content-type", "") if isinstance(headers, dict) else ""

    if isinstance(resp_body, dict):
        return JSONResponse(
            content=resp_body,
            status_code=rule.response_status,
            headers=headers if isinstance(headers, dict) else {},
        )
    elif isinstance(resp_body, str):
        if resp_body.strip().startswith(("{", "[")):
            try:
                import json as _json

                return JSONResponse(
                    content=_json.loads(resp_body),
                    status_code=rule.response_status,
                    headers=headers if isinstance(headers, dict) else {},
                )
            except (ValueError, UnicodeDecodeError):
                pass
        return Response(
            content=resp_body,
            status_code=rule.response_status,
            headers=headers if isinstance(headers, dict) else {},
        )
    else:
        return JSONResponse(
            content={"data": resp_body},
            status_code=rule.response_status,
            headers=headers if isinstance(headers, dict) else {},
        )
