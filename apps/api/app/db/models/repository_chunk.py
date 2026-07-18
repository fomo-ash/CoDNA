from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import TimestampedUUIDModel


class RepositoryChunk(TimestampedUUIDModel):
    __tablename__ = "repository_chunks"
    __table_args__ = (
        Index("ix_repository_chunks_repository_source", "repository_id", "source_type"),
        Index("ix_repository_chunks_repository_type", "repository_id", "chunk_type"),
        Index("ix_repository_chunks_repository_path", "repository_id", "path"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repository_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repository_files.id", ondelete="CASCADE"), nullable=True, index=True
    )
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
