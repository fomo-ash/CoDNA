"""create repository answer usage

Revision ID: 20260719_000013
Revises: 20260719_000012
Create Date: 2026-07-19 00:00:13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260719_000013"
down_revision = "20260719_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_answer_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="reserved"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repository_answer_usage_owner_created", "repository_answer_usage", ["owner_id", "created_at"])
    op.create_index("ix_repository_answer_usage_repository_created", "repository_answer_usage", ["repository_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_repository_answer_usage_repository_created", table_name="repository_answer_usage")
    op.drop_index("ix_repository_answer_usage_owner_created", table_name="repository_answer_usage")
    op.drop_table("repository_answer_usage")
