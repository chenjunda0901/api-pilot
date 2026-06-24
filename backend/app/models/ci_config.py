"""CI 配置模型——存储 CI Token、关联计划等配置。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CiConfig(Base):
    __tablename__ = "ci_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True,
        comment="关联项目 ID",
    )
    ci_token: Mapped[str] = mapped_column(
        String(64), default="", nullable=False,
        comment="CI 鉴权 Token",
    )
    plan_ids: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False,
        comment="关联测试计划 ID 列表（JSON 数组字符串）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )
