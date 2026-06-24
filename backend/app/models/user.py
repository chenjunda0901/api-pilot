from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.refresh_token import RefreshToken


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, server_default="")
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, server_default="")
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="member")

    # 多设备 session：同一个用户可以有多条有效 refresh token
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
