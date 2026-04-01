"""Add qwen-image-edit and ltx-2.3 models, sync server paths

Revision ID: 002
Revises: 001
Create Date: 2026-03-31 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE models
        SET local_path = '/data/models/utility/rmbg-1.4'
        WHERE name = 'rmbg-1.4'
    """)
    op.execute("""
        UPDATE models
        SET local_path = '/data/models/vlm/qwen3.5-vl-7b'
        WHERE name = 'qwen3.5-vl-7b'
    """)
    op.execute("""
        UPDATE models
        SET local_path = '/data/models/llm/qwen3.5-7b-instruct'
        WHERE name = 'qwen3.5-7b-instruct'
    """)
    op.execute("""
        INSERT INTO models (id, name, display_name, type, local_path, is_enabled,
                            max_width, max_height, credit_cost, created_at)
        SELECT gen_random_uuid(), 'qwen-image-edit', 'Qwen Image Edit', 'image',
               '/data/models/qwen-image-edit', true, 2048, 2048, 1, now()
        WHERE NOT EXISTS (
            SELECT 1 FROM models WHERE name = 'qwen-image-edit'
        )
    """)
    op.execute("""
        INSERT INTO models (id, name, display_name, type, local_path, is_enabled,
                            max_width, max_height, credit_cost, created_at)
        SELECT gen_random_uuid(), 'ltx-2.3', 'LTX 2.3', 'video',
               '/data/models/ltx-2.3', true, 1024, 1024, 1, now()
        WHERE NOT EXISTS (
            SELECT 1 FROM models WHERE name = 'ltx-2.3'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM models WHERE name = 'qwen-image-edit'")
    op.execute("DELETE FROM models WHERE name = 'ltx-2.3'")
    op.execute("""
        UPDATE models
        SET local_path = '/data/models/matting/rmbg-1.4'
        WHERE name = 'rmbg-1.4'
    """)
    op.execute("""
        UPDATE models
        SET local_path = '/data/models/qwen3.5-vl-7b'
        WHERE name = 'qwen3.5-vl-7b'
    """)
    op.execute("""
        UPDATE models
        SET local_path = '/data/models/qwen3.5-7b-instruct'
        WHERE name = 'qwen3.5-7b-instruct'
    """)
