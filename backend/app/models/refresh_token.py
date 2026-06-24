from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RefreshToken(Base):
    """刷新令牌表——支持多设备多端共存与密码重置码

    双用途设计：
      - purpose="session"：标准 JWT refresh token，用于登录会话续期
      - purpose="password_reset"：密码重置码（hash 存储），用于忘记密码流程

    每次登录创建一条 session 记录，刷新时轮换（旧记录标记失效），退出时批量失效。
    密码重置时创建一条 password_reset 记录，使用成功后删除。
    """

    PURPOSE_SESSION = "session"
    PURPOSE_PASSWORD_RESET = "password_reset"

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    token: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True,
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, server_default="session", index=True)
    reset_code_hash: Mapped[str] = mapped_column(String(255), nullable=False, server_default="", index=True)
    reset_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    user = relationship("User", back_populates="refresh_tokens", lazy="joined")

    # ── 工厂方法 ──────────────────────────────────────

    @classmethod
    def create_session(cls, user_id: int, token: str, expires_at: datetime) -> "RefreshToken":
        """创建 session 类型的 refresh token 记录。"""
        return cls(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            purpose=cls.PURPOSE_SESSION,
        )

    @classmethod
    def create_password_reset(cls, user_id: int, token: str, expires_at: datetime,
                              code_hash: str) -> "RefreshToken":
        """创建密码重置类型的记录。"""
        return cls(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            purpose=cls.PURPOSE_PASSWORD_RESET,
            reset_code_hash=code_hash,
        )
