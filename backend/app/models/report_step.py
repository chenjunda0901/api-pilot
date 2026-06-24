from sqlalchemy import String, Text, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ReportStep(Base):
    __tablename__ = "report_steps"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_scenes.id", ondelete="SET NULL"), nullable=True)
    scene_step_id: Mapped[int] = mapped_column(Integer, ForeignKey("scene_steps.id", ondelete="SET NULL"), nullable=True)
    api_id: Mapped[int] = mapped_column(Integer, ForeignKey("api_definitions.id", ondelete="SET NULL"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    request_url: Mapped[str] = mapped_column(Text, default="")
    request_method: Mapped[str] = mapped_column(String(10), default="")
    request_headers: Mapped[str] = mapped_column(Text, nullable=True)
    request_body: Mapped[str] = mapped_column(Text, nullable=True)
    response_status: Mapped[int] = mapped_column(Integer, default=0)
    response_headers: Mapped[str] = mapped_column(Text, nullable=True)
    response_body: Mapped[str] = mapped_column(Text, nullable=True)
    assertions: Mapped[str] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    script_output: Mapped[str] = mapped_column(Text, nullable=True)
    script_error: Mapped[str] = mapped_column(Text, nullable=True)
