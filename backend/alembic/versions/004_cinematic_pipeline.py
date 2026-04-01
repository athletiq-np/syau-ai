"""Add cinematic pipeline tables - projects, characters, scenes, shots

Revision ID: 004
Revises: 003
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Projects table
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "status",
            sa.Enum("draft", "processing", "done", "failed", name="projectstatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("script", sa.Text, nullable=False),
        sa.Column("total_shots", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_created_at", "projects", ["created_at"])

    # Characters table
    op.create_table(
        "characters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("reference_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_characters_project_id", "characters", ["project_id"])

    # Scenes table
    op.create_table(
        "scenes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_scenes_project_id", "scenes", ["project_id"])
    op.create_index("ix_scenes_order", "scenes", ["project_id", "order_index"])

    # Shots table
    op.create_table(
        "shots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("scene_id", UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column(
            "shot_type",
            sa.Enum("t2v", "i2v", name="shottype"),
            nullable=False,
            server_default="t2v",
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "failed", name="shotstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("negative_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("duration_frames", sa.Integer, nullable=False, server_default="81"),
        sa.Column("width", sa.Integer, nullable=False, server_default="640"),
        sa.Column("height", sa.Integer, nullable=False, server_default="640"),
        sa.Column("seed", sa.Integer, nullable=True),
        sa.Column("character_ids", JSON, nullable=False, server_default="[]"),
        sa.Column("reference_key", sa.String(512), nullable=True),
        sa.Column("output_key", sa.String(512), nullable=True),
        sa.Column("job_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_shots_project_id", "shots", ["project_id"])
    op.create_index("ix_shots_scene_id", "shots", ["scene_id"])
    op.create_index("ix_shots_status", "shots", ["status"])
    op.create_index("ix_shots_order", "shots", ["project_id", "order_index"])


def downgrade() -> None:
    op.drop_table("shots")
    op.drop_table("scenes")
    op.drop_table("characters")
    op.drop_table("projects")
    op.execute("DROP TYPE IF EXISTS projectstatus")
    op.execute("DROP TYPE IF EXISTS shotstatus")
    op.execute("DROP TYPE IF EXISTS shottype")
