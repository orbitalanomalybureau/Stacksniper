"""
STACKSNIPER MLB — Handedness (Platoon) Analysis Agent
Adjusts projections based on batter/pitcher handedness matchups.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion


class HandednessAgent(BaseAgent):
    """Adjusts projections based on batter/pitcher handedness matchups."""

    # Platoon advantage factors (empirical MLB averages)
    PLATOON_MAP = {
        ("L", "R"): 1.08,   # LHB vs RHP = advantage
        ("L", "L"): 0.88,   # LHB vs LHP = disadvantage
        ("R", "L"): 1.10,   # RHB vs LHP = advantage
        ("R", "R"): 0.97,   # RHB vs RHP = slight disadvantage
        ("S", "R"): 1.02,   # Switch vs RHP = slight advantage (batting L)
        ("S", "L"): 1.05,   # Switch vs LHP = advantage (batting R)
    }

    def __init__(self):
        super().__init__("HandednessAnalyst", "platoon", weight=1.0)

    def analyze(self, context: dict) -> AgentOpinion:
        batter_bats = context.get("batter_bats", "R")   # L, R, or S
        pitcher_throws = context.get("pitcher_throws", "R")  # L or R

        factor = self.PLATOON_MAP.get((batter_bats, pitcher_throws), 1.0)

        # Power bonus: platoon advantage amplifies HR potential
        if factor > 1.0:
            hr_factor = factor * 1.05  # Extra 5% HR boost on platoon advantage
        elif factor < 1.0:
            hr_factor = factor * 0.97  # Extra 3% HR penalty on disadvantage
        else:
            hr_factor = 1.0

        # Contact adjustment: walks suppressed in platoon disadvantage
        if factor < 0.95:
            walk_factor = factor * 0.95  # Walks suppressed in disadvantage
        else:
            walk_factor = 1.0  # Neutral or advantage — no walk suppression

        # Confidence is high because platoon splits are well-established
        confidence = 0.85

        reasoning = (
            f"Platoon: {batter_bats}-handed batter vs {pitcher_throws}-handed pitcher "
            f"-> factor {factor:.2f}"
        )

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=confidence,
            weight=self.weight,
            projection={
                "platoon_factor": round(factor, 3),
                "batter_bats": batter_bats,
                "pitcher_throws": pitcher_throws,
            },
            reasoning=reasoning,
            adjustments={
                "hits_multiplier": round(factor, 3),
                "hr_multiplier": round(hr_factor, 3),
                "walk_rate_multiplier": round(walk_factor, 3),
            },
        )
