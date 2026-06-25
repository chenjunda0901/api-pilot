from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class TestDataset(Base):
    __tablename__ = "test_datasets"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    rows = relationship("TestDatasetRow", back_populates="dataset", cascade="all, delete-orphan")


class TestDatasetRow(Base):
    __tablename__ = "test_dataset_rows"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    dataset = relationship("TestDataset", back_populates="rows")
