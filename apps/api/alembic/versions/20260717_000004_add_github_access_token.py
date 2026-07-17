"""add backend github access token

Revision ID: 20260717_000004
Revises: 20260717_000003
Create Date: 2026-07-17 00:00:04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260717_000004"
down_revision = "20260717_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("github_access_token", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "github_access_token")
