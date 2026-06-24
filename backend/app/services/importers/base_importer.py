"""API导入器基类 - 统一导入逻辑

提供所有API导入器的公共功能：
- JSON/YAML文件解析
- 分类树构建
- 变量和Header合并
- 错误处理
- 进度追踪
- 预览树构建
- 重复检测
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_definition import ApiDefinition

logger = logging.getLogger(__name__)


class BaseApiImporter(ABC):
    """API导入器抽象基类

    所有导入器（Apifox、OpenAPI、Postman等）都应继承此类。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.stats = {
            "imported": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
        }

    @abstractmethod
    async def import_data(self, project_id: int, raw_data: Any, **options) -> dict:
        """导入API数据（必须实现）

        Args:
            project_id: 目标项目ID
            raw_data: 原始数据（JSON dict或YAML dict）
            **options: 额外选项

        Returns:
            导入结果统计
        """
        raise NotImplementedError

    def _parse_json(self, content: str) -> dict:
        """解析JSON字符串

        Args:
            content: JSON字符串

        Returns:
            解析后的字典

        Raises:
            ValueError: JSON解析失败
        """
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")

    def _merge_variables(self, existing: list, new: list) -> list:
        """合并变量列表（去重）

        Args:
            existing: 现有变量列表
            new: 新变量列表

        Returns:
            合并后的变量列表
        """
        existing_keys = {v["key"] for v in existing if isinstance(v, dict) and v.get("key")}
        merged = list(existing)

        for var in new:
            if isinstance(var, dict) and var.get("key"):
                if var["key"] not in existing_keys:
                    merged.append(var)
                    existing_keys.add(var["key"])

        return merged

    def _merge_headers(self, existing: list, new: list) -> list:
        """合并Header列表（去重）

        Args:
            existing: 现有Header列表
            new: 新Header列表

        Returns:
            合并后的Header列表
        """
        existing_keys = {h["key"] for h in existing if isinstance(h, dict) and h.get("key")}
        merged = list(existing)

        for header in new:
            if isinstance(header, dict) and header.get("key"):
                if header["key"] not in existing_keys:
                    merged.append(header)
                    existing_keys.add(header["key"])

        return merged

    def _build_category_tree(self, categories: list[dict]) -> dict[int, dict]:
        """构建分类树并返回ID映射

        Args:
            categories: 分类列表

        Returns:
            {category_id: category_dict} 映射
        """
        cat_map = {}
        for cat in categories:
            if isinstance(cat, dict) and cat.get("id"):
                cat_map[cat["id"]] = cat
        return cat_map

    def _build_preview_tree(self, categories: list[dict], apis: list[dict]) -> list[dict]:
        """构建预览树结构（分类 + API列表）

        Args:
            categories: 分类列表
            apis: API列表

        Returns:
            预览树结构
        """
        cat_map = {c["id"]: c for c in categories if isinstance(c, dict) and c.get("id")}

        # 构建分类树
        tree = []
        children_map: dict[int, list] = {}

        for cat in categories:
            if not isinstance(cat, dict):
                continue
            parent_id = cat.get("parent_id")
            if parent_id:
                children_map.setdefault(parent_id, []).append(cat)
            else:
                tree.append(cat)

        def _add_children(node: dict) -> dict:
            """递归添加子分类"""
            children = children_map.get(node["id"], [])
            if children:
                node["children"] = [_add_children(c) for c in children]
            return node

        tree = [_add_children(c) for c in tree]

        # 为每个分类添加API列表
        for cat in categories:
            if not isinstance(cat, dict):
                continue
            cat_apis = [a for a in apis if a.get("category_id") == cat.get("id")]
            if cat_apis:
                cat["apis"] = cat_apis

        # 添加无分类的API
        uncategorized = [a for a in apis if not a.get("category_id")]
        if uncategorized:
            tree.append({
                "id": 0,
                "name": "未分类",
                "children": [],
                "apis": uncategorized,
            })

        return tree

    async def _mark_existing_apis(self, project_id: int, api_refs: list[dict]) -> set:
        """标记已存在的API（通过apifox_id或其他唯一标识）

        Args:
            project_id: 项目ID
            api_refs: API引用列表

        Returns:
            已存在API的ID集合
        """
        if not api_refs:
            return set()

        # 收集所有外部ID
        external_ids = []
        for ref in api_refs:
            if isinstance(ref, dict) and ref.get("external_id"):
                external_ids.append(ref["external_id"])

        if not external_ids:
            return set()

        # 查询数据库中已存在的API
        result = await self.db.execute(
            select(ApiDefinition.id, ApiDefinition.apifox_id).where(
                ApiDefinition.project_id == project_id,
                ApiDefinition.apifox_id.in_(external_ids),
            )
        )
        existing = {row[1] for row in result.fetchall() if row[1]}
        return existing

    def _log_progress(self, message: str, level: str = "info"):
        """记录导入进度

        Args:
            message: 进度消息
            level: 日志级别
        """
        log_fn = getattr(logger, level, logger.info)
        log_fn(f"[Import] {message}")

    def _record_error(self, error: Exception, context: str = ""):
        """记录导入错误

        Args:
            error: 异常对象
            context: 错误上下文
        """
        self.stats["failed"] += 1
        error_msg = f"{context}: {error}" if context else str(error)
        self.stats["errors"].append(error_msg)
        logger.warning(f"[Import Error] {error_msg}")

    def get_stats(self) -> dict:
        """获取导入统计

        Returns:
            包含导入统计信息的字典
        """
        return {
            **self.stats,
            "total": self.stats["imported"] + self.stats["skipped"] + self.stats["failed"],
        }
