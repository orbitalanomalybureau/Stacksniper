"""
STACKSNIPER MLB — Historical Data Loader
Uses pybaseball for deep historical data and the MLB API for recent games.
"""
from datetime import date, timedelta
from pathlib import Path
from sports.mlb.utils.logger import get_logger
from sports.mlb.data.mlb_api import mlb_api

log = get_logger("HISTORICAL")

class HistoricalLoader:
    """Load and manage historical MLB data."""

    def __init__(self):
        self.data_dir = Path("data/historical")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_player_recent_games(self, player_id: int, num_games: int = 20,
                                 stat_group: str = "hitting") -> list:
        """Get a player's most recent game logs."""
        current_year = date.today().year
        games = mlb_api.get_player_game_log(player_id, current_year, stat_group)

        if len(games) < num_games:
            prev_games = mlb_api.get_player_game_log(
                player_id, current_year - 1, stat_group
            )
            games = prev_games + games

        return games[-num_games:]

    def get_pitcher_vs_team(self, pitcher_id: int, team_id: int,
                             season: int = None) -> dict:
        """Get pitcher's stats vs a specific team."""
        season = season or date.today().year
        data = mlb_api._get(f"people/{pitcher_id}/stats", {
            "stats": "vsTeam",
            "group": "pitching",
            "season": season,
            "opposingTeamId": team_id,
        })
        stats_list = data.get("stats", [])
        splits = stats_list[0].get("splits", []) if stats_list else []
        if splits:
            return splits[0].get("stat", {})
        return {}

    def get_batter_vs_pitcher(self, batter_id: int, pitcher_id: int) -> dict:
        """Get batter's career stats vs a specific pitcher."""
        data = mlb_api._get(f"people/{batter_id}/stats", {
            "stats": "vsPlayer",
            "group": "hitting",
            "opposingPlayerId": pitcher_id,
        })
        stats_list = data.get("stats", [])
        splits = stats_list[0].get("splits", []) if stats_list else []
        if splits:
            return splits[0].get("stat", {})
        return {}

    def get_team_recent_results(self, team_id: int, num_games: int = 10) -> list:
        """Get a team's recent game results."""
        today = date.today()
        start = today - timedelta(days=30)
        games = mlb_api.get_schedule_range(start, today)
        team_games = [
            g for g in games
            if g["home_team"]["id"] == team_id or g["away_team"]["id"] == team_id
        ]
        return team_games[-num_games:]

    def get_batter_splits(self, player_id: int, season: int = None) -> dict:
        """Get batter splits (vs LHP/RHP, home/away)."""
        season = season or date.today().year
        result = {}

        for split_type in ["vsLeftRight", "homeAway"]:
            data = mlb_api._get(f"people/{player_id}/stats", {
                "stats": split_type,
                "group": "hitting",
                "season": season,
            })
            stats_list = data.get("stats", [])
            splits = stats_list[0].get("splits", []) if stats_list else []
            for s in splits:
                key = s.get("split", {}).get("description", "unknown")
                result[key] = s.get("stat", {})

        return result

historical_loader = HistoricalLoader()
