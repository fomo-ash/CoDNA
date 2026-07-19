"""create repository relationship edges

Revision ID: 20260719_000015
Revises: 20260719_000014
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260719_000015"
down_revision = "20260719_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_relationship_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.Column("source_path", sa.String(length=2048), nullable=False),
        sa.Column("source_stable_symbol_id", sa.String(length=4096), nullable=True),
        sa.Column("target_path", sa.String(length=2048), nullable=True),
        sa.Column("target_stable_symbol_id", sa.String(length=4096), nullable=True),
        sa.Column("target_symbol", sa.String(length=1024), nullable=True),
        sa.Column("resolution", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["repository_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_chunk_id"], ["repository_chunks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_relationship_edges_repository_source", "repository_relationship_edges", ["repository_id", "source_chunk_id"])
    op.create_index("ix_relationship_edges_repository_target", "repository_relationship_edges", ["repository_id", "target_chunk_id"])
    op.create_index("ix_relationship_edges_repository_target_path", "repository_relationship_edges", ["repository_id", "target_path"])


def downgrade() -> None:
    op.drop_index("ix_relationship_edges_repository_target_path", table_name="repository_relationship_edges")
    op.drop_index("ix_relationship_edges_repository_target", table_name="repository_relationship_edges")
    op.drop_index("ix_relationship_edges_repository_source", table_name="repository_relationship_edges")
    op.drop_table("repository_relationship_edges")
