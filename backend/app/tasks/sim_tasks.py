from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="run_simulation", max_retries=2)
def run_simulation_task(self, sim_run_id: str, season: int, week: int, num_sims: int):
    """Execute Monte Carlo simulation as background Celery task."""
    self.update_state(state="RUNNING", meta={"progress": 0})
    try:
        result = _run_async(_do_simulation(sim_run_id, season, week, num_sims))
        return result
    except Exception as exc:
        logger.exception("Simulation task failed: %s", sim_run_id)
        _run_async(_mark_failed(sim_run_id))
        raise self.retry(exc=exc, countdown=30)


async def _do_simulation(sim_run_id: str, season: int, week: int, num_sims: int) -> dict:
    """Run the simulation pipeline."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.simulation import SimRun
    from app.services.simulator import Simulator

    async with async_session() as db:
        result = await db.execute(select(SimRun).where(SimRun.id == sim_run_id))
        sim_run = result.scalar_one_or_none()
        if not sim_run:
            return {"error": "sim_run not found"}

        sim_run.status = "running"
        await db.commit()

        sim = Simulator(db)
        config = sim_run.config or {}
        sim_data = await sim.run_simulation(season, week, num_sims, config)

        sim_run.results_data = sim_data
        sim_run.status = "completed"
        sim_run.completed_at = datetime.now(timezone.utc)
        await db.commit()

    return {"sim_run_id": sim_run_id, "status": "completed"}


async def _mark_failed(sim_run_id: str):
    from sqlalchemy import select
    from app.database import async_session
    from app.models.simulation import SimRun

    async with async_session() as db:
        result = await db.execute(select(SimRun).where(SimRun.id == sim_run_id))
        sim_run = result.scalar_one_or_none()
        if sim_run:
            sim_run.status = "failed"
            await db.commit()


async def run_simulation_inline(sim_run_id: str, db):
    """Run simulation synchronously (no Celery) for dev/preview."""
    from sqlalchemy import select
    from app.models.simulation import SimRun
    from app.services.simulator import Simulator

    result = await db.execute(select(SimRun).where(SimRun.id == sim_run_id))
    sim_run = result.scalar_one_or_none()
    if not sim_run:
        return

    sim_run.status = "running"
    await db.commit()

    try:
        sim = Simulator(db)
        config = sim_run.config or {}
        sim_data = await sim.run_simulation(
            sim_run.season, sim_run.week, sim_run.num_sims, config
        )

        sim_run.results_data = sim_data
        sim_run.status = "completed"
        sim_run.completed_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception:
        logger.exception("Inline simulation failed: %s", sim_run_id)
        sim_run.status = "failed"
        await db.commit()
