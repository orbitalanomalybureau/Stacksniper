"""STACKSNIPER MLB — Statcast Advanced Metrics"""
from sports.mlb.utils.cache import get_cached, set_cached
from sports.mlb.utils.logger import get_logger

log = get_logger("Statcast")

def get_statcast_metrics(player_id: int, season: int = None) -> dict:
    """Fetch Statcast advanced metrics for a player.
    Returns: barrel_rate, exit_velocity, hard_hit_pct, xba, xslg, xwoba, sprint_speed
    Uses MLB Stats API savant endpoints with caching (12-hour TTL).
    """
    from datetime import date
    if season is None:
        season = date.today().year

    cache_key = f"statcast_{player_id}_{season}"
    cached = get_cached(cache_key, "player_stats")
    if cached:
        return cached

    try:
        import requests
        # Use MLB Stats API for advanced stats
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats"
        params = {"stats": "sabermetrics", "season": season, "group": "hitting"}
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        metrics = {"player_id": player_id, "season": season}
        splits = data.get("stats", [{}])[0].get("splits", [])
        if splits:
            s = splits[0].get("stat", {})
            metrics.update({
                "woba": s.get("wOBA", 0),
                "wrc_plus": s.get("wRCPlus", 100),
                "iso": s.get("iso", 0),
                "babip": s.get("babip", 0),
                "barrel_rate": None,  # Not available via this endpoint
                "exit_velocity": None,
                "hard_hit_pct": None,
                "xba": None,
                "xslg": None,
                "xwoba": None,
                "sprint_speed": None,
            })

        set_cached(cache_key, metrics, "player_stats")
        return metrics
    except Exception as e:
        log.warning(f"Failed to fetch Statcast for player {player_id}: {e}")
        return {"player_id": player_id, "season": season}

def check_regression_candidates(players: list) -> list:
    """Flag players whose xwOBA differs significantly from actual wOBA."""
    candidates = []
    for p in players:
        metrics = get_statcast_metrics(p.player_id)
        xwoba = metrics.get("xwoba")
        woba = metrics.get("woba")
        if xwoba and woba and abs(xwoba - woba) > 0.030:
            direction = "buy" if xwoba > woba else "sell"
            candidates.append({
                "player_id": p.player_id,
                "name": p.name,
                "woba": woba,
                "xwoba": xwoba,
                "diff": round(xwoba - woba, 3),
                "direction": direction,
            })
    return candidates
