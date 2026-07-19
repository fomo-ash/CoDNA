from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import TimestampedUUIDModel


class RepositoryQuestionCache(TimestampedUUIDModel):
    __tablename__ = "repository_question_cache"
    __table_args__ = (
        UniqueConstraint("repository_id", "question_hash", "repository_indexed_at", name="uq_repository_question_cache_version"),
        Index("ix_repository_question_cache_repository_indexed", "repository_id", "repository_indexed_at"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    question_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    repository_indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    vector_search_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
