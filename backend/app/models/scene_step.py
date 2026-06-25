from datetime import datetime
from sqlalchemy import (
    Boolean,
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, SoftDeleteMixin


class SceneStep(Base, SoftDeleteMixin):
    __tablename__ = "scene_steps"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("test_scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[str] = mapped_column(String(50), default="")
    node_type: Mapped[str] = mapped_column(String(20), default="request")
    label: Mapped[str] = mapped_column(String(200), default="")
    position_x: Mapped[float] = mapped_column(Float, default=0)
    position_y: Mapped[float] = mapped_column(Float, default=0)
    api_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_definitions.id", ondelete="CASCADE"), nullable=True
    )
    test_case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    timeout: Mapped[int] = mapped_column(Integer, default=30000)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    request_body: Mapped[str] = mapped_column(Text, nullable=True)
    headers: Mapped[str] = mapped_column(Text, nullable=True)
    query_params: Mapped[str] = mapped_column(Text, nullable=True)
    assertions: Mapped[str] = mapped_column(Text, nullable=True)
    extract_vars: Mapped[str] = mapped_column(Text, nullable=True)
    condition_expression: Mapped[str] = mapped_column(Text, nullable=True)
    loop_count: Mapped[int] = mapped_column(Integer, nullable=True)
    loop_variable: Mapped[str] = mapped_column(String(100), nullable=True)
    wait_duration: Mapped[int] = mapped_column(Integer, nullable=True)
    wait_mode: Mapped[str] = mapped_column(String(10), default="fixed", nullable=True)
    wait_min: Mapped[int] = mapped_column(Integer, nullable=True)
    wait_max: Mapped[int] = mapped_column(Integer, nullable=True)
    depends_on_step_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scene_steps.id", ondelete="SET NULL"), nullable=True
    )
    # 并行组：同一 parallel_group 的步骤并发执行，0 表示普通顺序执行
    parallel_group: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    is_seed: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
