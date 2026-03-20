"""STACKSNIPER MLB — Confirmed Lineup Detection"""
from sports.mlb.data.mlb_api import mlb_api
from sports.mlb.utils.cache import get_cached, set_cached
from sports.mlb.utils.logger import get_logger

log = get_logger("Lineups")

def get_confirmed_lineups(game_pk: int) -> dict:
    """Fetch confirmed batting order from boxscore if available."""
    cache_key = f"lineup_{game_pk}"
    cached = get_cached(cache_key, "lineups")
    if cached:
        return cached

    try:
        boxscore = mlb_api.get_boxscore(game_pk)
        result = {"game_pk": game_pk, "away": [], "home": []}

        for side in ["away", "home"]:
            team_data = boxscore.get("teams", {}).get(side, {})
            batting_order = team_data.get("battingOrder", [])
            players = team_data.get("players", {})

            lineup = []
            for i, pid in enumerate(batting_order):
                pdata = players.get(f"ID{pid}", {})
                person = pdata.get("person", {})
                lineup.append({
                    "player_id": pid,
                    "name": person.get("fullName", ""),
                    "position": pdata.get("position", {}).get("abbreviation", ""),
                    "batting_order": i + 1,
                    "is_confirmed": True,
                })
            result[side] = lineup

        if result["away"] or result["home"]:
            set_cached(cache_key, result, "lineups")
        return result
    except Exception as e:
        log.warning(f"Failed to fetch lineup for game {game_pk}: {e}")
        return {"game_pk": game_pk, "away": [], "home": [], "is_confirmed": False}

def get_all_confirmed_lineups(game_pks: list) -> dict:
    """Fetch confirmed lineups for all games."""
    results = {}
    for gpk in game_pks:
        results[gpk] = get_confirmed_lineups(gpk)
    return results
