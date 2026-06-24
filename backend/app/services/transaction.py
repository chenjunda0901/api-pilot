"""数据库事务管理 —— 阶段 4：导入/批量操作的回滚一致性。

提供 ``transaction_scope`` 异步上下文管理器：内部用 SAVEPOINT
（``session.begin_nested()``）隔离单步失败，异常时回滚到 SAVEPOINT
并冒泡给主事务（由 ``get_db`` 依赖统一提交或回滚）。

典型用法::

    from app.services.transaction import transaction_scope

    async def import_endpoints(db: AsyncSession, items: list[dict]) -> None:
        async with transaction_scope(db) as session:
            for item in items:
                # 任意一条失败 → 回滚到 SAVEPOINT，跳过本条
                session.add(ApiDefinition(**item))
                await session.flush()
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizError, TransactionError

logger = logging.getLogger("service.transaction")


class TransactionError_(Exception):
    """事务层内部异常（与 core.exceptions.TransactionError 区分）。"""


@asynccontextmanager
async def transaction_scope(
    db: AsyncSession,
    *,
    nested: bool = True,
    raise_on_error: bool = True,
) -> AsyncIterator[AsyncSession]:
    """事务作用域。

    参数：
        db: 共享的 ``AsyncSession``（通常来自 ``Depends(get_db)``）
        nested: True=SAVEPOINT（``begin_nested``），False=主事务
        raise_on_error: True 抛 ``TransactionError``，False 记录并返回

    用法::

        async with transaction_scope(db) as session:
            session.add(...)
    """
    if nested:
        # SAVEPOINT：单条失败只回滚 SAVEPOINT，不影响主事务
        try:
            async with db.begin_nested() as savepoint:
                yield db
            # 正常退出 → SAVEPOINT 释放
        except SQLAlchemyError as exc:
            logger.warning("transaction_scope SAVEPOINT rollback: %s", exc)
            if raise_on_error:
                raise TransactionError(detail=str(exc)) from exc
            # 不抛出：调用方自行检查 db 的状态
        except Exception as exc:
            # BizError 是业务异常（应映射为 4xx），直接向上抛出，不包装为 500
            if isinstance(exc, BizError):
                raise
            # 非数据库异常：仍尝试 SAVEPOINT 回滚
            try:
                await db.rollback()
            except Exception:  # noqa: BLE001
                pass
            logger.warning("transaction_scope unexpected error: %s", exc)
            if raise_on_error:
                raise TransactionError(detail=str(exc)) from exc
    else:
        # 主事务
        try:
            yield db
        except SQLAlchemyError as exc:
            logger.warning("transaction_scope rollback: %s", exc)
            if raise_on_error:
                raise TransactionError(detail=str(exc)) from exc
        except Exception as exc:
            # BizError 是业务异常（应映射为 4xx），直接向上抛出，不包装为 500
            if isinstance(exc, BizError):
                raise
            if raise_on_error:
                raise TransactionError(detail=str(exc)) from exc


async def safe_commit(db: AsyncSession) -> bool:
    """安全提交，失败时回滚并记录日志。返回是否成功。"""
    try:
        await db.commit()
        return True
    except SQLAlchemyError as exc:
        logger.warning("safe_commit failed: %s", exc)
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return False
