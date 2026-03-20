"""
STACKSNIPER MLB — Enhanced Ownership Projection Model (Phase 3.4)

Projects ownership percentages using:
- Salary-based ownership curves
- Position scarcity factors
- Recency bias (recent performance/news)
- Stacking correlation (popular stack teams)
- Contest-type adjustment (cash = flatter, GPP = top-heavy)
"""
import numpy as np
from typing import List, Dict
from sports.mlb.data.models import PlayerProjection
from sports.mlb.utils.logger import get_logger

log = get_logger("Ownership")

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

# Salary thresholds (DK-centric; works for FD scaling too)
_SALARY_BANDS = [
    (2000, 3500, 1.35),   # Punt range — if projection is decent, very popular
    (3500, 5000, 1.20),   # Value range
    (5000, 7000, 1.00),   # Mid-tier — neutral
    (7000, 9000, 0.90),   # Premium
    (9000, 15000, 0.80),  # Elite — lower base ownership, concentrated on studs
]

# Position scarcity multipliers (higher = more concentrated ownership)
_POSITION_SCARCITY = {
    "SP": 1.40,   # Elite SPs draw heavy ownership
    "RP": 0.60,   # Relievers rarely owned unless saves specialist
    "P":  1.20,   # Generic pitcher slot
    "C":  1.15,   # Thin position — top guys get owned
    "1B": 1.00,
    "2B": 1.00,
    "3B": 1.00,
    "SS": 1.05,
    "OF": 0.95,   # Deep position — ownership more spread
    "DH": 0.90,
    "UTIL": 0.90,
}

# Contest-type profiles
_CONTEST_PROFILES = {
    "gpp": {
        "top_heavy_exp": 2.0,    # Exponent applied to rank-based curve
        "noise_std": 3.5,        # More variance in GPPs
        "ceiling_weight": 0.40,  # Ceiling matters more
        "value_weight": 2.5,     # Value plays get ownership
        "max_ownership": 45.0,
        "min_ownership": 0.5,
    },
    "cash": {
        "top_heavy_exp": 1.2,    # Flatter distribution
        "noise_std": 1.5,        # Less variance — field converges
        "ceiling_weight": 0.10,
        "value_weight": 1.5,
        "max_ownership": 60.0,   # Cash chalk can be very high
        "min_ownership": 1.0,
    },
    "se": {  # Single-entry
        "top_heavy_exp": 1.6,
        "noise_std": 2.5,
        "ceiling_weight": 0.25,
        "value_weight": 2.0,
        "max_ownership": 50.0,
        "min_ownership": 0.8,
    },
}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def project_ownership(
    players: List[PlayerProjection],
    contest_type: str = "gpp",
) -> None:
    """
    Project ownership percentages for each player **in-place**.

    Parameters
    ----------
    players : list[PlayerProjection]
        Full player pool. Each player's ``ownership_proj`` field is updated.
    contest_type : str
        One of ``"gpp"``, ``"cash"``, or ``"se"`` (single-entry).
        Controls the shape of the ownership distribution.
    """
    if not players:
        return

    profile = _CONTEST_PROFILES.get(contest_type, _CONTEST_PROFILES["gpp"])

    # ---- Step 1: Compute raw ownership scores ----
    for p in players:
        p._ownership_score = _compute_raw_score(p, profile)

    # ---- Step 2: Stacking correlation bump ----
    _apply_stacking_correlation(players, profile)

    # ---- Step 3: Normalize within position groups ----
    _normalize_by_position(players, profile)

    # ---- Step 4: Clean up temp attributes ----
    for p in players:
        for attr in ("_ownership_score", "_stack_bump"):
            if hasattr(p, attr):
                delattr(p, attr)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #

def _compute_raw_score(p: PlayerProjection, profile: dict) -> float:
    """Build a raw ownership-attractiveness score for a single player."""
    score = 0.0

    # -- 1. Salary-based ownership curve --
    salary_mult = _salary_multiplier(p.salary)

    # -- 2. Value play factor (cheaper + good projection) --
    if p.salary > 0 and p.dk_points > 0:
        score += p.value * profile["value_weight"] * salary_mult

    # -- 3. Raw projection component --
    score += p.dk_points * 0.5

    # -- 4. Ceiling component (weighted by contest type) --
    if p.ceiling > 0:
        ceiling_upside = max(0, p.ceiling - p.dk_points)
        score += ceiling_upside * profile["ceiling_weight"]

    # -- 5. Position scarcity --
    pos_key = p.position if p.position in _POSITION_SCARCITY else "UTIL"
    score *= _POSITION_SCARCITY.get(pos_key, 1.0)

    # -- 6. Recency / momentum bias --
    score *= _recency_multiplier(p)

    return score


