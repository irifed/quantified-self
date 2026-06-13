"""Create the Withings body composition hypertable.

Revision ID: 0001
Revises:
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.create_table(
        "body_composition",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withings_grpid", sa.BigInteger(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("fat_ratio_pct", sa.Float(), nullable=True),
        sa.Column("fat_mass_kg", sa.Float(), nullable=True),
        sa.Column("fat_free_mass_kg", sa.Float(), nullable=True),
        sa.Column("muscle_mass_kg", sa.Float(), nullable=True),
        sa.Column("hydration_kg", sa.Float(), nullable=True),
        sa.Column("bone_mass_kg", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "unknown_measurements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("timestamp", "withings_grpid"),
    )
    op.execute(
        "SELECT create_hypertable('body_composition', by_range('timestamp'), "
        "if_not_exists => TRUE)"
    )
    op.create_index(
        "ix_body_composition_timestamp_desc",
        "body_composition",
        [sa.text("timestamp DESC")],
    )

    op.create_table(
        "sync_state",
        sa.Column("source", sa.String(length=32), primary_key=True),
        sa.Column("last_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("sync_state")
    op.drop_index("ix_body_composition_timestamp_desc", table_name="body_composition")
    op.drop_table("body_composition")
