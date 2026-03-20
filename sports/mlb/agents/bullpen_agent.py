"""
STACKSNIPER MLB — Bullpen Analysis Agent
Evaluates bullpen quality and usage for late-game projections.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion
from sports.mlb.data.mlb_api import mlb_api

class BullpenAgent(BaseAgent):
    """Analyzes bullpen strength and fatigue."""
    def __init__(self):
        super().__init__("BullpenAnalyst", "bullpen", weight=0.8)

    def analyze(self, context: dict) -> AgentOpinion:
        team_id = context.get("team_id")
        season = context.get("season")

        if not team_id:
            return self._default()

        # v6 Opt 5: Use pre-fetched team data from engine context if available
        team_pitching = (context.get("_team_data", {}).get("team_stats_pitching")
                         or mlb_api.get_team_stats(team_id, season, "pitching"))
        if not team_pitching:
            return self._default()

        era = float(team_pitching.get("era", 4.50))
        whip = float(team_pitching.get("whip", 1.30))
        k_per_9 = float(team_pitching.get("strikeoutsPer9Inn", 8.0))

        quality = 1.0
        if era < 3.50:
            quality = 0.88
        elif era < 4.00:
            quality = 0.94
        elif era > 5.00:
            quality = 1.10
        elif era > 4.50:
            quality = 1.05

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.65,
            weight=self.weight,
            projection={
                "bullpen_quality": quality,
                "team_era": era,
                "team_whip": whip,
                "team_k9": k_per_9,
            },
            reasoning=f"Team ERA: {era}, WHIP: {whip}, K/9: {k_per_9}",
            adjustments={"runs_multiplier": quality},
        )

    def _default(self) -> AgentOpinion:
        return AgentOpinion(
            agent_name=self.name, agent_type=self.agent_type,
            confidence=0.3, weight=0.3,
            projection={"bullpen_quality": 1.0},
            reasoning="Default bullpen assessment",
            adjustments={},
        )
