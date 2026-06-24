from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class SearchHistory(Base):
    __tablename__ = "search_history"
    __table_args__ = (
        UniqueConstraint("user_id", "query", name="uq_search_history_user_query"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    query: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