def _salary_multiplier(salary: int) -> float:
    """Return a multiplier based on salary band. Cheaper + viable = more owned."""
    for low, high, mult in _SALARY_BANDS:
        if low <= salary < high:
            return mult
    # Below minimum or above maximum
    if salary < _SALARY_BANDS[0][0]:
        return 1.40  # Min-price plays are very popular
    return 0.75  # Super-premium


def _recency_multiplier(p: PlayerProjection) -> float:
    """
    Approximate recency bias. Players with high recent ceiling relative to
    their median get a bump (the "hot hand" effect that drives ownership).

    Without a dedicated news feed, we proxy recency via the gap between
    ceiling and median — a wide gap implies recent variance/buzz.
    """
    if p.median <= 0 or p.ceiling <= 0:
        return 1.0

    # Ratio of ceiling to median — higher means more "buzz-worthy"
    ratio = p.ceiling / p.median
    if ratio >= 2.0:
        return 1.25  # Huge ceiling relative to median — "breakout" candidate
    elif ratio >= 1.5:
        return 1.15
    elif ratio >= 1.2:
        return 1.05
    return 1.0


def _apply_stacking_correlation(
    players: List[PlayerProjection], profile: dict
) -> None:
    """
    Popular stack teams get a team-level ownership bump.
    Teams with multiple high-scoring hitters become natural stacking targets,
    which drives correlated ownership across those players.
    """
    # Aggregate team quality for hitters only
    team_scores: Dict[str, float] = {}
    team_counts: Dict[str, int] = {}
    for p in players:
        if p.position in ("SP", "RP", "P"):
            continue
        team_scores[p.team] = team_scores.get(p.team, 0) + p.dk_points
        team_counts[p.team] = team_counts.get(p.team, 0) + 1

    if not team_scores:
        return

    # Rank teams by total projected output
    team_list = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)
    n_teams = len(team_list)

    # Top-third teams get a stacking bump
    team_bump: Dict[str, float] = {}
    for rank, (team, total_pts) in enumerate(team_list):
        pct = (n_teams - rank) / n_teams  # 1.0 for best, ~0 for worst
        if pct >= 0.67:
            team_bump[team] = 1.15  # Top third — popular stacking target
        elif pct >= 0.33:
            team_bump[team] = 1.05  # Middle third — moderate interest
        else:
            team_bump[team] = 0.95  # Bottom third — contrarian territory

    # Apply to hitters
    for p in players:
        if p.position in ("SP", "RP", "P"):
            continue
        bump = team_bump.get(p.team, 1.0)
        p._ownership_score = getattr(p, '_ownership_score', 0) * bump
        p._stack_bump = bump


def _normalize_by_position(
    players: List[PlayerProjection], profile: dict
) -> None:
    """
    Convert raw scores into realistic ownership percentages,
    normalized within each position group.
    """
    top_heavy_exp = profile["top_heavy_exp"]
    noise_std = profile["noise_std"]
    max_own = profile["max_ownership"]
    min_own = profile["min_ownership"]

    # Group by position bucket
    positions: Dict[str, List[PlayerProjection]] = {}
    for p in players:
        pos = "P" if p.position in ("SP", "RP", "P") else p.position
        positions.setdefault(pos, []).append(p)

    for pos, pos_players in positions.items():
        pos_players.sort(
            key=lambda x: getattr(x, '_ownership_score', 0), reverse=True
        )
        n = len(pos_players)
        if n == 0:
            continue

        for i, p in enumerate(pos_players):
            # Rank-based curve: top player gets ~1.0, worst gets ~0.0
            rank_pct = (n - i) / n

            # Apply top-heavy exponent — GPP concentrates at top, cash is flatter
            shaped = rank_pct ** top_heavy_exp

            # Scale to ownership range
            base_own = shaped * (max_own - min_own) + min_own

            # Add realistic noise
            noise = np.random.normal(0, noise_std)
            final = base_own + noise

            p.ownership_proj = round(
                max(min_own, min(max_own, final)), 1
            )
