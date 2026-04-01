"""Initial schema - jobs and models tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "failed", "cancelled", name="jobstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("negative_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("params", JSON, nullable=False, server_default="{}"),
        sa.Column("output_keys", JSON, nullable=True),
        sa.Column("seed_used", sa.Integer, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_type", "jobs", ["type"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])

    op.create_table(
        "models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), unique=True, nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("local_path", sa.String(512), nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("max_width", sa.Integer, nullable=True),
        sa.Column("max_height", sa.Integer, nullable=True),
        sa.Column("credit_cost", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_models_name", "models", ["name"])
    op.create_index("ix_models_type", "models", ["type"])

    # Seed the models table with our GPU server models
    op.execute("""
        INSERT INTO models (id, name, display_name, type, local_path, is_enabled,
                            max_width, max_height, credit_cost, created_at)
        VALUES
            (gen_random_uuid(), 'qwen-image-2512', 'Qwen Image 2512', 'image',
             '/data/models/t2i/qwen-image-2512', true, 2512, 2512, 1, now()),
            (gen_random_uuid(), 'qwen-image-layered', 'Qwen Image Layered', 'image',
             '/data/models/layered/qwen-image-layered', true, 1024, 1024, 1, now()),
            (gen_random_uuid(), 'rmbg-1.4', 'Background Removal (RMBG 1.4)', 'tool',
             '/data/models/matting/rmbg-1.4', true, null, null, 1, now()),
            (gen_random_uuid(), 'qwen3.5-vl-7b', 'Qwen 3.5 VL 7B (Vision)', 'vision',
             '/data/models/qwen3.5-vl-7b', true, null, null, 1, now()),
            (gen_random_uuid(), 'qwen3.5-7b-instruct', 'Qwen 3.5 7B Instruct (Chat)', 'chat',
             '/data/models/qwen3.5-7b-instruct', true, null, null, 1, now())
    """)


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("models")
    op.execute("DROP TYPE IF EXISTS jobstatus")
