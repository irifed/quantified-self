from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from health_observatory.models.base import Base


class BodyComposition(Base):
    __tablename__ = "body_composition"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    withings_grpid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    fat_ratio_pct: Mapped[float | None] = mapped_column(Float)
    fat_mass_kg: Mapped[float | None] = mapped_column(Float)
    fat_free_mass_kg: Mapped[float | None] = mapped_column(Float)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Float)
    hydration_kg: Mapped[float | None] = mapped_column(Float)
    bone_mass_kg: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), default="withings")
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    unknown_measurements: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)


class SyncState(Base):
    __tablename__ = "sync_state"

    source: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cursor: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
