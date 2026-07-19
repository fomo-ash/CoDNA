from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import TimestampedUUIDModel
from app.db.types import Vector


class RepositoryChunkEmbedding(TimestampedUUIDModel):
    """A provider-neutral vector derived solely from one persisted chunk."""

    __tablename__ = "repository_chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "model", name="uq_repository_chunk_embeddings_chunk_model"),
        Index("ix_repository_chunk_embeddings_repository_model", "repository_id", "model"),
        Index("ix_repository_chunk_embeddings_source_hash", "source_hash"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repository_chunks.id", ondelete="CASCADE"), nullable=False
    )
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
