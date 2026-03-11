from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.player import Player
from app.models.projection import Projection
from app.models.simulation import SimRun
from app.models.user import User
from app.schemas.simulation import OptimizedLineup, OptimizeRequest
from app.services.optimizer import LineupOptimizer

router = APIRouter()


async def _load_player_pool(
    db: AsyncSession, season: int, week: int
) -> List[dict]:
    """Load players + projections as optimizer-ready dicts."""
    stmt = (
        select(Player, Projection)
        .join(Projection, Player.id == Projection.player_id)
        .where(Projection.season == season, Projection.week == week)
    )
    result = await db.execute(stmt)
    rows = result.all()

    pool = []
    for player, proj in rows:
        pool.append({
            "id": player.id,
            "external_id": player.external_id,
            "name": player.name,
            "position": player.position,
            "team": player.team,
            "salary": player.salary or 5000,
            "projected_points": proj.projected_points,
            "floor": proj.floor,
            "ceiling": proj.ceiling,
            "ownership": player.ownership or 10.0,
        })
    return pool


@router.post("/optimize", response_model=List[OptimizedLineup])
async def optimize_lineups(
    body: OptimizeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pool = await _load_player_pool(db, body.season, body.week)

    # Auto-generate projections if none exist
    if not pool:
        from app.services.projection_engine import ProjectionEngine
        engine = ProjectionEngine(db)
        await engine.generate_projections(body.season, body.week)
        pool = await _load_player_pool(db, body.season, body.week)

    if not pool:
        raise HTTPException(status_code=404, detail="No projections available")

    optimizer = LineupOptimizer(
        platform=body.platform,
        contest_type=body.contest_type,
    )
    lineups = optimizer.optimize(
        pool,
        num_lineups=body.num_lineups,
        salary_cap=body.salary_cap,
        locked_ids=body.locked_players,
        excluded_ids=body.excluded_players,
        max_per_team=body.max_per_team,
    )

    return [
        OptimizedLineup(
            players=lu["players"],
            total_salary=lu["total_salary"],
            total_projected=lu["total_projected"],
        )
        for lu in lineups
    ]


@router.get("/{sim_id}/lineups", response_model=List[OptimizedLineup])
async def get_sim_lineups(
    sim_id: str,
    num: int = Query(20, ge=1, le=150),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get top N optimized lineups from a completed simulation."""
    result = await db.execute(
        select(SimRun).where(SimRun.id == sim_id, SimRun.user_id == user.id)
    )
    sim_run = result.scalar_one_or_none()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if sim_run.status != "completed":
        raise HTTPException(status_code=400, detail="Simulation not yet complete")

    data = sim_run.results_data or {}
    sim_players = data.get("players", [])
    if not sim_players:
        return []

    pool = []
    for sp in sim_players:
        pool.append({
            "id": sp["player_id"],
            "external_id": sp.get("external_id", sp["name"]),
            "name": sp["name"],
            "position": sp["position"],
            "team": sp["team"],
            "salary": sp["salary"],
            "projected_points": sp["avg_points"],
            "floor": sp.get("floor", sp["avg_points"] * 0.7),
            "ceiling": sp.get("ceiling", sp["avg_points"] * 1.3),
            "ownership": 10.0,
        })

    optimizer = LineupOptimizer(
        platform=sim_run.platform or "draftkings",
        contest_type=sim_run.contest_type or "gpp",
    )
    lineups = optimizer.optimize(pool, num_lineups=num)

    return [
        OptimizedLineup(
            players=lu["players"],
            total_salary=lu["total_salary"],
            total_projected=lu["total_projected"],
        )
        for lu in lineups
    ]


@router.get("/{sim_id}/export")
async def export_lineups_csv(
    sim_id: str,
    platform: str = Query("draftkings"),
    num: int = Query(20, ge=1, le=150),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export optimized lineups as CSV for DK/FD upload."""
    result = await db.execute(
        select(SimRun).where(SimRun.id == sim_id, SimRun.user_id == user.id)
    )
    sim_run = result.scalar_one_or_none()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if sim_run.status != "completed":
        raise HTTPException(status_code=400, detail="Simulation not yet complete")

    data = sim_run.results_data or {}
    sim_players = data.get("players", [])
    if not sim_players:
        raise HTTPException(status_code=400, detail="No simulation results")

    pool = []
    for sp in sim_players:
        pool.append({
            "id": sp["player_id"],
            "external_id": sp.get("external_id", sp["name"]),
            "name": sp["name"],
            "position": sp["position"],
            "team": sp["team"],
            "salary": sp["salary"],
            "projected_points": sp["avg_points"],
            "floor": sp.get("floor", 0),
            "ceiling": sp.get("ceiling", 0),
            "ownership": 10.0,
        })

    optimizer = LineupOptimizer(platform=platform, contest_type="gpp")
    lineups = optimizer.optimize(pool, num_lineups=num)
    csv_content = optimizer.export_csv(lineups)

    filename = f"lineups_{platform}_{sim_id[:8]}.csv"
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/")
async def get_saved_lineups(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return user's recent completed simulations (as lineup sources)."""
    result = await db.execute(
        select(SimRun)
        .where(SimRun.user_id == user.id, SimRun.status == "completed")
        .order_by(SimRun.created_at.desc())
        .limit(20)
    )
    sims = result.scalars().all()
    return [
        {
            "sim_id": s.id,
            "season": s.season,
            "week": s.week,
            "platform": s.platform,
            "num_sims": s.num_sims,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sims
    ]
