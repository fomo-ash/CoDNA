"""create repository question cache

Revision ID: 20260719_000014
Revises: 20260719_000013
Create Date: 2026-07-19 00:00:14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260719_000014"
down_revision = "20260719_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_question_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_hash", sa.String(length=64), nullable=False),
        sa.Column("repository_indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("vector_search_used", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "question_hash", "repository_indexed_at", name="uq_repository_question_cache_version"),
    )
    op.create_index("ix_repository_question_cache_repository_indexed", "repository_question_cache", ["repository_id", "repository_indexed_at"])


def downgrade() -> None:
    op.drop_index("ix_repository_question_cache_repository_indexed", table_name="repository_question_cache")
    op.drop_table("repository_question_cache")
