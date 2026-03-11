from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PlayerBase(BaseModel):
    name: str
    team: str
    position: str
    salary: Optional[int] = None
    ownership: Optional[float] = None
    status: str = "active"


class PlayerResponse(PlayerBase):
    id: str
    external_id: str
    season: int
    week: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectionResponse(BaseModel):
    id: str
    player_id: str
    season: int
    week: int
    source: str
    projected_points: float
    floor: Optional[float] = None
    ceiling: Optional[float] = None
    std_dev: Optional[float] = None
    pass_yds: Optional[float] = None
    pass_tds: Optional[float] = None
    rush_yds: Optional[float] = None
    rush_tds: Optional[float] = None
    rec: Optional[float] = None
    rec_yds: Optional[float] = None
    rec_tds: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlayerWithProjection(BaseModel):
    """Flat response combining player + projection for the projections table."""
    id: str
    name: str
    team: str
    position: str
    salary: Optional[int] = None
    opponent: Optional[str] = None
    projected_points: float = 0.0
    floor: Optional[float] = None
    ceiling: Optional[float] = None
    std_dev: Optional[float] = None
    ownership: Optional[float] = None
    value: Optional[float] = None
    pass_yds: Optional[float] = None
    pass_tds: Optional[float] = None
    rush_yds: Optional[float] = None
    rush_tds: Optional[float] = None
    rec: Optional[float] = None
    rec_yds: Optional[float] = None
    rec_tds: Optional[float] = None
