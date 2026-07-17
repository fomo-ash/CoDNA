"""update repository status and ownership constraints

Revision ID: 20260717_000005
Revises: 20260717_000004
Create Date: 2026-07-17 00:00:05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260717_000005"
down_revision = "20260717_000004"
branch_labels = None
depends_on = None


repository_status = postgresql.ENUM(
    "registered",
    "cloning",
    "indexing",
    "ready",
    "failed",
    "archived",
    name="repository_status",
)


def upgrade() -> None:
    repository_status.create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "repositories",
        "status",
        existing_type=sa.String(length=32),
        type_=repository_status,
        existing_nullable=False,
        postgresql_using="status::repository_status",
    )
    op.drop_constraint("uq_repositories_full_name", "repositories", type_="unique")
    op.create_unique_constraint(
        "uq_repositories_owner_github_id",
        "repositories",
        ["owner_id", "github_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_repositories_owner_github_id", "repositories", type_="unique")
    op.create_unique_constraint("uq_repositories_full_name", "repositories", ["full_name"])
    op.alter_column(
        "repositories",
        "status",
        existing_type=repository_status,
        type_=sa.String(length=32),
        existing_nullable=False,
        postgresql_using="status::text",
    )
    repository_status.drop(op.get_bind(), checkfirst=True)
