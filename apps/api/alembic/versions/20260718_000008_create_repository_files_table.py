"""create repository inventory tables

Revision ID: 20260718_000008
Revises: 20260718_000007
Create Date: 2026-07-18 00:00:08
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260718_000008"
down_revision = "20260718_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path", sa.String(length=2048), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("extension", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("is_binary", sa.Boolean(), nullable=False),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "path", name="uq_repository_files_repository_path"),
    )
    op.create_index("ix_repository_files_extension", "repository_files", ["extension"], unique=False)
    op.create_index("ix_repository_files_language", "repository_files", ["language"], unique=False)
    op.create_index(
        "ix_repository_files_repository_language",
        "repository_files",
        ["repository_id", "language"],
        unique=False,
    )
    op.create_index(
        "ix_repository_files_repository_path",
        "repository_files",
        ["repository_id", "path"],
        unique=False,
    )
    op.create_index("ix_repository_files_repository_id", "repository_files", ["repository_id"], unique=False)
    op.create_table(
        "repository_statistics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_files", sa.Integer(), nullable=False),
        sa.Column("source_files", sa.Integer(), nullable=False),
        sa.Column("binary_files", sa.Integer(), nullable=False),
        sa.Column("total_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("detected_languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id"),
    )
    op.create_index(
        "ix_repository_statistics_repository_id",
        "repository_statistics",
        ["repository_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_repository_statistics_repository_id", table_name="repository_statistics")
    op.drop_table("repository_statistics")
    op.drop_index("ix_repository_files_repository_id", table_name="repository_files")
    op.drop_index("ix_repository_files_repository_path", table_name="repository_files")
    op.drop_index("ix_repository_files_repository_language", table_name="repository_files")
    op.drop_index("ix_repository_files_language", table_name="repository_files")
    op.drop_index("ix_repository_files_extension", table_name="repository_files")
    op.drop_table("repository_files")
