from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class SceneDataset(Base):
    __tablename__ = "scene_dataset"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("test_scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON string: [{"col1": "val1", ...}, ...]
    type: Mapped[str] = mapped_column(String(10), default="json")  # csv / json
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
