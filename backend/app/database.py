"""数据库引擎与会话工厂——含慢查询日志、N+1 检测与后台任务会话隔离"""

import time
import logging
import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

logger = logging.getLogger("api_pilot.db")

# --- 慢查询日志配置 ---
SLOW_QUERY_THRESHOLD_MS = 500  # 超过此阈值的查询将被记录

# --- N+1 检测 ---
_query_count = defaultdict(int)
_query_counter_enabled = False

# --- 稳定性配置 ---
DB_MAX_RETRIES = 3           # 最大重试次数
DB_RETRY_DELAY = 0.5        # 重试延迟（秒）
DB_CONNECTION_TIMEOUT = 10  # 连接超时（秒，阶段 4 调整为 10s）
DB_QUERY_TIMEOUT = 20       # 查询超时（秒，阶段 4 调整为 20s）


def enable_query_counter():
    """启用查询计数（用于 N+1 检测，在测试或调试时开启）"""
    global _query_counter_enabled
    _query_counter_enabled = True
    _query_count.clear()


def get_query_stats() -> dict:
    """获取查询统计（按调用栈分组）"""
    return dict(_query_count)


def reset_query_stats():
    """重置查询统计"""
    _query_count.clear()


async def _retry_async_operation(operation, max_retries: int = DB_MAX_RETRIES):
    """通用异步重试机制，带指数退避"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            last_error = e
            # SQLite 锁定错误
            if "database is locked" in str(e).lower() or "locked" in str(e).lower():
                wait_time = DB_RETRY_DELAY * (2 ** attempt)  # 指数退避
                logger.warning(f"数据库锁定，{wait_time:.1f}秒后重试 ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                raise
    raise last_error


def _create_engine_with_retry(max_retries: int = 3):
    """创建数据库引擎，带重试机制"""
    last_error = None
    for attempt in range(max_retries):
        try:
            if settings.DATABASE_URL.startswith('sqlite'):
                engine = create_async_engine(
                    settings.DATABASE_URL,
                    echo=False,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": DB_CONNECTION_TIMEOUT,
                    },
                    pool_pre_ping=True,
                    # SQLite 使用 NullPool，每次获取新连接
                    poolclass=None,  # 让 SQLAlchemy 自动选择
                )
            else:
                # 阶段 4：PostgreSQL 增加 connect_timeout 与 statement_timeout
                # statement_timeout 由 SQLAlchemy 通过 connect_args 传递到 server_side_binding
                connect_args: dict = {"connect_timeout": DB_CONNECTION_TIMEOUT}
                if settings.DATABASE_URL.startswith('postgresql'):
                    # statement_timeout 单位为毫秒，PostgreSQL 服务端生效
                    connect_args["options"] = (
                        f"-c statement_timeout={DB_QUERY_TIMEOUT * 1000}"
                    )
                engine = create_async_engine(
                    settings.DATABASE_URL,
                    echo=False,
                    pool_pre_ping=True,
                    pool_size=20,
                    max_overflow=10,
                    pool_recycle=3600,
                    # 连接池超时配置
                    pool_timeout=30,
                    connect_args=connect_args,
                    # 空闲连接回收
                )
            return engine
        except Exception as e:
            last_error = e
            logger.warning(f"数据库引擎创建失败 ({attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(DB_RETRY_DELAY * (2 ** attempt))
    raise RuntimeError(f"数据库引擎创建失败，已重试 {max_retries} 次: {last_error}")


engine = _create_engine_with_retry()


# SQLite 默认关闭外键约束，每次连接时启用
if settings.DATABASE_URL.startswith('sqlite'):

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        """SQLite 连接建立时启用外键约束，确保级联删除生效。"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """记录查询开始时间"""
    conn._query_start_time = time.monotonic()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """记录查询耗时，超过阈值则告警"""
    elapsed_ms = (time.monotonic() - conn._query_start_time) * 1000
    if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
        stmt_short = statement[:200] if len(statement) > 200 else statement
        logger.warning(
            "慢查询 (%.0fms): %s",
            elapsed_ms,
            stmt_short,
        )
    if _query_counter_enabled:
        import traceback
        stack = "".join(traceback.format_stack(limit=6)[-4:-1])
        _query_count[stack] += 1


async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入专属：自动管理 Session 生命周期及异常回滚"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            # 记录详细错误日志，便于排查
            logger.error("FastAPI 会话异常，已回滚: %s", str(e))
            # 某些可恢复错误，转换为友好提示
            if "database is locked" in str(e).lower():
                logger.warning("数据库锁定，可能是并发过高或长时间事务")
            raise


@asynccontextmanager
async def get_background_db() -> AsyncGenerator[AsyncSession, None]:
    """非 FastAPI 上下文专属：用于定时任务或后台异步线程中，防止 Session 泄漏"""
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("后台任务独立会话异常，已回滚: %s", str(e))
        raise
    finally:
        await session.close()


class _RetrySession:
    """带自动重试的异步数据库会话，支持 async with 上下文管理。"""

    def __init__(self, max_retries: int = DB_MAX_RETRIES):
        self._max_retries = max_retries
        self._session: AsyncSession | None = None

    async def _get_session(self) -> AsyncSession:
        session = async_session_factory()
        try:
            await session.execute(text("SELECT 1"))
            return session
        except Exception:
            await session.close()
            raise

    async def __aenter__(self) -> AsyncSession:
        for attempt in range(self._max_retries):
            try:
                self._session = await self._get_session()
                return self._session
            except Exception as e:
                if attempt < self._max_retries - 1:
                    wait_time = DB_RETRY_DELAY * (2 ** attempt)
                    logger.warning("DB connection failed (attempt %d/%d): %s, retrying in %.1fs",
                                   attempt + 1, self._max_retries, e, wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    raise
        raise RuntimeError("unreachable")

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session is not None:
            try:
                if exc_type is not None:
                    await self._session.rollback()
                else:
                    await self._session.commit()
            finally:
                await self._session.close()


async def get_db_with_retry(max_retries: int = DB_MAX_RETRIES):
    """
    获取带重试的数据库会话。

    返回 ``_RetrySession`` 上下文管理器，必须使用 ``async with`` 确保资源释放。
    """
    return _RetrySession(max_retries)


async def warmup_pool():
    """启动时预热连接池，避免首次请求的冷启动延迟"""
    from sqlalchemy import text
    for _ in range(3):
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
                await session.commit()
                logger.info("数据库连接预热成功")
                return
        except Exception as e:
            logger.warning(f"连接预热失败 ({_ + 1}/3): {e}")
            if _ < 2:
                await asyncio.sleep(1)
    logger.error("数据库连接预热失败，请检查数据库配置")


async def health_check() -> dict:
    """数据库健康检查，返回连接状态和统计信息"""
    import datetime
    result = {
        "status": "unknown",
        "database": settings.DATABASE_URL.split("://")[0].split("+")[0],
        "timestamp": datetime.datetime.now().isoformat(),
        "slow_queries": 0,
        "error": None,
    }
    try:
        async with async_session_factory() as session:
            start = time.time()
            await session.execute(text("SELECT 1"))
            elapsed_ms = (time.time() - start) * 1000
            result["status"] = "healthy" if elapsed_ms < 1000 else "degraded"
            result["latency_ms"] = round(elapsed_ms, 2)
            
            # 获取慢查询统计
            slow_count = len(_query_count) if _query_count else 0
            result["slow_queries"] = slow_count
            
    except Exception as e:
        result["status"] = "unhealthy"
        result["error"] = str(e)
    
    return result
