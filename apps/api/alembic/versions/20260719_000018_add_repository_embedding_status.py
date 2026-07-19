"""add repository embedding status

Revision ID: 20260719_000018
Revises: 20260719_000017
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260719_000018"
down_revision = "20260719_000017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column("embedding_status", sa.String(length=32), server_default="pending", nullable=False))
    op.add_column("repositories", sa.Column("embedding_chunk_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("repositories", sa.Column("embedding_error_message", sa.Text(), nullable=True))
    op.add_column("repositories", sa.Column("embedding_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("repositories", sa.Column("embedding_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("repositories", "embedding_completed_at")
    op.drop_column("repositories", "embedding_started_at")
    op.drop_column("repositories", "embedding_error_message")
    op.drop_column("repositories", "embedding_chunk_count")
    op.drop_column("repositories", "embedding_status")
