"""
STACKSNIPER MLB — Exposure Management
Controls player exposure across multiple lineups.
"""
from typing import Dict, List
from sports.mlb.data.models import PlayerProjection

class ExposureManager:
    """Manage player exposure across a pool of lineups."""
    def __init__(self, max_exposure: float = 0.6):
        self.max_exposure = max_exposure
        self.exposure_overrides: Dict[int, float] = {}

    def set_player_exposure(self, player_id: int, max_pct: float):
        self.exposure_overrides[player_id] = max(0.0, min(1.0, max_pct))

    def lock_player(self, player_id: int):
        self.exposure_overrides[player_id] = 1.0

    def exclude_player(self, player_id: int):
        self.exposure_overrides[player_id] = 0.0

    def get_max_exposure(self, player_id: int) -> float:
        return self.exposure_overrides.get(player_id, self.max_exposure)

    def calculate_exposure_report(self, lineups: List[dict]) -> Dict[str, dict]:
        if not lineups:
            return {}

        player_counts = {}
        total = len(lineups)

        for lineup in lineups:
            for p in lineup.get("players", []):
                pid = p.player_id if isinstance(p, PlayerProjection) else p.get("player_id")
                name = p.name if isinstance(p, PlayerProjection) else p.get("name", "?")
                if pid not in player_counts:
                    player_counts[pid] = {"name": name, "count": 0}
                player_counts[pid]["count"] += 1

        report = {}
        for pid, info in player_counts.items():
            report[str(pid)] = {
                "name": info["name"],
                "count": info["count"],
                "exposure_pct": round(info["count"] / total * 100, 1),
            }
        return dict(sorted(report.items(), key=lambda x: x[1]["count"], reverse=True))
