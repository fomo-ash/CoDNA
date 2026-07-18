"""add repository clone metadata

Revision ID: 20260718_000007
Revises: 20260717_000006
Create Date: 2026-07-18 00:00:07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260718_000007"
down_revision = "20260717_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column("clone_path", sa.String(length=2048), nullable=True))
    op.add_column("repositories", sa.Column("last_cloned_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("repositories", "last_cloned_at")
    op.drop_column("repositories", "clone_path")
