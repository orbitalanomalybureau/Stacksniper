"""
MLB API Router — FastAPI endpoints for MLB simulation, optimization, and data.
Mirrors the Flask routes from the MLB V8.0 build adapted to the unified platform.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
log = logging.getLogger("stacksniper.mlb")

# ─── Lazy-init singletons ────────────────────────────────────────────────────
_engine = None
_optimizer = None


def _get_engine():
    global _engine
    if _engine is None:
        from sports.mlb.simulation.engine import SimulationEngine
        _engine = SimulationEngine()
    return _engine


def _get_optimizer():
    global _optimizer
    if _optimizer is None:
        from sports.mlb.optimizer.dk_optimizer import DKOptimizer
        _optimizer = DKOptimizer()
    return _optimizer


# ─── Request / Response Schemas ───────────────────────────────────────────────

class SimulateRequest(BaseModel):
    num_sims: int = Field(default=500, ge=100, le=10000)
    date: str | None = None
    vegas: dict[str, Any] = Field(default_factory=dict)
    salaries: dict[str, int] = Field(default_factory=dict)


class OptimizeRequest(BaseModel):
    num_lineups: int = Field(default=20, ge=1, le=150)
    max_exposure: float = Field(default=0.6, ge=0.1, le=1.0)
    contest_type: str = "gpp"
    platform: str = "draftkings"
    locks: list[int] = Field(default_factory=list)
    excludes: list[int] = Field(default_factory=list)
    salaries: dict[str, int] = Field(default_factory=dict)


class StacksRequest(BaseModel):
    pass


class BriefRequest(BaseModel):
    date: str | None = None


# ─── Serialization Helpers ────────────────────────────────────────────────────

def _serialize_player(p) -> dict:
    return {
        "id": p.player_id,
        "name": p.name,
        "team": p.team,
        "position": p.position,
        "opponent": getattr(p, "opponent", ""),
        "is_home": getattr(p, "is_home", False),
        "salary": p.salary,
        "dk_points": p.dk_points,
        "dk_std": getattr(p, "dk_points_std", 0),
        "ceiling": p.ceiling,
        "floor": p.floor,
        "median": getattr(p, "median", 0),
        "value": getattr(p, "value", 0),
        "ownership_proj": getattr(p, "ownership_proj", None),
    }


def _serialize_player_brief(p) -> dict:
    return {
        "name": p.name,
        "team": p.team,
        "position": p.position,
        "salary": p.salary,
        "dk_points": p.dk_points,
    }


# ─── Schedule ─────────────────────────────────────────────────────────────────

@router.get("/schedule")
async def get_schedule(date: str | None = None):
    """Get MLB schedule for a given date."""
    from sports.mlb.data.mlb_api import mlb_api

    if date:
        try:
            game_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")
    else:
        from datetime import date as date_cls
        game_date = date_cls.today()

    games = mlb_api.get_schedule(game_date)
    return {"date": str(game_date), "games": games, "count": len(games)}


# ─── Standings ────────────────────────────────────────────────────────────────

@router.get("/standings")
async def get_standings():
    """Get MLB standings."""
    from sports.mlb.data.mlb_api import mlb_api
    standings = mlb_api.get_standings()
    return {"standings": standings}


# ─── Simulate ─────────────────────────────────────────────────────────────────

@router.post("/simulate")
async def run_simulation(req: SimulateRequest):
    """Run Monte Carlo simulation for an MLB slate."""
    engine = _get_engine()

    if req.date:
        try:
            game_date = datetime.strptime(req.date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")
    else:
        game_date = date.today()

    num_sims = min(req.num_sims, 10000)
    log.info(f"Running {num_sims}-sim MLB simulation for {game_date}")
    engine.num_sims = num_sims

    try:
        result = engine.run_full_slate(game_date, req.vegas)
    except Exception as e:
        log.exception("Simulation failed")
        raise HTTPException(500, f"Simulation failed: {e}")

    # Apply custom salaries if provided
    if req.salaries:
        for p in result.player_projections:
            if str(p.player_id) in req.salaries:
                p.salary = req.salaries[str(p.player_id)]
                if p.salary > 0:
                    p.value = round(p.dk_points / p.salary * 1000, 2)

    # Project ownership
    try:
        from sports.mlb.simulation.ownership import project_ownership
        project_ownership(result.player_projections)
    except Exception:
        pass

    # Store result
    try:
        from sports.mlb.utils.sim_store import sim_store
        sim_store.save(result.sim_id, result)
    except Exception:
        pass

    return {
        "sim_id": result.sim_id,
        "timestamp": result.timestamp,
        "num_sims": result.num_sims,
        "confidence": result.confidence_score,
        "games_count": len(result.games),
        "players_count": len(result.player_projections),
        "players": [_serialize_player(p) for p in result.player_projections],
        "games": [
            {
                "game_pk": g.game_pk,
                "away": g.away_team,
                "home": g.home_team,
                "away_pitcher": g.away_pitcher,
                "home_pitcher": g.home_pitcher,
                "total_runs": g.total_runs,
            }
            for g in result.games
        ],
    }


# ─── Optimize ─────────────────────────────────────────────────────────────────

@router.post("/optimize")
async def optimize_lineups(req: OptimizeRequest):
    """Generate optimized DFS lineups from the last simulation."""
    try:
        from sports.mlb.utils.sim_store import sim_store
        last_result = sim_store.get_latest()
    except Exception:
        last_result = None

    if not last_result:
        raise HTTPException(400, "No simulation results available. Run /api/mlb/simulate first.")

    optimizer = _get_optimizer()

    # Use FanDuel optimizer if requested
    if req.platform == "fanduel":
        try:
            from sports.mlb.optimizer.fd_optimizer import FDOptimizer
            optimizer = FDOptimizer()
        except Exception:
            pass

    # Apply custom salaries
    if req.salaries:
        for p in last_result.player_projections:
            if str(p.player_id) in req.salaries:
                p.salary = req.salaries[str(p.player_id)]

    # Apply locks/excludes via exposure manager
    try:
        from sports.mlb.optimizer.exposure import ExposureManager
        exposure_mgr = ExposureManager()
        for pid in req.locks:
            exposure_mgr.lock_player(pid)
        for pid in req.excludes:
            exposure_mgr.exclude_player(pid)
    except Exception:
        exposure_mgr = None

    eligible = [p for p in last_result.player_projections if p.salary > 0]
    if exposure_mgr:
        eligible = [p for p in eligible if exposure_mgr.get_max_exposure(p.player_id) > 0]

    log.info(f"Optimizer: {len(eligible)} eligible players")

    try:
        lineups = optimizer.optimize(eligible, req.num_lineups, req.max_exposure)
    except Exception as e:
        log.exception("Optimization failed")
        raise HTTPException(500, f"Optimization failed: {e}")

    if not lineups:
        raise HTTPException(
            400,
            "Could not generate valid lineups. Check that players have salaries "
            "and there are enough eligible players per position.",
        )

    stacks = optimizer.find_stacks(eligible)

    exposure_report = {}
    if exposure_mgr:
        try:
            exposure_report = exposure_mgr.calculate_exposure_report(lineups)
        except Exception:
            pass

    return {
        "lineups_count": len(lineups),
        "lineups": [
            {
                "rank": i + 1,
                "salary": lu["salary"],
                "salary_remaining": lu["salary_remaining"],
                "projected": lu["projected_points"],
                "ceiling": lu["ceiling"],
                "floor": lu["floor"],
                "players": [_serialize_player_brief(p) for p in lu["players"]],
            }
            for i, lu in enumerate(lineups)
        ],
        "top_stacks": stacks[:15],
        "exposure": exposure_report,
    }


# ─── Stacks ───────────────────────────────────────────────────────────────────

@router.post("/stacks")
async def get_stacks():
    """Get stack recommendations from last simulation."""
    try:
        from sports.mlb.utils.sim_store import sim_store
        last_result = sim_store.get_latest()
    except Exception:
        last_result = None

    if not last_result:
        raise HTTPException(400, "Run simulation first.")

    optimizer = _get_optimizer()
    eligible = [p for p in last_result.player_projections if p.salary > 0]
    stacks = optimizer.find_stacks(eligible)
    return {"stacks": stacks}


# ─── Player Distribution ─────────────────────────────────────────────────────

@router.get("/player/{player_id}/distribution")
async def get_player_distribution(player_id: int):
    """Get simulation point distribution for a player."""
    try:
        from sports.mlb.utils.sim_store import sim_store
        last_result = sim_store.get_latest()
    except Exception:
        last_result = None

    if not last_result:
        raise HTTPException(400, "Run simulation first.")

    player = None
    for p in last_result.player_projections:
        if p.player_id == player_id:
            player = p
            break

    if not player or not hasattr(player, "sim_points") or not hasattr(player.sim_points, "__len__") or len(player.sim_points) == 0:
        raise HTTPException(404, "Player not found in simulation.")

    pts = player.sim_points
    if not isinstance(pts, np.ndarray):
        pts = np.array(pts)

    hist, bin_edges = np.histogram(pts, bins=25)

    return {
        "player_id": player_id,
        "name": player.name,
        "num_sims": len(pts),
        "mean": round(float(np.mean(pts)), 2),
        "median": round(float(np.median(pts)), 2),
        "std": round(float(np.std(pts)), 2),
        "min": round(float(np.min(pts)), 2),
        "max": round(float(np.max(pts)), 2),
        "p10": round(float(np.percentile(pts, 10)), 2),
        "p25": round(float(np.percentile(pts, 25)), 2),
        "p75": round(float(np.percentile(pts, 75)), 2),
        "p90": round(float(np.percentile(pts, 90)), 2),
        "p95": round(float(np.percentile(pts, 95)), 2),
        "histogram": {
            "counts": hist.tolist(),
            "bin_edges": [round(b, 2) for b in bin_edges.tolist()],
        },
    }
