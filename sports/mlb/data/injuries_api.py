"""
STACKSNIPER MLB — Injuries Data
"""
import requests
from sports.mlb.utils.cache import get_cached, set_cached
from sports.mlb.utils.logger import get_logger

log = get_logger("Injuries")

MLB_INJURIES_URL = "https://statsapi.mlb.com/api/v1/injuries"


def get_injuries() -> list:
    """Fetch current MLB injuries from the API."""
    cache_key = "mlb_injuries_current"
    cached = get_cached(cache_key, "schedule")
    if cached:
        return cached

    try:
        resp = requests.get(MLB_INJURIES_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        injuries = []
        for inj in data.get("injuries", data.get("row", [])):
            # Handle different response formats
            if isinstance(inj, dict):
                injuries.append({
                    "player": inj.get("playerName", inj.get("player", {}).get("fullName", "")),
                    "player_id": inj.get("playerId", inj.get("player", {}).get("id")),
                    "team": inj.get("teamName", inj.get("team", {}).get("name", "")),
                    "team_id": inj.get("teamId", inj.get("team", {}).get("id")),
                    "status": inj.get("status", ""),
                    "date": inj.get("date", ""),
                    "description": inj.get("description", inj.get("notes", "")),
                })

        set_cached(cache_key, injuries, "schedule")
        return injuries
    except Exception as e:
        log.warning(f"Failed to fetch injuries: {e}")
        return []
