"""Add user_id column to jobs table for authentication

Revision ID: 005
Revises: 004
Create Date: 2026-04-02 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("user_id", sa.String(64), nullable=False, server_default="anonymous"))
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_user_id")
    op.drop_column("jobs", "user_id")
