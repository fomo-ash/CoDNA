"""create repository chunks table

Revision ID: 20260718_000011
Revises: 20260718_000010
Create Date: 2026-07-18 00:00:11
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260718_000011"
down_revision = "20260718_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("path", sa.String(length=2048), nullable=False),
        sa.Column("chunk_type", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["repository_file_id"], ["repository_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repository_chunks_repository_id", "repository_chunks", ["repository_id"], unique=False)
    op.create_index("ix_repository_chunks_repository_file_id", "repository_chunks", ["repository_file_id"], unique=False)
    op.create_index("ix_repository_chunks_chunk_type", "repository_chunks", ["chunk_type"], unique=False)
    op.create_index("ix_repository_chunks_source_type", "repository_chunks", ["source_type"], unique=False)
    op.create_index("ix_repository_chunks_repository_source", "repository_chunks", ["repository_id", "source_type"], unique=False)
    op.create_index("ix_repository_chunks_repository_type", "repository_chunks", ["repository_id", "chunk_type"], unique=False)
    op.create_index("ix_repository_chunks_repository_path", "repository_chunks", ["repository_id", "path"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_repository_chunks_repository_path", table_name="repository_chunks")
    op.drop_index("ix_repository_chunks_repository_type", table_name="repository_chunks")
    op.drop_index("ix_repository_chunks_repository_source", table_name="repository_chunks")
    op.drop_index("ix_repository_chunks_source_type", table_name="repository_chunks")
    op.drop_index("ix_repository_chunks_chunk_type", table_name="repository_chunks")
    op.drop_index("ix_repository_chunks_repository_file_id", table_name="repository_chunks")
    op.drop_index("ix_repository_chunks_repository_id", table_name="repository_chunks")
    op.drop_table("repository_chunks")
