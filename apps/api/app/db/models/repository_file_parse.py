from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import TimestampedUUIDModel


class RepositoryFileParse(TimestampedUUIDModel):
    __tablename__ = "repository_file_parses"
    __table_args__ = (
        UniqueConstraint("repository_file_id", name="uq_repository_file_parses_file"),
        Index("ix_repository_file_parses_repository_status", "repository_id", "status"),
        Index("ix_repository_file_parses_repository_language", "repository_id", "language"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repository_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    parser: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    root_node_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    has_error: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    symbol_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    import_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    symbols: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    imports: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
