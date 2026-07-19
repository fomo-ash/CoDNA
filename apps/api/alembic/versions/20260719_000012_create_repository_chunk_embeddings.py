"""create repository chunk embeddings

Revision ID: 20260719_000012
Revises: 20260718_000011
Create Date: 2026-07-19 00:00:12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.db.types import Vector


revision = "20260719_000012"
down_revision = "20260718_000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "repository_chunk_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["repository_chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "model", name="uq_repository_chunk_embeddings_chunk_model"),
    )
    op.create_index("ix_repository_chunk_embeddings_repository_model", "repository_chunk_embeddings", ["repository_id", "model"])
    op.create_index("ix_repository_chunk_embeddings_source_hash", "repository_chunk_embeddings", ["source_hash"])
    op.execute(
        "CREATE INDEX ix_repository_chunk_embeddings_vector_cosine "
        "ON repository_chunk_embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_repository_chunk_embeddings_vector_cosine")
    op.drop_index("ix_repository_chunk_embeddings_source_hash", table_name="repository_chunk_embeddings")
    op.drop_index("ix_repository_chunk_embeddings_repository_model", table_name="repository_chunk_embeddings")
    op.drop_table("repository_chunk_embeddings")
