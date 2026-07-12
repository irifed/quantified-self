"""Create intervals.icu recovery and workout hypertables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_recovery",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resting_hr", sa.Float(), nullable=True),
        sa.Column("hrv", sa.Float(), nullable=True),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("sleep_score", sa.Float(), nullable=True),
        sa.Column("fitness", sa.Float(), nullable=True),
        sa.Column("fatigue", sa.Float(), nullable=True),
        sa.Column("form", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("timestamp"),
    )
    op.execute(
        "SELECT create_hypertable('daily_recovery', by_range('timestamp'), "
        "if_not_exists => TRUE)"
    )
    op.create_index(
        "ix_daily_recovery_timestamp_desc",
        "daily_recovery",
        [sa.text("timestamp DESC")],
    )

    op.create_table(
        "workouts",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("intervals_activity_id", sa.String(length=64), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=True),
        sa.Column("duration_minutes", sa.Float(), nullable=True),
        sa.Column("training_load", sa.Float(), nullable=True),
        sa.Column("avg_hr", sa.Float(), nullable=True),
        sa.Column("max_hr", sa.Float(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("timestamp", "intervals_activity_id"),
    )
    op.execute("SELECT create_hypertable('workouts', by_range('timestamp'), if_not_exists => TRUE)")
    op.create_index(
        "ix_workouts_timestamp_desc",
        "workouts",
        [sa.text("timestamp DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_workouts_timestamp_desc", table_name="workouts")
    op.drop_table("workouts")
    op.drop_index("ix_daily_recovery_timestamp_desc", table_name="daily_recovery")
    op.drop_table("daily_recovery")
