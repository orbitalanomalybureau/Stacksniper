from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.models.projection import Projection
from app.services.nfl_data import NFLDataService

logger = logging.getLogger(__name__)

# Half-PPR DraftKings scoring weights
SCORING = {
    "pass_yds": 0.04,
    "pass_tds": 4.0,
    "rush_yds": 0.1,
    "rush_tds": 6.0,
    "rec": 0.5,
    "rec_yds": 0.1,
    "rec_tds": 6.0,
}

# Position-level baseline ranges for K and DST
K_BASE = {"projected_points": 8.0, "floor": 3.0, "ceiling": 14.0}
DST_BASE = {"projected_points": 7.0, "floor": 2.0, "ceiling": 16.0}

HOME_BOOST = 1.05


class ProjectionEngine:
    """Heuristic projection engine for MVP.

    Uses stat averages (from SportsData.io or mock data) and applies
    matchup / home-away multipliers with noise for floor/ceiling.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.nfl = NFLDataService()

    async def generate_projections(self, season: int, week: int) -> int:
        """Generate projections for a given week. Returns count created."""
        raw_players = await self.nfl.get_players(season, week)

        # Upsert players into DB
        await self._upsert_players(raw_players, season, week)

        # Clear old projections for this week
        await self.db.execute(
            delete(Projection).where(
                Projection.season == season,
                Projection.week == week,
            )
        )

        # Build projections
        count = 0
        for pdata in raw_players:
            player = await self._get_player_by_external_id(pdata["external_id"])
            if not player:
                continue
            proj = self._heuristic_projection(pdata, player.id, season, week)
            if proj:
                self.db.add(proj)
                count += 1

        await self.db.commit()
        logger.info("Generated %d projections for %d week %d", count, season, week)
        return count

    # ------------------------------------------------------------------
    # Heuristic model
    # ------------------------------------------------------------------

    def _heuristic_projection(
        self, pdata: Dict, player_id: str, season: int, week: int
    ) -> Optional[Projection]:
        pos = pdata.get("position", "")
        stats = pdata.get("stats", {})
        is_home = pdata.get("home", True)

        if pos == "K":
            return self._baseline_projection(player_id, season, week, K_BASE)
        if pos == "DST":
            return self._baseline_projection(player_id, season, week, DST_BASE)

        # Skill positions: base from stat averages * scoring weights
        base_pts = sum(stats.get(k, 0) * v for k, v in SCORING.items())
        if base_pts <= 0:
            base_pts = 5.0

        if is_home:
            base_pts *= HOME_BOOST

        base_pts *= random.uniform(0.95, 1.05)

        floor_pct = random.uniform(0.20, 0.30)
        ceil_pct = random.uniform(0.20, 0.35)
        floor = round(base_pts * (1 - floor_pct), 1)
        ceiling = round(base_pts * (1 + ceil_pct), 1)
        projected = round(base_pts, 1)
        std_dev = round((ceiling - floor) / 4, 2)

        salary = pdata.get("salary") or 5000
        ownership = round(min(35, max(1, (salary / 9000) * 25 + random.uniform(-3, 3))), 1)

        return Projection(
            player_id=player_id,
            season=season,
            week=week,
            source="heuristic",
            projected_points=projected,
            floor=floor,
            ceiling=ceiling,
            std_dev=std_dev,
            pass_yds=stats.get("pass_yds"),
            pass_tds=stats.get("pass_tds"),
            rush_yds=stats.get("rush_yds"),
            rush_tds=stats.get("rush_tds"),
            rec=stats.get("rec"),
            rec_yds=stats.get("rec_yds"),
            rec_tds=stats.get("rec_tds"),
        )

    def _baseline_projection(
        self, player_id: str, season: int, week: int, base: Dict
    ) -> Projection:
        pts = base["projected_points"] * random.uniform(0.90, 1.10)
        return Projection(
            player_id=player_id,
            season=season,
            week=week,
            source="heuristic",
            projected_points=round(pts, 1),
            floor=round(base["floor"] * random.uniform(0.8, 1.2), 1),
            ceiling=round(base["ceiling"] * random.uniform(0.9, 1.1), 1),
            std_dev=round((base["ceiling"] - base["floor"]) / 4, 2),
        )

    # ------------------------------------------------------------------
    # Static helpers (kept for simulation engine)
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_distribution(mean: float, std_dev: float, n_samples: int = 10000) -> dict:
        samples = np.random.normal(mean, std_dev, n_samples)
        samples = np.maximum(samples, 0)
        return {
            "mean": float(np.mean(samples)),
            "median": float(np.median(samples)),
            "std_dev": float(np.std(samples)),
            "floor": float(np.percentile(samples, 10)),
            "ceiling": float(np.percentile(samples, 90)),
            "p25": float(np.percentile(samples, 25)),
            "p75": float(np.percentile(samples, 75)),
        }

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _upsert_players(
        self, raw_players: List[Dict], season: int, week: int
    ) -> None:
        for pdata in raw_players:
            ext_id = pdata["external_id"]
            result = await self.db.execute(
                select(Player).where(Player.external_id == ext_id)
            )
            player = result.scalar_one_or_none()
            if player:
                player.name = pdata["name"]
                player.team = pdata["team"]
                player.position = pdata["position"]
                player.salary = pdata.get("salary")
                player.status = pdata.get("status", "active")
                player.season = season
                player.week = week
            else:
                player = Player(
                    external_id=ext_id,
                    name=pdata["name"],
                    team=pdata["team"],
                    position=pdata["position"],
                    salary=pdata.get("salary"),
                    status=pdata.get("status", "active"),
                    season=season,
                    week=week,
                )
                self.db.add(player)
        await self.db.flush()

    async def _get_player_by_external_id(self, ext_id: str) -> Optional[Player]:
        result = await self.db.execute(
            select(Player).where(Player.external_id == ext_id)
        )
        return result.scalar_one_or_none()
