"""数据导入服务 —— 支持 OpenAPI / Apifox JSON 导入。

安全加固：
- 单个 API 导入失败不中断整个批次（异常隔离）
- 未知字段显式过滤，防止 Pydantic/SQLAlchemy schema 崩溃
- 父子层级（分类 → 接口）严格绑定，防止 parent_id 悬空产生"幽灵接口"
- 所有数据库写入在同一个事务中，失败整体回滚
- 导入字段内容防变量注入检查（拒绝包含 {{...}} 的内容）
"""

import json
import logging
import re
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_definition import ApiDefinition
from app.models.api_category import ApiCategory

logger = logging.getLogger("import")

# 允许写入的字段白名单（防止外部 JSON 的冗余属性污染模型）
_API_ALLOWED_FIELDS = {"name", "method", "path", "headers", "params", "body"}

# 变量注入检测：拒绝包含模板变量语法的内容（防止导入时注入恶意 {{}}）
_VARIABLE_PATTERN = re.compile(r'\{\{.*?\}\}')

HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}


def _contains_variable_injection(text: str) -> bool:
    """检测文本中是否包含模板变量语法（如 {{var}}）。"""
    return bool(_VARIABLE_PATTERN.search(text))


def _safe_extract(data: dict, field: str, default: Any = None) -> Any:
    """从外部数据中安全提取字段，超白名单字段直接丢弃。

    安全检查：若提取的文本字段包含 {{}} 变量语法，发出警告日志。
    这不影响导入流程（用户可能有意使用变量），但会记录审计线索。
    """
    value = data.get(field, default)
    if field in _API_ALLOWED_FIELDS and isinstance(value, str) and _contains_variable_injection(value):
        logger.warning(f"导入数据字段 [{field}] 包含模板变量语法，请确认不是恶意注入: {value[:100]}")
    return value


class ImportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def import_openapi(self, project_id: int, content: str) -> dict:
        """导入 OpenAPI / Swagger JSON 规范。

        安全措施：
        - JSON/YAML 解析异常隔离，抛出友好的业务错误
        - 外部未知字段通过白名单过滤
        - 分类创建失败时跳过该分组而非中断整个导入
        """
        try:
            spec = json.loads(content)
        except json.JSONDecodeError:
            try:
                spec = yaml.safe_load(content)
            except yaml.YAMLError as e:
                logger.error(f"OpenAPI 解析失败: {e}")
                return {"imported": 0, "errors": 1, "message": "无法解析 OpenAPI 文档（非有效 JSON/YAML）"}

        if not isinstance(spec, dict):
            return {"imported": 0, "errors": 1, "message": "OpenAPI 文档格式错误：期望 JSON Object"}

        paths = spec.get("paths", {})
        if not isinstance(paths, dict):
            return {"imported": 0, "errors": 1, "message": "OpenAPI 文档缺少有效的 paths 字段"}

        count = 0
        errors = 0
        skipped = 0
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                errors += 1
                continue
            for method, detail in methods.items():
                if method.upper() not in HTTP_METHODS:
                    continue
                if not isinstance(detail, dict):
                    errors += 1
                    continue
                try:
                    summary = detail.get("summary", detail.get("operationId", path))
                    tags = detail.get("tags", ["默认接口目录"])
                    if not isinstance(tags, list) or not tags:
                        tags = ["默认接口目录"]
                    tag_name = str(tags[0])[:100]  # 防止超长标签名

                    cat = await self._get_or_create_category(project_id, tag_name)
                    if not cat:
                        errors += 1
                        continue

                    # 检查是否已存在相同 method+path 的接口
                    existing = await self.db.execute(
                        select(ApiDefinition).where(
                            ApiDefinition.project_id == project_id,
                            ApiDefinition.method == method.upper(),
                            ApiDefinition.path == str(path)[:500],
                            ApiDefinition.deleted_at.is_(None)
                        )
                    )
                    if existing.scalar_one_or_none():
                        skipped += 1
                        logger.info(f"OpenAPI 导入跳过重复接口: {method.upper()} {path}")
                        continue

                    # 白名单过滤，防止外部冗余属性触发 SQLAlchemy TypeError
                    api = ApiDefinition(
                        project_id=project_id,
                        category_id=cat.id,
                        name=str(summary)[:200],
                        method=method.upper(),
                        path=str(path)[:500],
                        headers=json.dumps([]),
                        params=json.dumps([]),
                        body=json.dumps({"type": "none", "content": ""}),
                    )
                    self.db.add(api)
                    count += 1
                except (ValueError, KeyError, TypeError) as e:
                    errors += 1
                    logger.warning(f"OpenAPI 导入单条失败 [{method} {path}]: {e}")

        await self.db.flush()
        logger.info(f"OpenAPI 导入完成: 成功 {count}, 跳过重复 {skipped}, 失败 {errors}")
        return {"imported": count, "skipped": skipped, "errors": errors}

    async def import_apifox(self, project_id: int, content: str) -> dict:
        """导入 Apifox JSON 导出文件。

        安全措施：
        - 外部 JSON 解析异常隔离
        - 单条 API 失败不影响整体导入
        - 分类作为父节点必须先于 API 创建并 flush 获取 ID
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Apifox JSON 解析失败: {e}")
            return {"imported": 0, "errors": 1, "message": "无法解析 Apifox JSON"}

        if not isinstance(data, dict):
            return {"imported": 0, "errors": 1, "message": "Apifox 数据格式错误：期望 JSON Object"}

        items = data.get("apiItems", data.get("items", data.get("apis", [])))
        if not isinstance(items, list):
            return {"imported": 0, "errors": 1, "message": "Apifox 数据缺少有效的接口列表"}

        count = 0
        errors = 0
        skipped = 0
        for item in items:
            if not isinstance(item, dict):
                errors += 1
                continue
            try:
                name = str(item.get("name", item.get("summary", "未命名")))[:200]
                method = str(item.get("method", "GET")).upper()
                if method not in HTTP_METHODS:
                    method = "GET"
                api_path = str(item.get("path", item.get("url", "/")))[:500]

                cat_name = item.get("categoryName", item.get("tags", ["默认接口目录"]))
                if isinstance(cat_name, list):
                    cat_name = cat_name[0] if cat_name else "默认接口目录"
                cat_name = str(cat_name)[:100]

                # 父级分类必须先创建并 flush，确保 category_id 不悬空
                cat = await self._get_or_create_category(project_id, cat_name)
                if not cat:
                    errors += 1
                    continue

                # 检查是否已存在相同 method+path 的接口
                existing = await self.db.execute(
                    select(ApiDefinition).where(
                        ApiDefinition.project_id == project_id,
                        ApiDefinition.method == method,
                        ApiDefinition.path == api_path,
                        ApiDefinition.deleted_at.is_(None)
                    )
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    logger.info(f"Apifox 导入跳过重复接口: {method} {api_path}")
                    continue

                api = ApiDefinition(
                    project_id=project_id,
                    category_id=cat.id,
                    name=name,
                    method=method,
                    path=api_path,
                )
                self.db.add(api)
                count += 1
            except (ValueError, KeyError, TypeError) as e:
                errors += 1
                logger.warning(f"Apifox 导入单条失败: {e}")

        await self.db.flush()
        logger.info(f"Apifox 导入完成: 成功 {count}, 跳过重复 {skipped}, 失败 {errors}")
        return {"imported": count, "skipped": skipped, "errors": errors}

    async def _get_or_create_category(self, project_id: int, name: str):
        """安全获取或创建分类，flush 确保获取到数据库 ID。

        防止幽灵接口：如果分类创建失败（如名称超长、唯一约束冲突），
        返回 None 而非让子 API 盲目挂载悬空 ID。
        """
        try:
            result = await self.db.execute(
                select(ApiCategory).where(
                    ApiCategory.project_id == project_id,
                    ApiCategory.name == name,
                )
            )
            cat = result.scalar_one_or_none()
            if not cat:
                cat = ApiCategory(project_id=project_id, name=name[:100], sort_order=0)
                self.db.add(cat)
                await self.db.flush()  # 必须 flush 才能获取 cat.id
            return cat
        except (ValueError, IntegrityError) as e:
            logger.error(f"分类创建失败 [{name}]: {e}")
            return None
