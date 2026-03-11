from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class SimRunCreate(BaseModel):
    season: int = 2025
    week: int = 1
    num_sims: int = 10000
    platform: str = "draftkings"
    contest_type: str = "gpp"
    locked_players: Optional[List[str]] = None
    excluded_players: Optional[List[str]] = None
    config: Optional[Dict] = None


class SimRunResponse(BaseModel):
    id: str
    user_id: str
    season: int
    week: int
    num_sims: int
    status: str
    platform: Optional[str] = "draftkings"
    contest_type: Optional[str] = "gpp"
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SimPlayerResult(BaseModel):
    player_id: str
    name: str
    position: str
    team: str
    salary: int
    projected_points: float
    avg_points: float
    median_points: float
    std_dev: float
    floor: float
    ceiling: float
    percentile_25: Optional[float] = None
    percentile_75: Optional[float] = None
    boom_rate: Optional[float] = None
    bust_rate: Optional[float] = None


class StackResult(BaseModel):
    player_1: str
    player_2: str
    team_1: str
    team_2: str
    frequency: float


class SimResultsResponse(BaseModel):
    sim_id: str
    status: str
    num_sims: int
    players: List[SimPlayerResult] = []
    stacks: List[StackResult] = []
    lineup_score_avg: Optional[float] = None
    lineup_score_p90: Optional[float] = None
    lineup_scores_histogram: Optional[List[float]] = None


class LineupPlayer(BaseModel):
    id: str
    name: str
    position: str
    team: str
    salary: int
    projected_points: float

    model_config = {"from_attributes": True}


class OptimizedLineup(BaseModel):
    players: List[LineupPlayer]
    total_salary: int
    total_projected: float


class OptimizeRequest(BaseModel):
    season: int = 2025
    week: int = 1
    platform: str = "draftkings"
    contest_type: str = "gpp"
    num_lineups: int = 1
    salary_cap: Optional[int] = None
    locked_players: Optional[List[str]] = None
    excluded_players: Optional[List[str]] = None
    max_per_team: int = 4


class SimResultResponse(BaseModel):
    id: str
    sim_run_id: str
    player_id: str
    avg_points: float
    median_points: float
    std_dev: float
    floor: float
    ceiling: float
    percentile_25: Optional[float] = None
    percentile_75: Optional[float] = None
    optimal_rate: Optional[float] = None

    model_config = {"from_attributes": True}
