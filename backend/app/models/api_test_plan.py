from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiTestPlan(Base):
    """接口测试计划模型

    聚合一组用例/场景作为可调度的执行单元，承载并发、超时、失败策略等运行参数。
    """
    __tablename__ = "api_test_plans"
    __table_args__ = (
        Index("ix_api_test_plans_project_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    concurrency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    failure_strategy: Mapped[str] = mapped_column(
        String(20), default="continue", nullable=False,
        comment="枚举: stop_all / continue",
    )
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False, index=True,
        comment="枚举: active / paused",
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ApiTestPlanStep(Base):
    """测试计划步骤模型

    通过 step_type + step_id 多态引用具体用例/场景，按 order_index 有序执行。
    """
    __tablename__ = "api_test_plan_steps"
    __table_args__ = (
        Index("ix_api_test_plan_steps_plan_order", "plan_id", "order_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_test_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    step_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="枚举: case / scene",
    )
    step_id: Mapped[int] = mapped_column(Integer, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
