"""expand relationship edge target symbol storage

Revision ID: 20260720_000019
Revises: 20260719_000018
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260720_000019"
down_revision = "20260719_000018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "repository_relationship_edges",
        "target_symbol",
        existing_type=sa.String(length=1024),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "repository_relationship_edges",
        "target_symbol",
        existing_type=sa.Text(),
        type_=sa.String(length=1024),
        existing_nullable=True,
    )
