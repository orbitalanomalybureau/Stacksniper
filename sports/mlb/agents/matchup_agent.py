"""
STACKSNIPER MLB — Matchup Analysis Agent
Evaluates pitcher-batter matchup quality.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion
from sports.mlb.data.historical_loader import historical_loader

class MatchupAgent(BaseAgent):
    """Analyzes specific pitcher vs batter historical matchups."""
    def __init__(self):
        super().__init__("MatchupAnalyst", "matchup", weight=1.2)

    def analyze(self, context: dict) -> AgentOpinion:
        batter_id = context.get("batter_id")
        pitcher_id = context.get("opp_pitcher_id")

        if not batter_id or not pitcher_id:
            return self._neutral_opinion()

        bvp = historical_loader.get_batter_vs_pitcher(batter_id, pitcher_id)
        abs_count = int(bvp.get("atBats", 0))

        if abs_count < 5:
            return AgentOpinion(
                agent_name=self.name,
                agent_type=self.agent_type,
                confidence=0.2,
                weight=self.weight * 0.3,
                projection={"matchup_factor": 1.0, "sample_size": abs_count},
                reasoning=f"Insufficient BvP data ({abs_count} ABs)",
                adjustments={"hits_multiplier": 1.0},
            )

        avg = float(bvp.get("avg", ".250"))
        slg = float(bvp.get("slg", ".400"))
        k_rate = float(bvp.get("strikeOuts", 0)) / max(1, abs_count)
        hr_rate = float(bvp.get("homeRuns", 0)) / max(1, abs_count)

        league_avg = 0.250
        matchup_factor = 0.7 + 0.3 * (avg / league_avg) if league_avg > 0 else 1.0
        matchup_factor = max(0.5, min(1.6, matchup_factor))

        confidence = self.adjust_confidence(0.8, abs_count)

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=confidence,
            weight=self.weight,
            projection={
                "matchup_factor": round(matchup_factor, 3),
                "bvp_avg": avg,
                "bvp_slg": slg,
                "bvp_k_rate": round(k_rate, 3),
                "bvp_hr_rate": round(hr_rate, 3),
                "sample_size": abs_count,
            },
            reasoning=f"BvP: {avg} AVG / {slg} SLG in {abs_count} ABs",
            adjustments={
                "hits_multiplier": matchup_factor,
                "hr_multiplier": max(0.5, min(2.0, 0.7 + 0.3 * (slg / 0.400))),
            },
        )

    def _neutral_opinion(self) -> AgentOpinion:
        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.1,
            weight=0.1,
            projection={"matchup_factor": 1.0},
            reasoning="No matchup data available",
            adjustments={"hits_multiplier": 1.0},
        )
