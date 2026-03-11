from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SPORTSDATA_BASE = "https://api.sportsdata.io/v3/nfl"
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class NFLDataService:
    """Async client for SportsData.io NFL API with mock fallback."""

    def __init__(self) -> None:
        self.api_key = settings.SPORTSDATA_API_KEY
        self.use_mock = not self.api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_players(self, season: int, week: int) -> List[Dict]:
        if self.use_mock:
            return self._load_mock_players(season, week)
        return await self._fetch_players_from_api(season, week)

    async def get_projections(self, season: int, week: int) -> List[Dict]:
        if self.use_mock:
            return self._load_mock_players(season, week)
        return await self._fetch_projections_from_api(season, week)

    # ------------------------------------------------------------------
    # Live API helpers
    # ------------------------------------------------------------------

    async def _api_get(self, path: str) -> Optional[List]:
        url = f"{SPORTSDATA_BASE}/{path}"
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        retries = 3
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                wait = 2 ** attempt
                logger.warning("SportsData API attempt %d failed: %s — retrying in %ds", attempt + 1, exc, wait)
                if attempt == retries - 1:
                    logger.error("SportsData API exhausted retries for %s", path)
                    return None
                import asyncio
                await asyncio.sleep(wait)
        return None

    async def _fetch_players_from_api(self, season: int, week: int) -> List[Dict]:
        raw = await self._api_get(f"scores/json/Players")
        if not raw:
            logger.warning("Falling back to mock data")
            return self._load_mock_players(season, week)
        players = []
        for p in raw:
            if p.get("Status") not in ("Active",):
                continue
            pos = p.get("FantasyPosition") or p.get("Position", "")
            if pos not in ("QB", "RB", "WR", "TE", "K", "DST"):
                continue
            players.append({
                "external_id": str(p.get("PlayerID", "")),
                "name": f"{p.get('FirstName', '')} {p.get('LastName', '')}".strip(),
                "team": p.get("Team", ""),
                "position": pos,
                "salary": None,
                "status": "active",
                "season": season,
                "week": week,
                "stats": {},
                "opponent": "",
                "home": True,
            })
        return players

    async def _fetch_projections_from_api(self, season: int, week: int) -> List[Dict]:
        raw = await self._api_get(
            f"projections/json/PlayerGameProjectionStatsByWeek/{season}/{week}"
        )
        if not raw:
            logger.warning("Falling back to mock projection data")
            return self._load_mock_players(season, week)
        results = []
        for p in raw:
            pos = p.get("FantasyPosition") or p.get("Position", "")
            if pos not in ("QB", "RB", "WR", "TE", "K", "DST"):
                continue
            results.append({
                "external_id": str(p.get("PlayerID", "")),
                "name": p.get("Name", ""),
                "team": p.get("Team", ""),
                "position": pos,
                "salary": None,
                "status": "active",
                "season": season,
                "week": week,
                "opponent": p.get("Opponent", ""),
                "home": p.get("HomeOrAway", "HOME") == "HOME",
                "stats": {
                    "pass_yds": p.get("PassingYards", 0),
                    "pass_tds": p.get("PassingTouchdowns", 0),
                    "rush_yds": p.get("RushingYards", 0),
                    "rush_tds": p.get("RushingTouchdowns", 0),
                    "rec": p.get("Receptions", 0),
                    "rec_yds": p.get("ReceivingYards", 0),
                    "rec_tds": p.get("ReceivingTouchdowns", 0),
                },
                "projected_points": p.get("FantasyPointsDraftKings", 0),
            })
        return results

    # ------------------------------------------------------------------
    # Mock data
    # ------------------------------------------------------------------

    def _load_mock_players(self, season: int, week: int) -> List[Dict]:
        path = FIXTURES_DIR / "sample_players.json"
        with open(path) as f:
            data = json.load(f)
        for p in data:
            p["season"] = season
            p["week"] = week
        return data
