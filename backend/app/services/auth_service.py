import asyncio
from datetime import datetime, timedelta, UTC
import logging
from collections import defaultdict

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.middleware.auth import create_access_token, create_refresh_token, decode_token
from app.schemas.auth import RegisterRequest, LoginRequest
from app.utils.password import hash_password, verify_password, needs_rehash
from app.utils.security_audit import security_audit
from app.config import settings

logger = logging.getLogger("api_pilot.services.auth")

# 登录失败计数器（内存缓存）
# 结构: {username: {"count": int, "locked_until": datetime | None}}
_login_attempts: dict[str, dict] = defaultdict(
    lambda: {"count": 0, "locked_until": None}
)
_login_lock = asyncio.Lock()  # 保护 _login_attempts 的并发访问
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCK_MINUTES = 15


def reset_login_attempts(username: str | None = None) -> None:
    """重置登录失败计数器（用于测试环境）。

    Args:
        username: 指定用户名则重置该用户，为 None 则重置所有用户
    """
    global _login_attempts
    if username:
        _login_attempts[username] = {"count": 0, "locked_until": None}
    else:
        _login_attempts.clear()


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── helper ──────────────────────────────────────────────────

    async def _save_refresh_token(self, user_id: int, token: str) -> None:
        """保存 refresh token 到独立的 sessions 表（支持多端共存）"""
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        rt = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.db.add(rt)
        await self.db.flush()

    async def _revoke_all_user_tokens(self, user_id: int) -> None:
        """撤销某个用户的所有 refresh token"""
        await self.db.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )

    # ── register ────────────────────────────────────────────────

    async def register(self, req: RegisterRequest) -> User:
        # 密码强度验证：至少 6 位任意字符
        from app.utils.password import validate_password_strength

        if not validate_password_strength(req.password):
            raise_biz(ErrorCodes.AUTH_WEAK_PASSWORD, "密码至少 6 位")
        result = await self.db.execute(
            select(User).where(User.username == req.username)
        )
        if result.scalar_one_or_none():
            raise_biz(ErrorCodes.AUTH_USERNAME_EXISTS)
        pw_hash = hash_password(req.password)
        user = User(
            username=req.username,
            password_hash=pw_hash,
            nickname=req.nickname,
            email=req.email or None,
            role="member",
        )
        self.db.add(user)
        try:
            await self.db.flush()
            await self.db.refresh(user)
        except IntegrityError:
            raise_biz(ErrorCodes.AUTH_USERNAME_EXISTS)
        return user

    async def get_user_by_username(self, username: str) -> User | None:
        """根据用户名查找用户"""
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    # ── login ───────────────────────────────────────────────────

    async def login(
        self,
        req: LoginRequest,
        ip_address: str = "unknown",
        user_agent: str = "unknown",
    ) -> dict:
        # 检查账号是否被锁定
        attempt_info = _login_attempts[req.username]
        locked_until = attempt_info.get("locked_until")

        if locked_until and datetime.now(UTC) < locked_until:
            # 账号仍在锁定状态
            int(
                (locked_until - datetime.now(UTC)).total_seconds()
            )
            raise_biz(ErrorCodes.AUTH_ACCOUNT_LOCKED, "登录失败次数过多，请稍后重试")

        # 如果锁定已过期，重置计数器
        if locked_until and datetime.now(UTC) >= locked_until:
            _login_attempts[req.username] = {"count": 0, "locked_until": None}

        result = await self.db.execute(
            select(User).where(User.username == req.username)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(req.password, user.password_hash):
            # 记录登录失败
            security_audit.log_login_failed(
                username=req.username,
                ip_address=ip_address,
                user_agent=user_agent,
                reason="invalid_credentials",
            )

            # 增加失败计数（在锁保护下操作，防止并发绕过阈值）
            async with _login_lock:
                attempt_info = _login_attempts[req.username]
                attempt_info["count"] += 1

                # 检查是否达到锁定阈值
                if attempt_info["count"] >= LOGIN_MAX_ATTEMPTS:
                    locked_until = datetime.now(UTC) + timedelta(
                        minutes=LOGIN_LOCK_MINUTES
                    )
                    attempt_info["locked_until"] = locked_until
                    logger.warning(
                        "账号 %s 登录失败 %d 次，已锁定至 %s（多进程部署需依赖外部存储确保计数一致）",
                        req.username,
                        attempt_info["count"],
                        locked_until.isoformat(),
                    )
                raise_biz(
                    ErrorCodes.AUTH_ACCOUNT_LOCKED, "登录失败次数过多，请稍后重试"
                )

            # 返回通用错误消息（不泄露剩余尝试次数，防止攻击者精确计时）
            raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")

        # 登录成功，重置失败计数
        _login_attempts[req.username] = {"count": 0, "locked_until": None}

        # 自动升级哈希：如果当前哈希 rounds 不够或算法过时，登录成功后自动重哈希
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(req.password)
            await self.db.flush()
            logger.info("用户 %s 密码哈希已自动升级", user.username)

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        # 保存新 session 到 refresh_tokens 表，不干涉已有 session
        await self._save_refresh_token(user.id, refresh_token)

        # 记录登录成功
        security_audit.log_login_success(
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "email": user.email,
                "role": user.role,
                "created_at": str(user.created_at),
            },
        }

    # ── refresh ─────────────────────────────────────────────────

    async def refresh(self, token_str: str) -> dict:
        payload = decode_token(token_str)
        if not payload or payload.get("type") != "refresh":
            raise_biz(ErrorCodes.AUTH_TOKEN_EXPIRED, "invalid refresh token")
        user_id = int(payload["sub"])

        # 在 refresh_tokens 表中查找此 token
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == token_str,
                ~RefreshToken.is_revoked,
            )
        )
        stored = result.scalar_one_or_none()
        if not stored:
            raise_biz(ErrorCodes.AUTH_TOKEN_REVOKED, "refresh token 不存在或已撤销")

        # 轮换：删除旧 token，创建新 token
        await self.db.delete(stored)
        new_access = create_access_token(user_id)
        new_refresh = create_refresh_token(user_id)
        await self._save_refresh_token(user_id, new_refresh)

        return {"access_token": new_access, "refresh_token": new_refresh}

    # ── logout ──────────────────────────────────────────────────

    async def logout(self, user: User):
        """退出登录：撤销该用户所有 refresh token"""
        await self._revoke_all_user_tokens(user.id)

    async def update_profile(
        self, user: User, nickname: str = "", email: str = ""
    ) -> User:
        if nickname:
            user.nickname = nickname
        if email:
            user.email = email
        else:
            user.email = None
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def change_password(
        self, user: User, old_password: str, new_password: str
    ) -> None:
        """Change user password after verifying old password."""
        if not verify_password(old_password, user.password_hash):
            raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "Old password is incorrect")
        # 新密码不能与旧密码相同
        if verify_password(new_password, user.password_hash):
            raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "新密码不能与旧密码相同")
        # 校验新密码强度
        from app.utils.password import validate_password_strength

        if not validate_password_strength(new_password):
            raise_biz(ErrorCodes.AUTH_WEAK_PASSWORD, "密码至少 6 位")
        pw_hash = hash_password(new_password)
        user.password_hash = pw_hash
        await self._revoke_all_user_tokens(user.id)
        await self.db.flush()
