"""
STACKSNIPER MLB — Implied Runs Calibration Agent
Scales individual projections to match team implied run total from Vegas lines.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion


class ImpliedRunsAgent(BaseAgent):
    """Scales individual projections to match team implied run total."""

    def __init__(self):
        super().__init__("ImpliedRunsAnalyst", "calibration", weight=1.5)

    def analyze(self, context: dict) -> AgentOpinion:
        team_implied_total = context.get("team_implied_total", 4.25)
        base_team_runs = context.get("base_team_projected_runs", 4.25)

        if base_team_runs > 0:
            scaling = team_implied_total / base_team_runs
            scaling = max(0.7, min(1.5, scaling))  # Cap at ±50%
        else:
            scaling = 1.0

        confidence = 0.80 if team_implied_total != 4.25 else 0.40

        reasoning = (
            f"Team implied {team_implied_total:.2f} vs base projected "
            f"{base_team_runs:.2f} -> scaling {scaling:.3f}"
        )

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=confidence,
            weight=self.weight,
            projection={
                "team_implied_total": team_implied_total,
                "base_team_projected_runs": base_team_runs,
                "scaling_factor": round(scaling, 3),
            },
            reasoning=reasoning,
            adjustments={
                "runs_multiplier": round(scaling, 3),
                "rbi_multiplier": round(scaling, 3),
            },
        )
