from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class Projection(Base):
    __tablename__ = "projections"
    __table_args__ = (
        Index("ix_projections_player_season_week", "player_id", "season", "week"),
        Index("ix_projections_season_week_source", "season", "week", "source"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("players.id"), nullable=False, index=True
    )
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="model")  # model, manual, consensus
    projected_points: Mapped[float] = mapped_column(Float, nullable=False)
    floor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ceiling: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    std_dev: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pass_yds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pass_tds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rush_yds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rush_tds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rec_yds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rec_tds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
