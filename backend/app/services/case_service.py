import json
from datetime import datetime, timezone
from app.utils.json_helpers import safe_json_load

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes
from app.models.test_case import TestCase
from app.schemas.case import CaseCreate, CaseUpdate


class CaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _safe_json(self, val, default=None):
        return safe_json_load(val, default)

    def to_dict(self, case: TestCase) -> dict:
        return {
            "id": case.id, "project_id": case.project_id, "api_id": case.api_id,
            "name": case.name, "description": case.description,
            "priority": case.priority, "status": case.status, "case_type": case.case_type, "tags": case.tags,
            "request_body": case.request_body,
            "assertions": self._safe_json(case.assertions, []),
            "extract_vars": self._safe_json(case.extract_vars, []),
            "created_at": str(case.created_at), "updated_at": str(case.updated_at),
        }

    async def get(self, case_id: int, project_id: int | None = None) -> TestCase:
        from sqlalchemy import and_
        conditions = [TestCase.id == case_id, TestCase.deleted_at.is_(None)]
        if project_id is not None:
            conditions.append(TestCase.project_id == project_id)
        result = await self.db.execute(select(TestCase).where(and_(*conditions)))
        case = result.scalar_one_or_none()
        if not case:
            raise_biz(ErrorCodes.CASE_NOT_FOUND)
        return case

    async def get_include_deleted(self, case_id: int) -> TestCase:
        result = await self.db.execute(select(TestCase).where(TestCase.id == case_id))
        case = result.scalar_one_or_none()
        if not case:
            raise_biz(ErrorCodes.CASE_NOT_FOUND)
        return case

    async def list(self, project_id: int, api_id: Optional[int] = None,
                   status: Optional[str] = None, case_type: Optional[str] = None,
                   page: int = 1, page_size: int = 20) -> tuple:
        query = select(TestCase).where(TestCase.project_id == project_id, TestCase.deleted_at.is_(None))
        count_query = select(func.count(TestCase.id)).where(TestCase.project_id == project_id, TestCase.deleted_at.is_(None))
        if api_id is not None:
            query = query.where(TestCase.api_id == api_id)
            count_query = count_query.where(TestCase.api_id == api_id)
        if status:
            query = query.where(TestCase.status == status)
            count_query = count_query.where(TestCase.status == status)
        if case_type:
            query = query.where(TestCase.case_type == case_type)
            count_query = count_query.where(TestCase.case_type == case_type)
        total = await self.db.scalar(count_query) or 0
        result = await self.db.execute(
            query.order_by(TestCase.updated_at.desc()).offset((page-1)*page_size).limit(page_size))
        return [self.to_dict(c) for c in result.scalars().all()], total

    async def create(self, project_id: int, req: CaseCreate) -> TestCase:
        # 检查同名用例
        existing = await self.db.execute(
            select(TestCase).where(
                TestCase.project_id == project_id,
                TestCase.api_id == req.api_id,
                TestCase.name == req.name,
                TestCase.deleted_at.is_(None)
            )
        )
        if existing.scalar_one_or_none():
            raise_biz(ErrorCodes.CONFLICT, f"用例名称 '{req.name}' 在该接口下已存在")

        case = TestCase(
            project_id=project_id, api_id=req.api_id, name=req.name,
            description=req.description, priority=req.priority, status=req.status,
            case_type=req.case_type, tags=req.tags, request_body=req.request_body,
            assertions=json.dumps(req.assertions),
            extract_vars=json.dumps(req.extract_vars))
        self.db.add(case)
        await self.db.flush()
        await self.db.refresh(case)
        return case

    async def update(self, case_id: int, req: CaseUpdate, project_id: int | None = None) -> TestCase:
        case = await self.get(case_id, project_id)
        if req.name:
            # 改名时检查唯一性
            if req.name != case.name:
                existing = await self.db.execute(
                    select(TestCase).where(
                        TestCase.project_id == case.project_id,
                        TestCase.api_id == case.api_id,
                        TestCase.name == req.name,
                        TestCase.deleted_at.is_(None)
                    )
                )
                if existing.scalar_one_or_none():
                    raise_biz(ErrorCodes.CONFLICT, f"用例名称 '{req.name}' 在该接口下已存在")
            case.name = req.name
        if req.description is not None:
            case.description = req.description
        if req.priority is not None:
            case.priority = req.priority
        if req.status is not None:
            case.status = req.status
        if req.case_type is not None:
            case.case_type = req.case_type
        if req.tags is not None:
            case.tags = req.tags
        if req.request_body is not None:
            case.request_body = req.request_body
        if req.assertions is not None:
            case.assertions = json.dumps(req.assertions)
        if req.extract_vars is not None:
            case.extract_vars = json.dumps(req.extract_vars)
        await self.db.flush()
        await self.db.refresh(case)
        return case

    async def delete(self, case_id: int, project_id: int | None = None):
        """软删除用例"""
        case = await self.get(case_id, project_id)
        case.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def list_deleted(self, project_id: int) -> list:
        from sqlalchemy import select
        result = await self.db.execute(
            select(TestCase).where(
                TestCase.project_id == project_id,
                TestCase.deleted_at.isnot(None)
            ).order_by(TestCase.deleted_at.desc())
        )
        return [{"id": c.id, "name": c.name, "project_id": c.project_id,
                 "api_id": c.api_id, "deleted_at": str(c.deleted_at)}
                for c in result.scalars().all()]

    async def restore(self, case_id: int, project_id: int):
        case = await self.get_include_deleted(case_id)
        if case.project_id != project_id:
            raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "资源不属于该项目")
        if case.deleted_at is None:
            return

        # 检查关联的 API 是否仍存在（未删除）
        parent_exists = True
        if case.api_id:
            from app.models.api_definition import ApiDefinition
            api_result = await self.db.execute(
                select(ApiDefinition).where(
                    ApiDefinition.id == case.api_id,
                    ApiDefinition.deleted_at.is_(None)
                )
            )
            api = api_result.scalar_one_or_none()
            if not api:
                parent_exists = False

        case.deleted_at = None
        await self.db.flush()
        return {"parent_exists": parent_exists}

    async def permanent_delete(self, case_id: int, project_id: int):
        case = await self.get_include_deleted(case_id)
        if case.project_id != project_id:
            raise_biz(ErrorCodes.PROJECT_FORBIDDEN, "资源不属于该项目")
        await self.db.delete(case)
        await self.db.flush()

    async def batch_update(self, ids: list, priority: Optional[str] = None, tags: Optional[str] = None):
        """批量更新用例属性"""
        if not ids:
            return
        values = {}
        if priority:
            values["priority"] = priority
        if tags is not None:
            values["tags"] = tags
        if values:
            from sqlalchemy import update
            await self.db.execute(
                update(TestCase).where(TestCase.id.in_(ids)).values(**values)
            )
            await self.db.flush()

    async def batch_delete(self, ids: list):
        """批量软删除"""
        from sqlalchemy import update
        await self.db.execute(
            update(TestCase)
            .where(TestCase.id.in_(ids))
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await self.db.flush()
