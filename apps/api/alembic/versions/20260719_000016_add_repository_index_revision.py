"""add repository index revision

Revision ID: 20260719_000016
Revises: 20260719_000015
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260719_000016"
down_revision = "20260719_000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column("last_indexed_revision", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("repositories", "last_indexed_revision")
