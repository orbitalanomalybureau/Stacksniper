"""
STACKSNIPER MLB — Live Scoring Tracker
Tracks live DraftKings fantasy points during active games.
"""
import time
from typing import Dict, List
from sports.mlb.config.dk_scoring import calculate_hitter_dkfp, calculate_pitcher_dkfp
from sports.mlb.data.mlb_api import mlb_api
from sports.mlb.utils.logger import get_logger

log = get_logger("LiveTracker")


class LiveTracker:
    """Tracks live DK fantasy points for active game slates."""

    def __init__(self):
        self.active_games: Dict[int, dict] = {}  # game_pk -> game info
        self.player_scores: Dict[int, dict] = {}  # player_id -> score info
        self.last_update: float = 0

    def set_active_games(self, game_pks: List[int]):
        """Set which games to track."""
        self.active_games = {pk: {} for pk in game_pks}
        log.info(f"Tracking {len(game_pks)} games")

    def update(self) -> dict:
        """Fetch live data and update all player scores."""
        updated_players = {}

        for game_pk in list(self.active_games.keys()):
            try:
                boxscore = mlb_api.get_live_boxscore(game_pk)
                if not boxscore:
                    continue

                game_data = self._parse_boxscore(game_pk, boxscore)
                self.active_games[game_pk] = game_data

                for player_id, score_info in game_data.get("players", {}).items():
                    self.player_scores[player_id] = score_info
                    updated_players[player_id] = score_info

            except Exception as e:
                log.error(f"Live update error for game {game_pk}: {e}")

        self.last_update = time.time()
        return updated_players

    def _parse_boxscore(self, game_pk: int, boxscore: dict) -> dict:
        """Parse boxscore data into player DK scores."""
        result = {"game_pk": game_pk, "players": {}}

        teams = boxscore.get("teams", {})

        # Check game status
        game_status = "live"

        for side in ["away", "home"]:
            team_data = teams.get(side, {})
            team_name = team_data.get("team", {}).get("abbreviation", "")
            players_data = team_data.get("players", {})

            for player_key, player_info in players_data.items():
                try:
                    player_id = player_info.get("person", {}).get("id", 0)
                    player_name = player_info.get("person", {}).get("fullName", "Unknown")
                    position = player_info.get("position", {}).get("abbreviation", "")

                    stats = player_info.get("stats", {})

                    if position in ("P", "SP", "RP"):
                        pitching = stats.get("pitching", {})
                        if not pitching:
                            continue
                        dk_pts = self._calc_pitcher_live(pitching)
                    else:
                        batting = stats.get("batting", {})
                        if not batting:
                            continue
                        dk_pts = self._calc_hitter_live(batting)

                    self.player_scores[player_id] = {
                        "player_id": player_id,
                        "name": player_name,
                        "team": team_name,
                        "position": position,
                        "current_dkfp": round(dk_pts, 2),
                        "game_pk": game_pk,
                        "game_status": game_status,
                        "game_final": game_status == "Final",
                        "side": side,
                    }
                    result["players"][player_id] = self.player_scores[player_id]

                except Exception as e:
                    log.debug(f"Parse error for player in game {game_pk}: {e}")

        return result

    def _calc_hitter_live(self, batting: dict) -> float:
        """Calculate hitter DK points from live batting stats."""
        hits = int(batting.get("hits", 0))
        doubles = int(batting.get("doubles", 0))
        triples = int(batting.get("triples", 0))
        hr = int(batting.get("homeRuns", 0))
        singles = hits - doubles - triples - hr

        stats = {
            "singles": max(0, singles),
            "doubles": doubles,
            "triples": triples,
            "home_runs": hr,
            "rbi": int(batting.get("rbi", 0)),
            "runs": int(batting.get("runs", 0)),
            "walks": int(batting.get("baseOnBalls", 0)),
            "hbp": int(batting.get("hitByPitch", 0)),
            "stolen_bases": int(batting.get("stolenBases", 0)),
            "caught_stealing": int(batting.get("caughtStealing", 0)),
        }
        return calculate_hitter_dkfp(stats)

    def _calc_pitcher_live(self, pitching: dict) -> float:
        """Calculate pitcher DK points from live pitching stats."""
        stats = {
            "win": 1 if pitching.get("wins", 0) > 0 else 0,
            "earned_runs": int(pitching.get("earnedRuns", 0)),
            "strikeouts": int(pitching.get("strikeOuts", 0)),
            "innings_pitched": float(pitching.get("inningsPitched", "0") or 0),
            "hits_against": int(pitching.get("hits", 0)),
            "walks_against": int(pitching.get("baseOnBalls", 0)),
            "hbp_against": int(pitching.get("hitBatsmen", 0)),
            "complete_game": bool(pitching.get("completeGames", 0)),
            "shutout": bool(pitching.get("shutouts", 0)),
            "no_hitter": False,  # Not easily determined from boxscore
        }
        return calculate_pitcher_dkfp(stats)

    def get_lineup_score(self, lineup_players: list) -> dict:
        """Get current and projected score for a lineup."""
        current = 0
        projected = 0

        for p in lineup_players:
            pid = p.player_id if hasattr(p, "player_id") else p.get("id", 0)
            live = self.player_scores.get(pid, {})

            if live:
                current += live.get("current_dkfp", 0)
                if live.get("game_final", False):
                    projected += live.get("current_dkfp", 0)
                else:
                    # Use higher of current or original projection for in-progress
                    projected += max(
                        live.get("current_dkfp", 0),
                        getattr(p, "dk_points", 0) if hasattr(p, "dk_points") else p.get("dk_points", 0),
                    )
            else:
                projected += getattr(p, "dk_points", 0) if hasattr(p, "dk_points") else p.get("dk_points", 0)

        return {
            "current": round(current, 2),
            "projected": round(projected, 2),
        }

    def get_all_scores(self) -> dict:
        """Get all tracked player scores."""
        return {
            "players": self.player_scores,
            "games": {
                pk: {
                    "game_pk": pk,
                    "status": info.get("game_status", "unknown"),
                }
                for pk, info in self.active_games.items()
            },
            "last_update": self.last_update,
        }


# Module singleton
live_tracker = LiveTracker()
