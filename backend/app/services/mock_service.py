from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from functools import lru_cache

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes
from app.models.mock_rule import MockRule
from app.utils.json_helpers import safe_json_load
import builtins

logger = logging.getLogger("mock")

_MATCH_CACHE_MAX_PROJECTS = 256


@lru_cache(maxsize=_MATCH_CACHE_MAX_PROJECTS)
def _build_pattern(rule_path: str) -> re.Pattern:
    """编译 Mock 路径匹配模式为正则对象（LRU 缓存）。"""
    if rule_path == '*':
        return re.compile(r'.*')
    pattern = re.escape(rule_path)
    pattern = re.sub(r'\\{(\w+)\\}', r'[^/]+', pattern) + '$'
    return re.compile(pattern)


class MockService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def to_dict(self, r: MockRule) -> dict:
        d = {
            "id": r.id, "project_id": r.project_id, "name": r.name,
            "enabled": bool(r.enabled), "priority": r.priority,
            "match_method": r.match_method, "match_path": r.match_path,
            "response_status": r.response_status,
            "response_headers": safe_json_load(r.response_headers, {}),
            "response_body": r.response_body,
            "response_delay": r.response_delay,
            "conditions": safe_json_load(r.conditions, []),
            "script": r.script,
            "hit_count": r.hit_count,
            "created_at": str(r.created_at), "updated_at": str(r.updated_at),
        }
        return d

    async def list(self, project_id: int, method: str | None = None, page: int = 1, page_size: int = 20) -> tuple:
        query = select(MockRule).where(MockRule.project_id == project_id)
        count_query = select(func.count(MockRule.id)).where(MockRule.project_id == project_id)
        if method:
            query = query.where(MockRule.match_method == method)
            count_query = count_query.where(MockRule.match_method == method)
        total = await self.db.scalar(count_query) or 0
        result = await self.db.execute(
            query.order_by(MockRule.priority.desc(), MockRule.id.desc())
            .offset((page-1)*page_size).limit(page_size))
        return [self.to_dict(r) for r in result.scalars().all()], total

    async def get(self, rule_id: int) -> MockRule:
        result = await self.db.execute(select(MockRule).where(MockRule.id == rule_id))
        r = result.scalar_one_or_none()
        if not r:
            raise_biz(ErrorCodes.MOCK_NOT_FOUND)
        return r

    async def create(self, project_id: int, req) -> MockRule:
        rule = MockRule(
            project_id=project_id, name=req.name,
            enabled=getattr(req, 'enabled', True),
            priority=getattr(req, 'priority', 0),
            match_method=getattr(req, 'match_method', '*'),
            match_path=getattr(req, 'match_path', '/'),
            response_status=getattr(req, 'response_status', 200),
            response_headers=json.dumps(getattr(req, 'response_headers', {})),
            response_body=getattr(req, 'response_body', ''),
            response_delay=getattr(req, 'response_delay', 0),
            conditions=self._serialize_conditions(getattr(req, 'conditions', None)),
            script=getattr(req, 'script', None),
        )
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def update(self, rule_id: int, req) -> MockRule:
        rule = await self.get(rule_id)
        if req.name:
            rule.name = req.name
        if hasattr(req, 'enabled'):
            rule.enabled = req.enabled
        rule.priority = getattr(req, 'priority', rule.priority)
        rule.match_method = getattr(req, 'match_method', rule.match_method)
        rule.match_path = getattr(req, 'match_path', rule.match_path)
        rule.response_status = getattr(req, 'response_status', rule.response_status)
        raw_headers = getattr(req, 'response_headers', None)
        if raw_headers is not None:
            rule.response_headers = json.dumps(raw_headers)
        raw_body = getattr(req, 'response_body', None)
        if raw_body is not None:
            rule.response_body = raw_body
        rule.response_delay = getattr(req, 'response_delay', rule.response_delay)
        # 新字段
        if hasattr(req, 'conditions') and req.conditions is not None:
            rule.conditions = self._serialize_conditions(req.conditions)
        if hasattr(req, 'script') and req.script is not None:
            rule.script = req.script
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    @staticmethod
    def _serialize_conditions(conditions) -> str | None:
        """把 Pydantic 列表 / dict 列表统一序列化为 JSON 字符串。"""
        if not conditions:
            return None
        normalized = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in conditions
        ]
        return json.dumps(normalized, ensure_ascii=False)

    async def delete(self, rule_id: int):
        rule = await self.get(rule_id)
        await self.db.delete(rule)
        await self.db.flush()

    async def increment_hit_count(self, rule_id: int):
        """原子递增命中计数"""
        await self.db.execute(
            update(MockRule)
            .where(MockRule.id == rule_id)
            .values(hit_count=MockRule.hit_count + 1)
        )

    async def match(self, project_id: int, method: str, path: str,
                    request_data: dict | None = None) -> MockRule | None:
        """按优先级匹配 Mock 规则，支持条件过滤"""
        result = await self.db.execute(
            select(MockRule).where(
                MockRule.project_id == project_id, MockRule.enabled == 1
            ).order_by(MockRule.priority.desc(), MockRule.id.asc()))
        rules = result.scalars().all()
        for rule in rules:
            if not self._path_match(rule.match_method, rule.match_path, method, path):
                continue
            # 条件评估
            if rule.conditions:
                if not self._evaluate_conditions(rule.conditions, request_data or {}):
                    continue
            # 命中，递增计数
            await self.increment_hit_count(rule.id)
            return rule
        return None

    def _path_match(self, rule_method: str, rule_path: str, req_method: str, req_path: str) -> bool:
        if rule_method != '*' and rule_method.upper() != req_method.upper():
            return False
        pattern = _build_pattern(rule_path)
        return bool(pattern.match(req_path))

    def _evaluate_conditions(self, conditions_json: str, request_data: dict) -> bool:
        """评估条件表达式列表"""
        try:
            conditions = json.loads(conditions_json)
        except (json.JSONDecodeError, TypeError):
            return False
        if not isinstance(conditions, list):
            return False
        for cond in conditions:
            field_path = cond.get("field", "")
            operator = cond.get("operator", "equals")
            expected = cond.get("value", "")
            actual = self._resolve_field(field_path, request_data)
            if not self._match_operator(actual, operator, expected):
                return False
        return True

    def _resolve_field(self, field_path: str, data: dict):
        """解析 query.*, header.*, body.* 路径"""
        parts = field_path.split(".", 1)
        source = data.get(parts[0], {})
        if len(parts) > 1 and isinstance(source, dict):
            for p in parts[1].split("."):
                if isinstance(source, dict):
                    source = source.get(p)
                else:
                    return None
        return source

    def _match_operator(self, actual, operator: str, expected) -> bool:
        """支持多种操作符的条件匹配"""
        ops = {
            "equals": lambda a, e: a == e,
            "not_equals": lambda a, e: a != e,
            "contains": lambda a, e: e in str(a) if a is not None else False,
            "not_contains": lambda a, e: e not in str(a) if a is not None else True,
            "greater_than": lambda a, e: float(a) > float(e) if a is not None else False,
            "less_than": lambda a, e: float(a) < float(e) if a is not None else False,
            "regex": lambda a, e: bool(re.match(e, str(a))) if a is not None else False,
            "in": lambda a, e: a in json.loads(e) if a is not None else False,
            "exists": lambda a, e: a is not None,
        }
        handler = ops.get(operator)
        if not handler:
            return False
        try:
            return handler(actual, expected)
        except (ValueError, TypeError):
            return False

    def build_response_body(self, rule: MockRule, request_data: dict | None = None) -> dict | str:
        """构建响应体，支持脚本执行（使用 simpleeval 安全沙箱）、Mock 函数处理和 Faker 模板。"""
        if rule.script:
            return self._execute_script(rule.script, request_data or {})
        body = rule.response_body
        # 处理 $randomXxx()、{{variable}} 和 {{faker.TYPE}} 占位符
        if body and ("$random" in body or "{{" in body):
            from app.services.mock_engine import process_mock_functions
            body = process_mock_functions(body)
        # 尝试 JSON 解析
        try:
            return json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return body

    def _execute_script(self, script: str, request_data: dict) -> dict:
        """在沙箱中执行脚本（仅支持简单表达式，禁止文件/网络/导入）"""
        try:
            from simpleeval import simple_eval, EvalWithCompoundTypes
            evaluator = EvalWithCompoundTypes(
                names={
                    "request": request_data,
                    "headers": request_data.get("headers", {}),
                    "query": request_data.get("query", {}),
                    "body": request_data.get("body", {}),
                    "true": True, "false": False, "null": None,
                },
                functions={
                    "len": len, "str": str, "int": int, "float": float,
                    "bool": bool, "list": list, "dict": dict,
                    "abs": abs, "min": min, "max": max, "sum": sum,
                    "round": round,
                },
            )
            result = simple_eval(script, evaluator)
            if isinstance(result, (dict, list, str, int, float, bool)):
                return result if isinstance(result, dict) else {"data": result}
            return {"data": result}
        except (ValueError, SyntaxError, NameError, TypeError) as e:
            logger.warning(f"Mock script execution failed: {e}")
            return {"error": f"Script execution error: {str(e)}"}
        except Exception as e:
            # simpleeval.FunctionNotDefined / AttributeError / ZeroDivisionError 等
            type_name = type(e).__name__
            logger.warning(f"Mock script execution failed [{type_name}]: {e}")
            return {"error": f"Script execution error: {str(e)}"}

    async def test_mock(self, req) -> dict:
        """测试 Mock 规则匹配并返回响应"""
        result = await self.db.execute(
            select(MockRule)
            .where(MockRule.project_id == req.project_id, MockRule.enabled == 1)
            .order_by(MockRule.priority.desc(), MockRule.id.asc())
        )
        rules = result.scalars().all()

        # 构建请求数据供条件匹配
        request_data = {
            "query": getattr(req, 'query_params', {}) or {},
            "headers": getattr(req, 'headers', {}) or {},
            "body": getattr(req, 'body', None),
        }

        matched = None
        for rule in rules:
            # 跳过"全通配兜底"——兜底规则只用于 mock proxy 真实响应，
            # 不应干扰 test_mock 的匹配语义（否则任何路径都被匹配）。
            if rule.match_method == '*' and rule.match_path == '*':
                continue
            if not self._path_match(rule.match_method, rule.match_path, req.method, req.path):
                continue
            if rule.conditions:
                if not self._evaluate_conditions(rule.conditions, request_data):
                    continue
            matched = rule
            break

        if not matched:
            return {"matched": False, "rule": None, "response": None, "duration_ms": 0}

        start = time.time()
        if matched.response_delay:
            await asyncio.sleep(matched.response_delay / 1000)

        resp_body = self.build_response_body(matched, request_data)

        return {
            "matched": True,
            "rule": {
                "id": matched.id, "name": matched.name,
                "response_status": matched.response_status,
                "response_delay": matched.response_delay,
                "conditions": safe_json_load(matched.conditions, []),
                "has_script": bool(matched.script),
            },
            "response": {
                "status": matched.response_status,
                "headers": safe_json_load(matched.response_headers, {}),
                "body": resp_body,
            },
            "duration_ms": int((time.time() - start) * 1000),
        }

    async def generate_from_api(self, project_id: int, api_id: int) -> MockRule:
        """从 API 定义自动生成 Mock 规则"""
        from app.models.api_definition import ApiDefinition

        api = await self.db.get(ApiDefinition, api_id)
        if not api or api.project_id != project_id:
            raise_biz(ErrorCodes.API_NOT_FOUND)

        # 从 API 定义获取示例响应
        response_body = None
        if api.response_examples:
            response_body = api.response_examples
        elif api.response_schema:
            response_body = api.response_schema
        else:
            # 默认根据 HTTP 方法返回示例
            method_samples = {
                "GET": '{"id": 1, "name": "example", "status": "active"}',
                "POST": '{"id": 1, "message": "created successfully"}',
                "PUT": '{"message": "updated successfully"}',
                "DELETE": '{"message": "deleted successfully"}',
                "PATCH": '{"message": "updated successfully"}',
            }
            response_body = method_samples.get(api.method, '{"message": "ok"}')

        rule = MockRule(
            project_id=project_id,
            name=f"Auto: {api.method} {api.path}",
            enabled=True,
            priority=100,
            match_method=api.method,
            match_path=api.path,
            response_status=200,
            response_headers='{"Content-Type": "application/json"}',
            response_body=response_body,
            response_delay=0,
            conditions="[]",
            script="",
        )
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def batch_generate_from_apis(self, project_id: int, api_ids: builtins.list[int] | None = None) -> int:
        """批量生成 Mock 规则：从指定 API 列表（或所有 API）生成"""
        from app.models.api_definition import ApiDefinition

        query = select(ApiDefinition).where(
            ApiDefinition.project_id == project_id,
            ApiDefinition.deleted_at.is_(None),
        )
        if api_ids:
            query = query.where(ApiDefinition.id.in_(api_ids))

        result = await self.db.execute(query)
        apis = result.scalars().all()

        count = 0
        for api in apis:
            # 跳过已有规则的 API
            existing = await self.db.execute(
                select(MockRule).where(
                    MockRule.project_id == project_id,
                    MockRule.match_method == api.method,
                    MockRule.match_path == api.path,
                )
            )
            if existing.first():
                continue
            await self.generate_from_api(project_id, api.id)
            count += 1

        await self.db.flush()
        return count

    async def get_statistics(self, project_id: int) -> dict:
        """Mock 服务统计"""
        total_result = await self.db.scalar(
            select(func.count(MockRule.id)).where(MockRule.project_id == project_id))
        enabled_result = await self.db.scalar(
            select(func.count(MockRule.id)).where(
                MockRule.project_id == project_id, MockRule.enabled == 1))
        hits_result = await self.db.scalar(
            select(func.sum(MockRule.hit_count)).where(MockRule.project_id == project_id))

        # Top rules by hit count
        top_result = await self.db.execute(
            select(MockRule)
            .where(MockRule.project_id == project_id)
            .order_by(MockRule.hit_count.desc())
            .limit(10))
        top_rules = [self.to_dict(r) for r in top_result.scalars().all()]

        return {
            "total_rules": total_result or 0,
            "enabled_rules": enabled_result or 0,
            "total_hits": hits_result or 0,
            "top_rules": top_rules,
        }

    @staticmethod
    def generate_mock_from_schema(schema: dict) -> dict:
        """按 JSON Schema 生成 Mock 数据（纯 Python，无第三方依赖）。"""
        from app.services.mock_engine import SchemaMockGenerator
        generator = SchemaMockGenerator()
        return generator.generate(schema)

    async def record_call_log(
        self,
        project_id: int,
        mock_rule_id: int | None,
        request_method: str,
        request_path: str,
        request_headers: dict | None,
        request_query: dict | None,
        matched_rule_name: str | None,
        response_status: int,
        response_body_hash: str | None,
        duration_ms: int,
    ) -> None:
        """记录 Mock 调用日志。"""
        from app.models.mock_call_log import MockCallLog
        log = MockCallLog(
            project_id=project_id,
            mock_rule_id=mock_rule_id,
            request_method=request_method,
            request_path=request_path,
            request_headers=json.dumps(request_headers or {}, ensure_ascii=False) if request_headers else None,
            request_query=json.dumps(request_query or {}, ensure_ascii=False) if request_query else None,
            matched_rule_name=matched_rule_name,
            response_status=response_status,
            response_body_hash=response_body_hash,
            duration_ms=duration_ms,
        )
        self.db.add(log)
        await self.db.flush()

    async def list_call_logs(
        self,
        project_id: int,
        rule_id: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple:
        """查询 Mock 调用日志。"""
        from app.models.mock_call_log import MockCallLog
        query = select(MockCallLog).where(MockCallLog.project_id == project_id)
        count_query = select(func.count(MockCallLog.id)).where(MockCallLog.project_id == project_id)

        if rule_id:
            query = query.where(MockCallLog.mock_rule_id == rule_id)
            count_query = count_query.where(MockCallLog.mock_rule_id == rule_id)
        if start_date:
            query = query.where(MockCallLog.created_at >= start_date)
            count_query = count_query.where(MockCallLog.created_at >= start_date)
        if end_date:
            # 包含结束日期当天
            from datetime import datetime, timedelta
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(MockCallLog.created_at < end_dt.isoformat())
            count_query = count_query.where(MockCallLog.created_at < end_dt.isoformat())

        total = await self.db.scalar(count_query) or 0
        result = await self.db.execute(
            query.order_by(MockCallLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        logs = result.scalars().all()
        items = [
            {
                "id": log.id,
                "project_id": log.project_id,
                "mock_rule_id": log.mock_rule_id,
                "request_method": log.request_method,
                "request_path": log.request_path,
                "request_headers": safe_json_load(log.request_headers, {}),
                "request_query": safe_json_load(log.request_query, {}),
                "matched_rule_name": log.matched_rule_name,
                "response_status": log.response_status,
                "response_body_hash": log.response_body_hash,
                "duration_ms": log.duration_ms,
                "created_at": str(log.created_at),
            }
            for log in logs
        ]
        return items, total

    async def clear_call_logs(self, project_id: int) -> int:
        """清除项目的 Mock 调用日志。"""
        from app.models.mock_call_log import MockCallLog
        result = await self.db.execute(
            select(MockCallLog).where(MockCallLog.project_id == project_id)
        )
        logs = result.scalars().all()
        count = len(logs)
        for log in logs:
            await self.db.delete(log)
        await self.db.flush()
        return count

    async def get_call_trend(self, project_id: int, days: int = 7) -> list[dict]:
        """获取最近 N 天的调用趋势。"""
        from app.models.mock_call_log import MockCallLog
        from datetime import datetime, timedelta
        trend = []
        for i in range(days - 1, -1, -1):
            day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            next_day = (datetime.now() - timedelta(days=i - 1)).strftime("%Y-%m-%d") if i > 0 else (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            count = await self.db.scalar(
                select(func.count(MockCallLog.id)).where(
                    MockCallLog.project_id == project_id,
                    MockCallLog.created_at >= day,
                    MockCallLog.created_at < next_day,
                )
            ) or 0
            trend.append({"date": day, "count": count})
        return trend

    async def get_match_rate(self, project_id: int) -> dict:
        """获取规则匹配率（命中 vs 404）。"""
        from app.models.mock_call_log import MockCallLog
        total_calls = await self.db.scalar(
            select(func.count(MockCallLog.id)).where(MockCallLog.project_id == project_id)
        ) or 0
        matched_calls = await self.db.scalar(
            select(func.count(MockCallLog.id)).where(
                MockCallLog.project_id == project_id,
                MockCallLog.mock_rule_id.isnot(None),
            )
        ) or 0
        unmatched_calls = total_calls - matched_calls
        rate = round(matched_calls / total_calls * 100, 1) if total_calls > 0 else 0
        return {
            "total_calls": total_calls,
            "matched_calls": matched_calls,
            "unmatched_calls": unmatched_calls,
            "match_rate": rate,
        }
