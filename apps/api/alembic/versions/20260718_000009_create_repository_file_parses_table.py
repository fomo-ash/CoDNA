"""create repository file parses table

Revision ID: 20260718_000009
Revises: 20260718_000008
Create Date: 2026-07-18 00:00:09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260718_000009"
down_revision = "20260718_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_file_parses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path", sa.String(length=2048), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("parser", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("root_node_type", sa.String(length=128), nullable=True),
        sa.Column("has_error", sa.Boolean(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("symbol_count", sa.Integer(), nullable=False),
        sa.Column("import_count", sa.Integer(), nullable=False),
        sa.Column("symbols", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("imports", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repository_file_id"], ["repository_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_file_id", name="uq_repository_file_parses_file"),
    )
    op.create_index(
        "ix_repository_file_parses_language",
        "repository_file_parses",
        ["language"],
        unique=False,
    )
    op.create_index(
        "ix_repository_file_parses_repository_id",
        "repository_file_parses",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        "ix_repository_file_parses_repository_file_id",
        "repository_file_parses",
        ["repository_file_id"],
        unique=False,
    )
    op.create_index(
        "ix_repository_file_parses_repository_language",
        "repository_file_parses",
        ["repository_id", "language"],
        unique=False,
    )
    op.create_index(
        "ix_repository_file_parses_repository_status",
        "repository_file_parses",
        ["repository_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_repository_file_parses_status",
        "repository_file_parses",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_repository_file_parses_status", table_name="repository_file_parses")
    op.drop_index("ix_repository_file_parses_repository_status", table_name="repository_file_parses")
    op.drop_index("ix_repository_file_parses_repository_language", table_name="repository_file_parses")
    op.drop_index("ix_repository_file_parses_repository_file_id", table_name="repository_file_parses")
    op.drop_index("ix_repository_file_parses_repository_id", table_name="repository_file_parses")
    op.drop_index("ix_repository_file_parses_language", table_name="repository_file_parses")
    op.drop_table("repository_file_parses")
