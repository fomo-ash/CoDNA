"""create repository history artifacts

Revision ID: 20260719_000017
Revises: 20260719_000016
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260719_000017"
down_revision = "20260719_000016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_history_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("author_login", sa.String(length=255), nullable=True),
        sa.Column("path", sa.String(length=2048), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("authored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "provider", "artifact_type", "external_id", name="uq_repository_history_artifacts_external"),
    )
    op.create_index("ix_history_artifacts_repository_type", "repository_history_artifacts", ["repository_id", "artifact_type"])
    op.create_index("ix_history_artifacts_repository_path", "repository_history_artifacts", ["repository_id", "path"])


def downgrade() -> None:
    op.drop_index("ix_history_artifacts_repository_path", table_name="repository_history_artifacts")
    op.drop_index("ix_history_artifacts_repository_type", table_name="repository_history_artifacts")
    op.drop_table("repository_history_artifacts")
