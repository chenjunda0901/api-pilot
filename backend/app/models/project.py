from datetime import datetime
from sqlalchemy import Boolean, String, Text, Integer, DateTime, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    global_variables: Mapped[str] = mapped_column(Text, default="[]")
    global_params: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    global_demo: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default=text('0'))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('0'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
