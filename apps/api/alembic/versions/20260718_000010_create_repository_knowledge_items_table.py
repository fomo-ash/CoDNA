"""create repository knowledge items table

Revision ID: 20260718_000010
Revises: 20260718_000009
Create Date: 2026-07-18 00:00:10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260718_000010"
down_revision = "20260718_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_knowledge_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("path", sa.String(length=2048), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("extractor", sa.String(length=128), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
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
    )
    op.create_index(
        "ix_repository_knowledge_items_extractor",
        "repository_knowledge_items",
        ["extractor"],
        unique=False,
    )
    op.create_index(
        "ix_repository_knowledge_items_item_type",
        "repository_knowledge_items",
        ["item_type"],
        unique=False,
    )
    op.create_index(
        "ix_repository_knowledge_items_name",
        "repository_knowledge_items",
        ["name"],
        unique=False,
    )
    op.create_index(
        "ix_repository_knowledge_items_repository_file_id",
        "repository_knowledge_items",
        ["repository_file_id"],
        unique=False,
    )
    op.create_index(
        "ix_repository_knowledge_items_repository_id",
        "repository_knowledge_items",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        "ix_repository_knowledge_items_repository_item",
        "repository_knowledge_items",
        ["repository_id", "item_type"],
        unique=False,
    )
    op.create_index(
        "ix_repository_knowledge_items_repository_path",
        "repository_knowledge_items",
        ["repository_id", "path"],
        unique=False,
    )
    op.create_index(
        "ix_repository_knowledge_items_repository_source",
        "repository_knowledge_items",
        ["repository_id", "source_type"],
        unique=False,
    )
    op.create_index(
        "ix_repository_knowledge_items_source_type",
        "repository_knowledge_items",
        ["source_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_repository_knowledge_items_source_type", table_name="repository_knowledge_items")
    op.drop_index("ix_repository_knowledge_items_repository_source", table_name="repository_knowledge_items")
    op.drop_index("ix_repository_knowledge_items_repository_path", table_name="repository_knowledge_items")
    op.drop_index("ix_repository_knowledge_items_repository_item", table_name="repository_knowledge_items")
    op.drop_index("ix_repository_knowledge_items_repository_id", table_name="repository_knowledge_items")
    op.drop_index("ix_repository_knowledge_items_repository_file_id", table_name="repository_knowledge_items")
    op.drop_index("ix_repository_knowledge_items_name", table_name="repository_knowledge_items")
    op.drop_index("ix_repository_knowledge_items_item_type", table_name="repository_knowledge_items")
    op.drop_index("ix_repository_knowledge_items_extractor", table_name="repository_knowledge_items")
    op.drop_table("repository_knowledge_items")
