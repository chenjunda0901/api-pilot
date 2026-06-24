"""数据库内联迁移模块 —— 已弃用。

保留此文件仅为向后兼容。新迁移请使用 Alembic。
"""

import logging

logger = logging.getLogger("api_pilot.migration")


async def run_inline_migrations(conn) -> None:
    """已弃用：此函数仅记录警告，不再执行迁移。

    所有数据库变更已迁移到 Alembic。
    请使用 alembic upgrade head 应用迁移。
    """
    logger.warning(
        "run_inline_migrations() 已弃用。请使用 alembic upgrade head 应用迁移。"
    )