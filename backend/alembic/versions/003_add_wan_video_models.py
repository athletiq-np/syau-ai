"""Add WAN 2.2 video model

Revision ID: 003
Revises: 002
Create Date: 2026-03-31 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO models (id, name, display_name, type, local_path, is_enabled,
                            max_width, max_height, credit_cost, created_at)
        SELECT gen_random_uuid(), 'wan-2.2', 'WAN 2.2 (Primary)', 'video',
               '/data/ComfyUI/models/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors', true, 576, 576, 1, now()
        WHERE NOT EXISTS (
            SELECT 1 FROM models WHERE name = 'wan-2.2'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM models WHERE name = 'wan-2.2'")
