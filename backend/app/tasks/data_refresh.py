from __future__ import annotations

import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="refresh_nfl_data", bind=True, max_retries=3)
def refresh_nfl_data(self, season: int, week: int):
    """Fetch latest player data and generate projections.

    Scheduled: Tuesday 6am ET (post-game), Thursday 6pm ET (pre-TNF).
    """
    try:
        count = _run_async(_do_refresh(season, week))
        return {"season": season, "week": week, "projections": count, "status": "completed"}
    except Exception as exc:
        logger.exception("refresh_nfl_data failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _do_refresh(season: int, week: int) -> int:
    from app.database import async_session
    from app.services.projection_engine import ProjectionEngine

    async with async_session() as db:
        engine = ProjectionEngine(db)
        count = await engine.generate_projections(season, week)
    return count


@celery_app.task(name="refresh_odds_data")
def refresh_odds_data(season: int, week: int):
    """Fetch latest odds/Vegas lines for matchup analysis."""
    # Future: fetch from SportsData.io odds endpoint
    return {"season": season, "week": week, "status": "refreshed"}
