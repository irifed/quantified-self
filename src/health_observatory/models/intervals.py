from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from health_observatory.models.base import Base


class DailyRecovery(Base):
    __tablename__ = "daily_recovery"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    resting_hr: Mapped[float | None] = mapped_column(Float)
    hrv: Mapped[float | None] = mapped_column(Float)
    sleep_hours: Mapped[float | None] = mapped_column(Float)
    sleep_score: Mapped[float | None] = mapped_column(Float)
    fitness: Mapped[float | None] = mapped_column(Float)
    fatigue: Mapped[float | None] = mapped_column(Float)
    form: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), default="intervals_icu")
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Workout(Base):
    __tablename__ = "workouts"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    intervals_activity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    activity_type: Mapped[str | None] = mapped_column(String(64))
    duration_minutes: Mapped[float | None] = mapped_column(Float)
    training_load: Mapped[float | None] = mapped_column(Float)
    avg_hr: Mapped[float | None] = mapped_column(Float)
    max_hr: Mapped[float | None] = mapped_column(Float)
    calories: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), default="intervals_icu")
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
