from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_effective_tier
from app.models.simulation import SimRun
from app.models.user import User
from app.schemas.simulation import SimRunCreate, SimRunResponse, SimResultsResponse
from app.tasks.sim_tasks import run_simulation_inline

router = APIRouter()

# Tier limits: sims per week
SIM_LIMITS = {"free": 5, "pro": 100, "elite": 999999}
NUM_SIMS_LIMITS = {"free": 1000, "pro": 5000, "elite": 10000}


async def _check_sim_limit(user: User, tier: str, db: AsyncSession):
    """Enforce weekly simulation limits."""
    limit = SIM_LIMITS.get(tier, 5)
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(func.count(SimRun.id)).where(
            SimRun.user_id == user.id,
            SimRun.created_at >= one_week_ago,
        )
    )
    count = result.scalar() or 0
    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Weekly simulation limit reached ({limit}). Upgrade for more.",
        )


@router.post("/", response_model=SimRunResponse, status_code=202)
async def create_simulation(
    body: SimRunCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tier = get_effective_tier(user)
    await _check_sim_limit(user, tier, db)

    # Enforce num_sims cap per tier
    max_sims = NUM_SIMS_LIMITS.get(tier, 1000)
    num_sims = min(body.num_sims, max_sims)

    config = body.config or {}
    if body.locked_players:
        config["locked_players"] = body.locked_players
    if body.excluded_players:
        config["excluded_players"] = body.excluded_players

    # Auto-generate projections if none exist for this week
    from app.models.projection import Projection
    proj_count = await db.execute(
        select(func.count(Projection.id)).where(
            Projection.season == body.season, Projection.week == body.week
        )
    )
    if (proj_count.scalar() or 0) == 0:
        from app.services.projection_engine import ProjectionEngine
        engine = ProjectionEngine(db)
        await engine.generate_projections(body.season, body.week)

    sim_run = SimRun(
        user_id=user.id,
        season=body.season,
        week=body.week,
        num_sims=num_sims,
        platform=body.platform,
        contest_type=body.contest_type,
        status="pending",
        config=config,
    )
    db.add(sim_run)
    await db.commit()
    await db.refresh(sim_run)

    # Run inline (no Celery in dev) — in prod, dispatch to Celery
    await run_simulation_inline(sim_run.id, db)
    await db.refresh(sim_run)

    return sim_run


@router.get("/", response_model=List[SimRunResponse])
async def list_simulations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SimRun)
        .where(SimRun.user_id == user.id)
        .order_by(SimRun.created_at.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.get("/{sim_id}", response_model=SimRunResponse)
async def get_simulation(
    sim_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SimRun).where(SimRun.id == sim_id, SimRun.user_id == user.id)
    )
    sim_run = result.scalar_one_or_none()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim_run


@router.get("/{sim_id}/results", response_model=SimResultsResponse)
async def get_simulation_results(
    sim_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SimRun).where(SimRun.id == sim_id, SimRun.user_id == user.id)
    )
    sim_run = result.scalar_one_or_none()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if sim_run.status != "completed":
        return SimResultsResponse(
            sim_id=sim_run.id,
            status=sim_run.status,
            num_sims=sim_run.num_sims,
        )

    data = sim_run.results_data or {}
    lineup_scores = data.get("lineup_scores", [])

    # Build histogram: 20 buckets
    histogram = []
    if lineup_scores:
        arr = np.array(lineup_scores)
        counts, edges = np.histogram(arr, bins=20)
        histogram = [
            round(float(edges[i]), 1) for i in range(len(counts)) if counts[i] > 0
        ]

    return SimResultsResponse(
        sim_id=sim_run.id,
        status=sim_run.status,
        num_sims=sim_run.num_sims,
        players=data.get("players", []),
        stacks=data.get("stacks", []),
        lineup_score_avg=round(float(np.mean(lineup_scores)), 1) if lineup_scores else None,
        lineup_score_p90=round(float(np.percentile(lineup_scores, 90)), 1) if lineup_scores else None,
        lineup_scores_histogram=histogram,
    )


@router.delete("/{sim_id}", status_code=204)
async def delete_simulation(
    sim_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SimRun).where(SimRun.id == sim_id, SimRun.user_id == user.id)
    )
    sim_run = result.scalar_one_or_none()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation not found")
    await db.delete(sim_run)
    await db.commit()
