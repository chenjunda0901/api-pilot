import logging
import random
import re
import uuid
from datetime import datetime, timedelta, UTC

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import raise_biz, ErrorCodes
from app.database import get_db
from app.models.user import User
from app.models.revoked_token import RevokedToken

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("api_pilot.auth")

WHITE_LIST = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/health",
}

# 精确匹配 /api/v1/reports/shared/{token}，token 为非空且不含额外路径段
_SHARED_REPORT_RE = re.compile(r"^/api/v1/reports/shared/[^/]+$")


def is_white_list(path: str) -> bool:
    if path in WHITE_LIST:
        return True
    if _SHARED_REPORT_RE.match(path):
        return True
    return False


def create_access_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "access", "jti": uuid.uuid4().hex}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh", "jti": uuid.uuid4().hex}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc.__class__.__name__)
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise_biz(ErrorCodes.AUTH_TOKEN_MISSING)
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise_biz(ErrorCodes.AUTH_INVALID_TOKEN, "invalid access token")
    # JWT 黑名单检查：token 被吊销后立即失效
    jti = payload.get("jti")
    if jti:
        revoked = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
        if revoked.scalar_one_or_none():
            raise_biz(ErrorCodes.AUTH_TOKEN_REVOKED, "token has been revoked")
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise_biz(ErrorCodes.AUTH_USER_NOT_FOUND)
    # 概率触发过期 token 清理（约每 100 次验证触发一次）
    if random.random() < 0.01:
        try:
            from app.database import async_session_factory
            async with async_session_factory() as cleanup_session:
                await cleanup_expired_tokens(cleanup_session)
        except Exception:
            pass  # 清理失败不影响认证
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """与 get_current_user 类似，但未提供令牌时返回 None 而不是 401"""
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        return None
    # JWT 黑名单检查
    jti = payload.get("jti")
    if jti:
        revoked = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
        if revoked.scalar_one_or_none():
            return None
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise_biz(ErrorCodes.AUTH_FORBIDDEN)
    return current_user


async def revoke_token(db: AsyncSession, token: str) -> None:
    """将 JWT token 加入黑名单（按 jti），使其立即失效。"""
    payload = decode_token(token)
    if payload is None:
        return  # 无效 token 无需加入黑名单
    jti = payload.get("jti")
    if not jti:
        return
    existing = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
    if existing.scalar_one_or_none() is None:
        db.add(RevokedToken(jti=jti))
        await db.flush()


async def cleanup_expired_tokens(db: AsyncSession) -> None:
    """清理过期的 RevokedToken 记录，防止表无限增长。

    JWT token 过期后其黑名单记录不再有实际意义，保留 7 天后清理。
    """
    from sqlalchemy import delete as sa_delete
    cutoff = datetime.now(UTC) - timedelta(days=7)
    try:
        await db.execute(sa_delete(RevokedToken).where(RevokedToken.revoked_at < cutoff))
        await db.commit()
    except Exception:
        await db.rollback()
