from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import TimestampedUUIDModel


class RepositoryRelationshipEdge(TimestampedUUIDModel):
    """A materialized, repository-local relationship extracted from a chunk."""

    __tablename__ = "repository_relationship_edges"
    __table_args__ = (
        Index("ix_relationship_edges_repository_source", "repository_id", "source_chunk_id"),
        Index("ix_relationship_edges_repository_target", "repository_id", "target_chunk_id"),
        Index("ix_relationship_edges_repository_target_path", "repository_id", "target_path"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repository_chunks.id", ondelete="CASCADE"), nullable=False
    )
    target_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repository_chunks.id", ondelete="SET NULL"), nullable=True
    )
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_stable_symbol_id: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    target_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    target_stable_symbol_id: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    # Relationship labels can be generated from nested or aliased source expressions.
    # They are evidence, not identifiers, so truncating them would both lose context
    # and make indexing fail for otherwise valid repositories.
    target_symbol: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str] = mapped_column(String(16), nullable=False, default="unresolved")
