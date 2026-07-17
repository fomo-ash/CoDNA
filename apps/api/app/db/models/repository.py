from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import TimestampedUUIDModel
from app.modules.repositories.enums import RepositoryStatus


class Repository(TimestampedUUIDModel):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("owner_id", "github_id", name="uq_repositories_owner_github_id"),
    )

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    github_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clone_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[RepositoryStatus] = mapped_column(
        Enum(
            RepositoryStatus,
            name="repository_status",
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=False,
        index=True,
    )
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
