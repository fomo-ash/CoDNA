from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import TimestampedUUIDModel


class RepositoryHistoryArtifact(TimestampedUUIDModel):
    """A source-backed GitHub artifact used for repository decision context."""

    __tablename__ = "repository_history_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "provider", "artifact_type", "external_id",
            name="uq_repository_history_artifacts_external",
        ),
        Index("ix_history_artifacts_repository_type", "repository_id", "artifact_type"),
        Index("ix_history_artifacts_repository_path", "repository_id", "path"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="github")
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    authored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
