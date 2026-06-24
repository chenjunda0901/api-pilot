from sqlalchemy import String, Integer, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class SceneEdge(Base):
    __tablename__ = "scene_edges"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    edge_id: Mapped[str] = mapped_column(String(50), default="")
    source_node_id: Mapped[str] = mapped_column(String(50), default="")
    target_node_id: Mapped[str] = mapped_column(String(50), default="")
    source_handle: Mapped[str] = mapped_column(String(20), nullable=True)
    label: Mapped[str] = mapped_column(String(200), default="")
    is_seed: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default=text('0'))
