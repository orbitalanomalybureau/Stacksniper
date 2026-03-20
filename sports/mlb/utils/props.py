"""
STACKSNIPER MLB — Props Analysis Engine (v6 Sprint 5.2)
Analyzes per-stat simulation distributions to generate over/under
probabilities for player prop lines.
"""
import numpy as np

HITTER_PROPS = {
    "hits": {"lines": [0.5, 1.5], "stat_key": "sim_hits"},
    "home_runs": {"lines": [0.5], "stat_key": "sim_hrs"},
    "rbi": {"lines": [0.5, 1.5], "stat_key": "sim_rbi"},
    "runs": {"lines": [0.5], "stat_key": "sim_runs"},
    "total_bases": {"lines": [1.5, 2.5], "stat_key": "sim_total_bases"},
    "stolen_bases": {"lines": [0.5], "stat_key": "sim_sb"},
}

PITCHER_PROPS = {
    "strikeouts": {"lines": [4.5, 5.5, 6.5], "stat_key": "sim_ks"},
    "earned_runs": {"lines": [2.5], "stat_key": "sim_er"},
    "outs_recorded": {"lines": [15.5, 17.5], "stat_key": "sim_outs"},
    "hits_allowed": {"lines": [5.5], "stat_key": "sim_hits_allowed"},
}


class PropAnalyzer:
    """Calculates over/under probabilities for player prop lines
    using per-stat simulation distributions."""

    def analyze_player_props(self, player_projection):
        """Calculate over/under probabilities for all prop lines."""
        results = []
        is_pitcher = player_projection.position in ("SP", "RP", "P")
        props = PITCHER_PROPS if is_pitcher else HITTER_PROPS

        for prop_name, config in props.items():
            stat_array = getattr(player_projection, config["stat_key"], None)
            if stat_array is None or len(stat_array) == 0:
                continue
            arr = np.array(stat_array)
            for line in config["lines"]:
                over_pct = float(np.mean(arr > line))
                under_pct = 1.0 - over_pct
                # Edge classification
                edge = abs(over_pct - 0.5)
                confidence = "high" if edge > 0.15 else "medium" if edge > 0.05 else "low"
                results.append({
                    "prop": prop_name,
                    "line": line,
                    "over_pct": round(over_pct * 100, 1),
                    "under_pct": round(under_pct * 100, 1),
                    "edge": round(edge * 100, 1),
                    "confidence": confidence,
                    "mean": round(float(np.mean(arr)), 2),
                    "median": round(float(np.median(arr)), 2),
                })
        return results

    def analyze_slate_props(self, sim_result):
        """Analyze props for all players in a simulation result."""
        all_props = []
        for player in sim_result.player_projections:
            player_props = self.analyze_player_props(player)
            if player_props:
                all_props.append({
                    "player_name": player.name,
                    "player_id": player.player_id,
                    "team": player.team,
                    "position": player.position,
                    "props": player_props,
                })
        return all_props


prop_analyzer = PropAnalyzer()
