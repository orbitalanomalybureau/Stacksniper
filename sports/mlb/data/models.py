"""
STACKSNIPER MLB — Data Models
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class PlayerProjection:
    """A single player's projected stats for one simulation run."""
    player_id: int
    name: str
    team: str
    position: str
    opponent: str
    is_home: bool
    salary: int = 0
    game_pk: int = 0

    # v3 Phase 9.1: Multi-position eligibility
    positions: List[str] = field(default_factory=list)
    primary_position: str = ""

    # v3 Phase 9.2: Player handedness
    bats: str = "R"
    throws: str = "R"

    # v3 Phase 9.3: DK/FD player IDs
    dk_id: Optional[str] = None
    fd_id: Optional[str] = None

    # Hitter projections
    plate_appearances: float = 0.0
    at_bats: float = 0.0
    singles: float = 0.0
    doubles: float = 0.0
    triples: float = 0.0
    home_runs: float = 0.0
    rbi: float = 0.0
    runs: float = 0.0
    walks: float = 0.0
    hbp: float = 0.0
    stolen_bases: float = 0.0
    strikeouts: float = 0.0

    # Pitcher projections
    innings_pitched: float = 0.0
    pitcher_strikeouts: float = 0.0
    earned_runs: float = 0.0
    hits_against: float = 0.0
    walks_against: float = 0.0
    hbp_against: float = 0.0
    win_probability: float = 0.0

    # DFS
    dk_points: float = 0.0
    dk_points_std: float = 0.0
    value: float = 0.0  # pts / salary * 1000

    # Simulation results (np.ndarray after simulation, list default for compat)
    sim_points: any = field(default_factory=list)
    ceiling: float = 0.0
    floor: float = 0.0
    median: float = 0.0
    ownership_proj: float = 0.0

    # v3 Phase 1.8: Convergence detection — actual sims used (may be < requested)
    actual_sims_used: int = 0

    # v6 Sprint 5.1: Per-stat simulation distributions for props analysis
    # Hitter per-sim stat arrays
    sim_hits: list = None
    sim_hrs: list = None
    sim_rbi: list = None
    sim_runs: list = None
    sim_sb: list = None
    sim_total_bases: list = None
    # Pitcher per-sim stat arrays
    sim_ks: list = None
    sim_er: list = None
    sim_outs: list = None
    sim_hits_allowed: list = None

@dataclass
class GameProjection:
    """Projected outcome of a single MLB game."""
    game_pk: int
    away_team: str
    home_team: str
    away_pitcher: str
    home_pitcher: str
    venue: str
    away_win_pct: float = 0.5
    home_win_pct: float = 0.5
    total_runs: float = 8.5
    away_runs: float = 4.25
    home_runs: float = 4.25
    away_implied_total: float = 4.25
    home_implied_total: float = 4.25
    weather_impact: float = 1.0
    park_factor: float = 1.0
    sim_results: list = field(default_factory=list)

@dataclass
class SimulationResult:
    """Result of a full simulation run."""
    sim_id: int
    timestamp: str
    num_sims: int
    games: list = field(default_factory=list)
    player_projections: list = field(default_factory=list)
    optimal_lineups: list = field(default_factory=list)
    confidence_score: float = 0.0

    # v3 Phase 9.5: Agent metadata
    agents_used: List[str] = field(default_factory=list)
    agent_weights: Dict[str, float] = field(default_factory=dict)
    seed: int = 0

    # v6 Performance: Phase timing instrumentation
    timings: Dict[str, float] = field(default_factory=dict)
