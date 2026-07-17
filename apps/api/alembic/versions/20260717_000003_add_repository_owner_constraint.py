"""add repository owner constraint

Revision ID: 20260717_000003
Revises: 20260717_000002
Create Date: 2026-07-17 00:00:03
"""
from __future__ import annotations

from alembic import op


revision = "20260717_000003"
down_revision = "20260717_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_repositories_owner_id_users",
        "repositories",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_repositories_owner_id", "repositories", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_repositories_owner_id", table_name="repositories")
    op.drop_constraint(
        "fk_repositories_owner_id_users",
        "repositories",
        type_="foreignkey",
    )
