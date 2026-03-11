from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class SimRun(Base):
    __tablename__ = "sim_runs"
    __table_args__ = (
        Index("ix_sim_runs_user_season_week", "user_id", "season", "week"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    num_sims: Mapped[int] = mapped_column(Integer, default=10000)
    platform: Mapped[str] = mapped_column(String(20), default="draftkings")
    contest_type: Mapped[str] = mapped_column(String(20), default="gpp")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    results_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class SimResult(Base):
    __tablename__ = "sim_results"
    __table_args__ = (
        Index("ix_sim_results_run_player", "sim_run_id", "player_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sim_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sim_runs.id"), nullable=False, index=True
    )
    player_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("players.id"), nullable=False
    )
    avg_points: Mapped[float] = mapped_column(Float, nullable=False)
    median_points: Mapped[float] = mapped_column(Float, nullable=False)
    std_dev: Mapped[float] = mapped_column(Float, nullable=False)
    floor: Mapped[float] = mapped_column(Float, nullable=False)
    ceiling: Mapped[float] = mapped_column(Float, nullable=False)
    percentile_25: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    percentile_75: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    optimal_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
