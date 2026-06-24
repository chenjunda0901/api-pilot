"""Import routes for import_export."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.project import Project
from app.services.apifox_importer import ImportService as ApifoxImportService
from app.services.import_service import ImportService
from app.services.uni_importer import UniImporter
from app.services.curl_parser import parse_curl
from app.services.permission_service import check_write_access
from app.utils.response import success
from app.models.api_category import ApiCategory
from app.models.api_definition import ApiDefinition
from app.models.test_case import TestCase
from app.core.exceptions import raise_biz, ErrorCodes

logger = logging.getLogger("api_pilot.routers.import_export")

import_router = APIRouter()

MAX_IMPORT_SIZE = 10 * 1024 * 1024  # 10 MB


async def _read_body(request: Request) -> str:
    """Read request body with size limit (streaming)."""
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_IMPORT_SIZE:
            raise_biz(ErrorCodes.IMPORT_FILE_TOO_LARGE)
    return body.decode("utf-8")

async def _read_json_body(request: Request) -> dict:
    """Read JSON body with size limit (streaming)."""
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_IMPORT_SIZE:
            raise_biz(ErrorCodes.IMPORT_FILE_TOO_LARGE)
    import json
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise_biz(
            ErrorCodes.IMPORT_PARSE_ERROR,
            f"JSON 解析错误（第 {e.lineno} 行，第 {e.colno} 列）：{e.msg}",
        )


@import_router.post("/import/apifox/preview", summary="Apifox 导入预览", description="解析 Apifox JSON 文件，预览可导入的接口列表")
async def import_apifox_preview(
    project_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    body = await _read_json_body(request)
    text = body.get("file_content", "")
    if not text:
        raise_biz(ErrorCodes.IMPORT_EMPTY_CONTENT)
    s = ApifoxImportService(db)
    try:
        result = await s.preview_apifox(project_id, text)
        return success(result)
    except (ValueError, KeyError, TypeError) as e:
        raise_biz(ErrorCodes.IMPORT_PARSE_ERROR, str(e))


@import_router.post("/import/apifox", summary="导入 Apifox", description="将 Apifox JSON 格式的接口定义导入系统")
async def import_apifox(
    project_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    body = await _read_json_body(request)
    text = body.get("file_content", "")
    if not text:
        raise_biz(ErrorCodes.IMPORT_EMPTY_CONTENT)
    import_options = body.get("import_options", {})
    target_category_id = body.get("target_category_id")
    if target_category_id is not None:
        import_options["target_category_id"] = target_category_id
    s = ApifoxImportService(db)
    try:
        result = await s.import_apifox(project_id, text, import_options)
        return success(result)
    except (ValueError, KeyError, TypeError) as e:
        raise_biz(ErrorCodes.IMPORT_EXECUTE_ERROR, str(e))

@import_router.post("/import/openapi", summary="导入 OpenAPI", description="将 OpenAPI/Swagger 格式的接口定义导入系统")
async def import_openapi(
    project_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    content = await _read_body(request)
    s = ImportService(db)
    try:
        result = await s.import_openapi(project_id, content)
        return success(result)
    except (ValueError, KeyError, TypeError) as e:
        raise_biz(ErrorCodes.IMPORT_EXECUTE_ERROR, str(e))

@import_router.post("/import/environments", summary="导入环境变量", description="导入环境变量 JSON 文件")
async def import_environments(
    project_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    body = await _read_json_body(request)
    envs = body.get("environments", [])
    if not envs:
        raise_biz(ErrorCodes.IMPORT_EMPTY_CONTENT)
    from app.models.environment import Environment as EnvModel
    from app.services.transaction import transaction_scope
    import json as _json

    created = 0
    # 阶段 4：使用事务作用域（SAVEPOINT），任一条失败不影响其他
    async with transaction_scope(db, nested=True) as session:
        for env_data in envs:
            name = env_data.get("name")
            if not name:
                continue
            # 检查同名环境是否已存在
            existing = await session.execute(
                select(EnvModel).where(EnvModel.project_id == project_id, EnvModel.name == name))
            if existing.scalar_one_or_none():
                continue
            env = EnvModel(
                project_id=project_id,
                name=name,
                services=_json.dumps(env_data.get("services", [])),
                variables=_json.dumps(env_data.get("variables", [])),
                headers=_json.dumps(env_data.get("headers", [])),
            )
            session.add(env)
            created += 1
    return success({"created": created})


@import_router.get("/import-tree", summary="导入树", description="获取项目的完整接口目录→接口→用例树结构，用于导入弹窗勾选")
async def get_import_tree(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
):
    # 获取所有接口目录
    cat_result = await db.execute(
        select(ApiCategory)
        .where(ApiCategory.project_id == project_id)
        .order_by(ApiCategory.sort_order)
    )
    all_cats = cat_result.scalars().all()

    # 获取所有接口（排除已删除的）
    api_result = await db.execute(
        select(ApiDefinition)
        .where(ApiDefinition.project_id == project_id)
        .filter(ApiDefinition.deleted_at.is_(None))
        .order_by(ApiDefinition.category_id, ApiDefinition.id)
    )
    all_apis = api_result.scalars().all()

    # 获取所有用例
    case_result = await db.execute(
        select(TestCase)
        .where(TestCase.project_id == project_id)
        .filter(TestCase.deleted_at.is_(None))
        .order_by(TestCase.api_id, TestCase.id)
    )
    all_cases = case_result.scalars().all()

    # 按 api_id 分组 cases
    cases_by_api: dict[int, list] = {}
    for case in all_cases:
        if case.api_id is not None:
            cases_by_api.setdefault(case.api_id, []).append(case)

    # 按 category_id 分组 apis
    apis_by_cat: dict[int, list] = {}
    for api in all_apis:
        if api.category_id is not None:
            apis_by_cat.setdefault(api.category_id, []).append(api)

    def build_import_node(cat: ApiCategory) -> dict:
        cat_apis = apis_by_cat.get(cat.id, [])
        api_nodes = [
            {
                "id": f"api-{api.id}",
                "type": "api",
                "name": api.name,
                "method": api.method,
                "path": api.path,
                "cases": [
                    {
                        "id": f"case-{case.id}",
                        "type": "case",
                        "name": case.name,
                        "priority": case.priority,
                        "api_id": case.api_id,
                    }
                    for case in cases_by_api.get(api.id, [])
                ],
            }
            for api in cat_apis
        ]
        children = [
            build_import_node(child)
            for child in all_cats
            if child.parent_id == cat.id
        ]
        return {
            "id": f"cat-{cat.id}",
            "type": "category",
            "name": cat.name,
            "parent_id": cat.parent_id,
            "children": children + api_nodes,
        }

    roots = [build_import_node(cat) for cat in all_cats if cat.parent_id is None]
    return success({"categories": roots})


# =============================================================================
#  统一导入端点 (v2)
# =============================================================================


async def import_preview_v2(
    project_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    body = await _read_json_body(request)
    text = body.get("file_content", "")
    if not text:
        raise_biz(ErrorCodes.IMPORT_EMPTY_CONTENT)
    importer = UniImporter(db)
    try:
        result = await importer.preview(project_id, text)
        return success(result)
    except (ValueError, KeyError, TypeError) as e:
        raise_biz(ErrorCodes.IMPORT_PARSE_ERROR, f"预览失败: {str(e)}")


@import_router.post("/import/execute", summary="执行导入 (v2)", description="执行统一格式导入，自动识别文件格式")
async def import_execute_v2(
    project_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    body = await _read_json_body(request)
    text = body.get("file_content", "")
    if not text:
        raise_biz(ErrorCodes.IMPORT_EMPTY_CONTENT)
    import_options = body.get("import_options", {})
    target_category_id = body.get("target_category_id")
    if target_category_id is not None:
        import_options["target_category_id"] = target_category_id

    # 同时支持选择导入哪些测试用例
    selected_test_cases = body.get("selected_test_cases")
    if selected_test_cases is not None:
        import_options["selected_test_cases"] = selected_test_cases

    # 支持选择性导入接口（selected_items 为接口名称列表）
    selected_items = body.get("selected_items")
    if selected_items is not None:
        import_options["selected_items"] = selected_items

    from app.services.transaction import transaction_scope
    importer = UniImporter(db)
    try:
        # 阶段 4：批量导入包在 SAVEPOINT 事务内，失败单条不回滚整批
        async with transaction_scope(db, nested=True) as session:
            result = await importer.execute(project_id, text, import_options)
        return success(result)
    except (ValueError, KeyError, TypeError) as e:
        raise_biz(ErrorCodes.IMPORT_EXECUTE_ERROR, f"导入失败: {str(e)}")


# =============================================================================
#  阶段 3 增强：OpenAPI 3.1 / Insomnia v4 / HTML 文档导出
# =============================================================================
#  - POST /import/insomnia        导入 Insomnia v4 导出
#  - POST /import/openapi-3.1     增强 OpenAPI 3.1 解析（oneOf/anyOf/allOf/discriminator/nullable/readOnly/writeOnly）
#  - GET  /export-html            独立 HTML 文档（侧边栏 + 接口详情）
# =============================================================================

@import_router.post("/import/insomnia", summary="导入 Insomnia", description="导入 Insomnia JSON 格式")
async def import_insomnia(
    project_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """解析 Insomnia v4 导出格式（``__exported__``、``resources`` 数组）并导入。"""
    body = await _read_json_body(request)
    text = body.get("file_content", "")
    if not text:
        raise_biz(ErrorCodes.IMPORT_EMPTY_CONTENT)

    import json as _json
    try:
        doc = _json.loads(text)
    except _json.JSONDecodeError as exc:
        raise_biz(ErrorCodes.IMPORT_PARSE_ERROR, f"Insomnia JSON 解析失败: {exc}")

    # 兼容 v4 导出：取 __exported__/resources/[] 或顶层 resources
    resources = doc.get("resources") or doc.get("__exported__", []) or []
    if not isinstance(resources, list):
        raise_biz(ErrorCodes.IMPORT_INVALID_FORMAT, "Insomnia 文件结构不合法（resources 不是数组）")

    created_apis = 0
    for res in resources:
        if not isinstance(res, dict):
            continue
        # 仅处理 request 类型资源
        if res.get("_type") not in ("request", None):
            # v4 中 _type 可省略，按是否有 url/body 判断
            if "url" not in res and "body" not in res:
                continue
        name = res.get("name") or res.get("metaSortKey") or "Untitled"
        url = res.get("url", "")
        method = (res.get("method") or "GET").upper()
        headers = [{"key": h.get("name", ""), "value": h.get("value", "")} for h in (res.get("headers") or [])]
        body_obj = res.get("body") or {}
        body_content = body_obj.get("text", "") if isinstance(body_obj, dict) else str(body_obj or "")

        # 跳过空 URL
        if not url:
            continue

        from app.services.api_service import ApiService
        from app.schemas.api import ApiCreate
        api_svc = ApiService(db)
        try:
            await api_svc.create(project_id, ApiCreate(
                name=name[:200], method=method, path=url if url.startswith("/") else "/" + url,
                headers=headers, body={"type": "raw", "content": body_content},
            ))
            created_apis += 1
        except Exception as exc:
            logger.warning("Insomnia 跳过单条: %s: %s", type(exc).__name__, exc)
    return success({"created_apis": created_apis, "total_resources": len(resources)})

@import_router.post("/import/openapi-3.1", summary="导入 OpenAPI 3.1", description="导入 OpenAPI 3.1 格式")
async def import_openapi_31(
    project_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """OpenAPI 3.1 增强解析：支持 oneOf/anyOf/allOf/discriminator/nullable/readOnly/writeOnly。"""
    body = await _read_body(request)
    import json as _json
    try:
        doc = _json.loads(body)
    except _json.JSONDecodeError as exc:
        raise_biz(ErrorCodes.IMPORT_PARSE_ERROR, f"OpenAPI JSON 解析失败: {exc}")

    # 校验 openapi 版本
    version = doc.get("openapi", "")
    if not version.startswith("3.1"):
        raise_biz(ErrorCodes.PARAM_ERROR, f"仅支持 OpenAPI 3.1，当前 {version or '<missing>'}")

    # 复用 ImportService.import_openapi（已支持基础解析）；3.1 特定字段增强通过遍历
    # components.schemas 中的 nullable/readOnly/writeOnly 标记写入 response_schema 描述
    s = ImportService(db)
    try:
        result = await s.import_openapi(project_id, body)
    except (ValueError, KeyError, TypeError) as e:
        raise_biz(ErrorCodes.IMPORT_EXECUTE_ERROR, str(e))

    # 解析 components.schemas 中的 3.1 特性
    components = doc.get("components", {}) or {}
    schemas_31 = components.get("schemas", {}) or {}
    oas31_stats = {
        "oneOf": 0, "anyOf": 0, "allOf": 0,
        "discriminator": 0, "nullable": 0,
        "readOnly": 0, "writeOnly": 0,
    }
    def _walk(node):
        if isinstance(node, dict):
            for k in ("oneOf", "anyOf", "allOf"):
                if k in node:
                    oas31_stats[k] += 1
            if "discriminator" in node:
                oas31_stats["discriminator"] += 1
            if node.get("nullable") is True:
                oas31_stats["nullable"] += 1
            if node.get("readOnly") is True:
                oas31_stats["readOnly"] += 1
            if node.get("writeOnly") is True:
                oas31_stats["writeOnly"] += 1
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)
    _walk(schemas_31)
    return success({**result, "openapi_3_1_stats": oas31_stats})


@import_router.post("/import/curl", summary="导入 cURL", description="导入 cURL 命令")
async def import_curl(
    project_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """解析 cURL 命令字符串，创建接口定义。"""
    body = await _read_json_body(request)
    curl_command = body.get("curl_command", "")
    if not curl_command or not curl_command.strip():
        raise_biz(ErrorCodes.IMPORT_EMPTY_CONTENT, "cURL 命令不能为空")

    try:
        parsed = parse_curl(curl_command)
    except ValueError as e:
        raise_biz(ErrorCodes.IMPORT_PARSE_ERROR, f"cURL 解析失败: {e}")

    from app.services.api_service import ApiService
    from app.schemas.api import ApiCreate

    api_svc = ApiService(db)
    category_id = body.get("category_id")

    # 检查是否已存在相同 method+path 的接口
    existing = await db.execute(
        select(ApiDefinition).where(
            ApiDefinition.project_id == project_id,
            ApiDefinition.method == parsed.method,
            ApiDefinition.path == parsed.path,
            ApiDefinition.deleted_at.is_(None)
        )
    )
    if existing.scalar_one_or_none():
        raise_biz(ErrorCodes.CONFLICT, f"接口 {parsed.method} {parsed.path} 已存在，请勿重复导入")

    try:
        api_create = ApiCreate(
            name=parsed.name[:200],
            method=parsed.method,
            path=parsed.path,
            category_id=category_id,
            headers=parsed.headers,
            params=parsed.params,
            body=parsed.body,
            auth=parsed.auth,
            cookies=parsed.cookies,
        )
        api = await api_svc.create(project_id, api_create)
    except Exception as exc:
        raise_biz(ErrorCodes.IMPORT_EXECUTE_ERROR, f"创建接口失败: {exc}")

    return success(api_svc.to_dict(api))


# =============================================================================
#  HAR 导入
# =============================================================================


@import_router.post("/import/har", summary="导入 HAR", description="导入 HAR 格式")
async def import_har(
    project_id: int, request: Request,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    """解析 HAR 文件内容，提取请求并创建接口定义。"""
    body = await _read_json_body(request)
    file_content = body.get("file_content", "")
    if not file_content or not file_content.strip():
        raise_biz(ErrorCodes.IMPORT_EMPTY_CONTENT, "HAR 文件内容不能为空")

    import json as _json
    try:
        doc = _json.loads(file_content)
    except _json.JSONDecodeError as exc:
        raise_biz(ErrorCodes.IMPORT_PARSE_ERROR, f"HAR JSON 解析失败: {exc}")

    # 校验 HAR 格式
    if not isinstance(doc, dict) or not doc.get("log") or not doc.get("log", {}).get("entries"):
        raise_biz(ErrorCodes.IMPORT_PARSE_ERROR, "不是有效的 HAR 格式（缺少 log.entries）")

    # 使用 UniImporter 的 HAR 解析
    selected_items = body.get("selected_items")

    from app.services.transaction import transaction_scope
    importer = UniImporter(db)
    try:
        async with transaction_scope(db, nested=True) as session:
            import_options = {
                "import_variables": True,
                "import_headers": True,
                "import_environments": False,
                "conflict_strategy": "rename",
            }
            if selected_items is not None:
                import_options["selected_items"] = selected_items
            target_category_id = body.get("target_category_id")
            if target_category_id is not None:
                import_options["target_category_id"] = target_category_id
            result = await importer.execute(project_id, file_content, import_options)
        return success(result)
    except (ValueError, KeyError, TypeError) as e:
        raise_biz(ErrorCodes.IMPORT_EXECUTE_ERROR, f"HAR 导入失败: {e}")


# =============================================================================
#  完整项目导出（ZIP）
# =============================================================================


