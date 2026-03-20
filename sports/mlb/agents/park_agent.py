"""
STACKSNIPER MLB — Park Factor Agent
Adjusts projections based on ballpark characteristics.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion
from sports.mlb.config.team_mappings import PARK_FACTORS

class ParkAgent(BaseAgent):
    """Adjusts projections for park factors."""
    def __init__(self):
        super().__init__("ParkAnalyst", "environment", weight=1.0)

    def analyze(self, context: dict) -> AgentOpinion:
        home_team_abbr = context.get("home_team_abbr", "")
        factors = PARK_FACTORS.get(home_team_abbr, {})

        run_factor = factors.get("runs", 1.0)
        hr_factor = factors.get("hr", 1.0)
        hit_factor = factors.get("hits", 1.0)

        adjustments = {
            "runs_multiplier": run_factor,
            "hr_multiplier": hr_factor,
            "hits_multiplier": hit_factor,
            "doubles_multiplier": factors.get("doubles", 1.0),
            "triples_multiplier": factors.get("triples", 1.0),
        }

        rating = "hitter-friendly" if run_factor > 1.05 else \
                 "pitcher-friendly" if run_factor < 0.95 else "neutral"

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.9,
            weight=self.weight,
            projection={"park_rating": rating, "run_factor": run_factor},
            reasoning=f"{home_team_abbr} park is {rating} (run factor: {run_factor})",
            adjustments=adjustments,
        )
