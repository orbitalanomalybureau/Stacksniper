"""
STACKSNIPER MLB v3.0 — Phase 3.6: Multi-Slate Support
Filters players and games by slate type (main, early, night, turbo).
Games from the MLB API arrive with UTC timestamps in the 'game_date' field.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from sports.mlb.data.models import PlayerProjection
from sports.mlb.utils.logger import get_logger

log = get_logger("SlateManager")

# Eastern Time offset (UTC-5 standard, UTC-4 daylight)
_ET_STANDARD = timezone(timedelta(hours=-5))
_ET_DAYLIGHT = timezone(timedelta(hours=-4))


def _to_eastern(utc_str: str) -> datetime:
    """Convert a UTC ISO-8601 timestamp (from MLB API) to Eastern Time.

    Handles formats like '2026-03-17T17:05:00Z' and '2026-03-17T17:05:00+00:00'.
    Uses a naive DST heuristic: Mar-Nov -> EDT (UTC-4), else EST (UTC-5).
    """
    if not utc_str:
        return datetime.now(tz=_ET_STANDARD)

    # Normalise the string so fromisoformat can handle it
    cleaned = utc_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        # Fallback: try common MLB API format
        try:
            dt = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            log.warning(f"Unparseable game_date: {utc_str}, using current time")
            return datetime.now(tz=_ET_STANDARD)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Simple DST heuristic (March through November)
    et_offset = _ET_DAYLIGHT if 3 <= dt.month <= 11 else _ET_STANDARD
    return dt.astimezone(et_offset)


# ── Slate Definitions ────────────────────────────────────────────────

SLATE_DEFS = {
    "main": {
        "label": "Main Slate",
        "description": "All games on the schedule",
    },
    "early": {
        "label": "Early Slate",
        "description": "Games starting before 4:00 PM ET",
        "before_hour": 16,  # exclusive upper bound
    },
    "night": {
        "label": "Night Slate",
        "description": "Games starting at or after 6:00 PM ET",
        "from_hour": 18,  # inclusive lower bound
    },
    "turbo": {
        "label": "Turbo Slate",
        "description": "2-3 game mini-slates (earliest cluster)",
        "max_games": 3,
    },
}


class SlateManager:
    """Filter players and games by DFS slate type."""

    def __init__(self):
        self.slate_defs = SLATE_DEFS

    # ── Public API ────────────────────────────────────────────────────

    def filter_by_slate(
        self,
        players: List[PlayerProjection],
        slate_type: str,
        game_times: Dict[int, str],
    ) -> List[PlayerProjection]:
        """Return only players whose game_pk belongs to the given slate.

        Args:
            players:    Full list of PlayerProjection objects.
            slate_type: One of 'main', 'early', 'night', 'turbo'.
            game_times: Mapping of game_pk -> UTC ISO-8601 datetime string.

        Returns:
            Filtered list of PlayerProjection objects.
        """
        if slate_type not in self.slate_defs:
            log.warning(f"Unknown slate type '{slate_type}', returning all players")
            return players

        if slate_type == "main":
            return players

        valid_pks = self._game_pks_for_slate(slate_type, game_times)
        filtered = [p for p in players if p.game_pk in valid_pks]
        log.info(
            f"Slate '{slate_type}': {len(valid_pks)} games, "
            f"{len(filtered)}/{len(players)} players"
        )
        return filtered

    def get_available_slates(self, games: List[dict]) -> List[dict]:
        """Determine which slates are viable for the given schedule.

        Args:
            games: List of game dicts as returned by mlb_api.get_schedule().
                   Each dict must contain 'game_pk' and 'game_date' keys.

        Returns:
            List of slate info dicts with keys:
                name, label, description, game_pks, player_count (always 0
                here -- caller can enrich), game_count.
        """
        game_times: Dict[int, str] = {}
        for g in games:
            pk = g.get("game_pk")
            gd = g.get("game_date", "")
            if pk is not None:
                game_times[pk] = gd

        available: List[dict] = []
        for slate_type, sdef in self.slate_defs.items():
            pks = self._game_pks_for_slate(slate_type, game_times)
            if not pks:
                continue
            available.append({
                "name": slate_type,
                "label": sdef["label"],
                "description": sdef["description"],
                "game_pks": sorted(pks),
                "game_count": len(pks),
                "player_count": 0,  # enriched downstream
            })

        log.info(f"Available slates: {[s['name'] for s in available]}")
        return available

    # ── Internals ─────────────────────────────────────────────────────

    def _game_pks_for_slate(
        self, slate_type: str, game_times: Dict[int, str]
    ) -> set:
        """Return the set of game_pk values that belong to *slate_type*."""
        if slate_type == "main":
            return set(game_times.keys())

        sdef = self.slate_defs[slate_type]

        # Convert all game times to Eastern
        et_times: Dict[int, datetime] = {}
        for pk, utc_str in game_times.items():
            et_times[pk] = _to_eastern(utc_str)

        if slate_type == "early":
            cutoff = sdef["before_hour"]
            return {pk for pk, dt in et_times.items() if dt.hour < cutoff}

        if slate_type == "night":
            start_hour = sdef["from_hour"]
            return {pk for pk, dt in et_times.items() if dt.hour >= start_hour}

        if slate_type == "turbo":
            max_games = sdef["max_games"]
            if len(et_times) <= max_games:
                # Everything fits in a turbo
                return set(et_times.keys())
            # Pick the earliest cluster of max_games games
            sorted_pks = sorted(et_times, key=lambda pk: et_times[pk])
            return set(sorted_pks[:max_games])

        return set()
