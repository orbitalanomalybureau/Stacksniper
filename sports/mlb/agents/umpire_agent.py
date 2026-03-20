"""
STACKSNIPER MLB — Umpire Agent
Adjusts projections based on home plate umpire tendencies.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion

# Known umpire tendencies (positive = more calls, negative = fewer)
# k_rate_impact: multiplier on strikeout rate (>1.0 = more Ks)
# walk_rate_impact: multiplier on walk rate (>1.0 = more walks)
UMPIRE_TENDENCIES = {
    "Angel Hernandez": {"k_rate_impact": 0.95, "walk_rate_impact": 1.08},
    "CB Bucknor": {"k_rate_impact": 0.97, "walk_rate_impact": 1.05},
    "Joe West": {"k_rate_impact": 1.03, "walk_rate_impact": 0.96},
    "Ron Kulpa": {"k_rate_impact": 1.02, "walk_rate_impact": 0.98},
    "Laz Diaz": {"k_rate_impact": 0.96, "walk_rate_impact": 1.04},
    "Marvin Hudson": {"k_rate_impact": 1.01, "walk_rate_impact": 1.02},
    "Jeff Nelson": {"k_rate_impact": 1.04, "walk_rate_impact": 0.95},
    "Lance Barksdale": {"k_rate_impact": 1.02, "walk_rate_impact": 0.97},
    "Pat Hoberg": {"k_rate_impact": 1.00, "walk_rate_impact": 1.00},
    "Nic Lentz": {"k_rate_impact": 1.03, "walk_rate_impact": 0.97},
}

class UmpireAgent(BaseAgent):
    """Adjusts projections based on home plate umpire tendencies."""

    def __init__(self):
        super().__init__("UmpireAnalyst", "umpire", weight=0.5)

    def analyze(self, context: dict) -> AgentOpinion:
        umpire_name = context.get("umpire_name", "")

        if not umpire_name or umpire_name not in UMPIRE_TENDENCIES:
            return AgentOpinion(
                agent_name=self.name,
                agent_type=self.agent_type,
                confidence=0.1,
                weight=0.1,
                projection={"umpire": umpire_name or "Unknown"},
                reasoning="No umpire data available",
                adjustments={},
            )

        tendencies = UMPIRE_TENDENCIES[umpire_name]
        k_impact = tendencies["k_rate_impact"]
        bb_impact = tendencies["walk_rate_impact"]

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.4,
            weight=self.weight,
            projection={
                "umpire": umpire_name,
                "k_rate_impact": k_impact,
                "walk_rate_impact": bb_impact,
            },
            reasoning=f"Umpire {umpire_name}: K rate x{k_impact}, BB rate x{bb_impact}",
            adjustments={
                "k_rate_multiplier": k_impact,
                "walk_rate_multiplier": bb_impact,
            },
        )
