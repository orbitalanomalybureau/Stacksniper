"""
STACKSNIPER MLB — MLB Stats API Client
Free MLB Stats API: https://statsapi.mlb.com
No authentication required.
"""
import requests
from datetime import datetime, date
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from sports.mlb.config.settings import MLB_API_BASE
from sports.mlb.utils.cache import get_cached, set_cached
from sports.mlb.utils.logger import get_logger

log = get_logger("MLB_API")

class MLBStatsAPI:
    """Client for MLB's free Stats API."""

    def __init__(self):
        self.base = MLB_API_BASE
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base}/{endpoint}"
        cache_key = f"{endpoint}:{str(params)}"

        cached = get_cached(cache_key, "schedule")
        if cached:
            return cached

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            set_cached(cache_key, data, "schedule")
            return data
        except Exception as e:
            log.error(f"API error {endpoint}: {e}")
            return {}

    # ── Schedule & Games ──────────────────────────────────────────────

    def get_schedule(self, game_date: Optional[date] = None, sport_id: int = 1) -> list:
        """Get MLB schedule for a given date."""
        d = game_date or date.today()
        data = self._get("schedule", {
            "sportId": sport_id,
            "date": d.strftime("%m/%d/%Y"),
            "hydrate": "team,probablePitcher,linescore,venue,weather"
        })

        games = []
        for game_date_entry in data.get("dates", []):
            for g in game_date_entry.get("games", []):
                games.append(self._parse_game(g))
        return games

    def get_schedule_range(self, start: date, end: date) -> list:
        """Get schedule for a date range."""
        data = self._get("schedule", {
            "sportId": 1,
            "startDate": start.strftime("%m/%d/%Y"),
            "endDate": end.strftime("%m/%d/%Y"),
            "hydrate": "team,probablePitcher,venue"
        })
        games = []
        for game_date_entry in data.get("dates", []):
            for g in game_date_entry.get("games", []):
                games.append(self._parse_game(g))
        return games

    def _parse_game(self, g: dict) -> dict:
        """Parse raw game data into clean dict."""
        away = g.get("teams", {}).get("away", {})
        home = g.get("teams", {}).get("home", {})
        venue = g.get("venue", {})
        weather = g.get("weather", {})

        def _get_pitcher(team_data):
            pp = team_data.get("probablePitcher", {})
            return {
                "id": pp.get("id"),
                "name": pp.get("fullName", "TBD"),
            } if pp else {"id": None, "name": "TBD"}

        return {
            "game_pk": g.get("gamePk"),
            "game_date": g.get("gameDate"),
            "status": g.get("status", {}).get("detailedState", ""),
            "away_team": {
                "id": away.get("team", {}).get("id"),
                "name": away.get("team", {}).get("name", ""),
                "abbr": away.get("team", {}).get("abbreviation", ""),
                "probable_pitcher": _get_pitcher(away),
                "score": away.get("score", 0),
            },
            "home_team": {
                "id": home.get("team", {}).get("id"),
                "name": home.get("team", {}).get("name", ""),
                "abbr": home.get("team", {}).get("abbreviation", ""),
                "probable_pitcher": _get_pitcher(home),
                "score": home.get("score", 0),
            },
            "venue": {
                "id": venue.get("id"),
                "name": venue.get("name", ""),
            },
            "weather": {
                "condition": weather.get("condition", ""),
                "temp": weather.get("temp", ""),
                "wind": weather.get("wind", ""),
            },
        }

    # ── Rosters ──────────────────────────────────────────────────────

    def get_roster(self, team_id: int, roster_type: str = "active") -> list:
        """Get team roster."""
        data = self._get(f"teams/{team_id}/roster", {"rosterType": roster_type})
        players = []
        for p in data.get("roster", []):
            person = p.get("person", {})
            pos = p.get("position", {})
            players.append({
                "id": person.get("id"),
                "name": person.get("fullName", ""),
                "jersey": p.get("jerseyNumber", ""),
                "position": pos.get("abbreviation", ""),
                "position_type": pos.get("type", ""),
                "status": p.get("status", {}).get("code", "A"),
            })
        return players

    # ── Player Stats ────────────────────────────────────────────────

    def get_player_stats(self, player_id: int, season: int = None,
                         stat_group: str = "hitting",
                         stat_type: str = "season") -> dict:
        """Get player stats for a season."""
        season = season or datetime.now().year
        data = self._get(f"people/{player_id}/stats", {
            "stats": stat_type,
            "group": stat_group,
            "season": season,
        })
        stats_list = data.get("stats", [])
        if not stats_list:
            return {}
        splits = stats_list[0].get("splits", [])
        if splits:
            return splits[0].get("stat", {})
        return {}

    def get_player_game_log(self, player_id: int, season: int = None,
                             stat_group: str = "hitting") -> list:
        """Get player game log for a season."""
        season = season or datetime.now().year
        cache_key = f"gamelog:{player_id}:{season}:{stat_group}"
        cached = get_cached(cache_key, "player_stats")
        if cached:
            return cached

        data = self._get(f"people/{player_id}/stats", {
            "stats": "gameLog",
            "group": stat_group,
            "season": season,
        })
        stats_list = data.get("stats", [])
        splits = stats_list[0].get("splits", []) if stats_list else []
        games = []
        for s in splits:
            stat = s.get("stat", {})
            stat["date"] = s.get("date", "")
            stat["opponent"] = s.get("opponent", {}).get("abbreviation", "")
            stat["isHome"] = s.get("isHome", False)
            games.append(stat)

        set_cached(cache_key, games, "player_stats")
        return games

    # ── Team Stats ──────────────────────────────────────────────────

    def get_team_stats(self, team_id: int, season: int = None,
                       stat_group: str = "hitting") -> dict:
        """Get team aggregate stats."""
        season = season or datetime.now().year
        data = self._get(f"teams/{team_id}/stats", {
            "stats": "season",
            "group": stat_group,
            "season": season,
        })
        stats_list = data.get("stats", [])
        if not stats_list:
            return {}
        splits = stats_list[0].get("splits", [])
        if splits:
            return splits[0].get("stat", {})
        return {}

    # ── Standings ───────────────────────────────────────────────────

    def get_standings(self, season: int = None) -> list:
        """Get current MLB standings."""
        season = season or datetime.now().year
        data = self._get("standings", {
            "leagueId": "103,104",
            "season": season,
            "hydrate": "team"
        })
        teams = []
        for record in data.get("records", []):
            for tr in record.get("teamRecords", []):
                teams.append({
                    "team_id": tr.get("team", {}).get("id"),
                    "team_name": tr.get("team", {}).get("name", ""),
                    "wins": tr.get("wins", 0),
                    "losses": tr.get("losses", 0),
                    "pct": tr.get("winningPercentage", ".000"),
                    "streak": tr.get("streak", {}).get("streakCode", ""),
                    "last10": f'{(tr.get("records", {}).get("splitRecords", []) or [{}])[0].get("wins", 0)}-{(tr.get("records", {}).get("splitRecords", []) or [{}])[0].get("losses", 0)}',
                    "division": record.get("division", {}).get("abbreviation", ""),
                    "run_diff": tr.get("runDifferential", 0),
                })
        return teams

    # ── Live Game Data ──────────────────────────────────────────────

    def get_live_game(self, game_pk: int) -> dict:
        """Fetch live game feed with play-by-play data."""
        try:
            resp = self.session.get(
                f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live",
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.error(f"Live game feed error for {game_pk}: {e}")
            return {}

    def get_live_boxscore(self, game_pk: int) -> dict:
        """Fetch live boxscore for a game."""
        data = self._get(f"game/{game_pk}/boxscore")
        return data

    # ── Boxscore ────────────────────────────────────────────────────

    def get_boxscore(self, game_pk: int) -> dict:
        """Get game boxscore."""
        data = self._get(f"game/{game_pk}/boxscore", {})
        return data

    # ── Batch Requests (v3 Phase 5.3) ────────────────────────────

    def fetch_games_batch(self, game_pks: List[int], max_workers: int = 6) -> Dict[int, dict]:
        """
        Fetch multiple game data (live feeds) in parallel using ThreadPoolExecutor.
        Returns dict mapping game_pk -> game data.
        """
        results = {}
        if not game_pks:
            return results

        max_workers = min(max_workers, len(game_pks))

        def _fetch_single(game_pk: int) -> tuple:
            try:
                data = self.get_live_game(game_pk)
                return (game_pk, data)
            except Exception as e:
                log.warning(f"Batch fetch failed for game {game_pk}: {e}")
                return (game_pk, {})

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch_single, pk): pk for pk in game_pks}
            for future in as_completed(futures):
                game_pk, data = future.result()
                results[game_pk] = data

        log.info(f"Batch fetched {len(results)}/{len(game_pks)} games")
        return results

    def fetch_boxscores_batch(self, game_pks: List[int], max_workers: int = 6) -> Dict[int, dict]:
        """
        Fetch multiple boxscores in parallel using ThreadPoolExecutor.
        Returns dict mapping game_pk -> boxscore data.
        """
        results = {}
        if not game_pks:
            return results

        max_workers = min(max_workers, len(game_pks))

        def _fetch_single(game_pk: int) -> tuple:
            try:
                data = self.get_boxscore(game_pk)
                return (game_pk, data)
            except Exception as e:
                log.warning(f"Batch boxscore fetch failed for game {game_pk}: {e}")
                return (game_pk, {})

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch_single, pk): pk for pk in game_pks}
            for future in as_completed(futures):
                game_pk, data = future.result()
                results[game_pk] = data

        log.info(f"Batch fetched {len(results)}/{len(game_pks)} boxscores")
        return results

# Singleton
mlb_api = MLBStatsAPI()
