"""
STACKSNIPER MLB — Lineup Order Agent
Adjusts projections based on batting order position.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion

LINEUP_PA_MULTIPLIER = {
    1: 1.12, 2: 1.08, 3: 1.04, 4: 1.01, 5: 0.98,
    6: 0.95, 7: 0.93, 8: 0.90, 9: 0.87,
}

LINEUP_RBI_MULTIPLIER = {
    1: 0.85, 2: 0.90, 3: 1.12, 4: 1.20, 5: 1.10,
    6: 1.00, 7: 0.92, 8: 0.85, 9: 0.78,
}

LINEUP_RUNS_MULTIPLIER = {
    1: 1.15, 2: 1.10, 3: 1.05, 4: 1.00, 5: 0.95,
    6: 0.92, 7: 0.88, 8: 0.85, 9: 0.80,
}

class LineupOrderAgent(BaseAgent):
    """Adjusts projections based on batting order position."""
    def __init__(self):
        super().__init__("LineupOrderAnalyst", "context", weight=0.9)

    def analyze(self, context: dict) -> AgentOpinion:
        lineup_pos = context.get("lineup_position", 5)
        pa_mult = LINEUP_PA_MULTIPLIER.get(lineup_pos, 1.0)
        rbi_mult = LINEUP_RBI_MULTIPLIER.get(lineup_pos, 1.0)
        runs_mult = LINEUP_RUNS_MULTIPLIER.get(lineup_pos, 1.0)

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.85,
            weight=self.weight,
            projection={
                "lineup_position": lineup_pos,
                "pa_multiplier": pa_mult,
                "rbi_multiplier": rbi_mult,
                "runs_multiplier": runs_mult,
            },
            reasoning=f"Batting {lineup_pos}th: PA×{pa_mult}, RBI×{rbi_mult}",
            adjustments={
                "pa_multiplier": pa_mult,
                "rbi_multiplier": rbi_mult,
                "runs_multiplier": runs_mult,
            },
        )
