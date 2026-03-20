"""
STACKSNIPER MLB — Vegas Line Agent
Uses implied team totals from over/under and moneyline for calibration.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion

class VegasAgent(BaseAgent):
    """Integrates Vegas lines as a calibration signal."""
    def __init__(self):
        super().__init__("VegasAnalyst", "calibration", weight=1.3)

    def analyze(self, context: dict) -> AgentOpinion:
        total = context.get("total")
        home_ml = context.get("home_ml")
        away_ml = context.get("away_ml")

        if not total:
            return self._default()

        if home_ml and away_ml:
            home_imp_pct = self._ml_to_implied_pct(home_ml)
            away_imp_pct = self._ml_to_implied_pct(away_ml)
            total_imp = home_imp_pct + away_imp_pct
            home_pct = home_imp_pct / total_imp
            away_pct = away_imp_pct / total_imp
            home_implied = total * home_pct
            away_implied = total * (1 - home_pct)
        else:
            home_pct = 0.54
            away_pct = 0.46
            home_implied = total * 0.52
            away_implied = total * 0.48

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.85,
            weight=self.weight,
            projection={
                "total": total,
                "home_implied_total": round(home_implied, 2),
                "away_implied_total": round(away_implied, 2),
                "home_win_pct": round(home_pct, 3),
                "away_win_pct": round(away_pct, 3),
            },
            reasoning=f"O/U {total}, implied: H={home_implied:.1f} A={away_implied:.1f}",
            adjustments={
                "home_runs_target": home_implied,
                "away_runs_target": away_implied,
            },
        )

    def _ml_to_implied_pct(self, ml: int) -> float:
        if ml > 0:
            return 100 / (ml + 100)
        else:
            return abs(ml) / (abs(ml) + 100)

    def _default(self) -> AgentOpinion:
        return AgentOpinion(
            agent_name=self.name, agent_type=self.agent_type,
            confidence=0.3, weight=0.3,
            projection={"total": 8.5, "home_implied_total": 4.5, "away_implied_total": 4.0},
            reasoning="No Vegas lines available — using default",
            adjustments={},
        )
