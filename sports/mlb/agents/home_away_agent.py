"""
STACKSNIPER MLB — Home/Away Splits Agent
Adjusts projections based on whether the batter is playing at home or away.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion
from sports.mlb.data.historical_loader import historical_loader


class HomeAwayAgent(BaseAgent):
    """Adjusts projections based on batter home/away splits."""

    def __init__(self):
        super().__init__("HomeAwayAnalyst", "home_away", weight=0.7)

    def analyze(self, context: dict) -> AgentOpinion:
        batter_id = context.get("batter_id")
        season = context.get("season")
        is_home = context.get("is_home", True)

        if not batter_id:
            return self._neutral_opinion()

        splits = historical_loader.get_batter_splits(batter_id, season) if batter_id else {}

        split_key = "Home" if is_home else "Away"
        split_data = splits.get(split_key, {})

        if not split_data:
            return self._neutral_opinion()

        # Compare split performance to season averages
        split_avg = float(split_data.get("avg", 0))
        split_slg = float(split_data.get("slg", 0))
        season_avg = float(splits.get("season_avg", split_avg) if splits.get("season_avg") else split_avg)
        season_slg = float(splits.get("season_slg", split_slg) if splits.get("season_slg") else split_slg)

        # Fall back to context-level season stats if splits don't carry season totals
        if season_avg == 0:
            season_avg = float(context.get("batter_season_avg", 0.250))
        if season_slg == 0:
            season_slg = float(context.get("batter_season_slg", 0.400))

        # Compute multipliers from split vs season
        if season_avg > 0:
            avg_ratio = split_avg / season_avg
        else:
            avg_ratio = 1.0

        if season_slg > 0:
            slg_ratio = split_slg / season_slg
        else:
            slg_ratio = 1.0

        # Blend avg and slg ratios (60/40 weighting toward avg for contact, slg for power)
        hits_multiplier = 0.6 * avg_ratio + 0.4 * slg_ratio
        hr_multiplier = 0.3 * avg_ratio + 0.7 * slg_ratio  # Power weighted toward slg

        # Clamp to reasonable range
        hits_multiplier = max(0.85, min(1.15, hits_multiplier))
        hr_multiplier = max(0.85, min(1.15, hr_multiplier))

        sample_size = int(split_data.get("atBats", 0))
        confidence = self.adjust_confidence(0.7, sample_size)

        venue_label = "Home" if is_home else "Away"
        reasoning = (
            f"{venue_label} split: {split_avg:.3f} AVG / {split_slg:.3f} SLG "
            f"vs season {season_avg:.3f}/{season_slg:.3f} "
            f"-> hits x{hits_multiplier:.3f}, HR x{hr_multiplier:.3f}"
        )

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=confidence,
            weight=self.weight,
            projection={
                "split": venue_label,
                "split_avg": split_avg,
                "split_slg": split_slg,
                "season_avg": season_avg,
                "season_slg": season_slg,
            },
            reasoning=reasoning,
            adjustments={
                "hits_multiplier": round(hits_multiplier, 3),
                "hr_multiplier": round(hr_multiplier, 3),
            },
        )

    def _neutral_opinion(self) -> AgentOpinion:
        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.1,
            weight=0.1,
            projection={"split": "unknown"},
            reasoning="No home/away split data available",
            adjustments={"hits_multiplier": 1.0, "hr_multiplier": 1.0},
        )
