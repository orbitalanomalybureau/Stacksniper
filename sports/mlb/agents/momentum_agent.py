"""
STACKSNIPER MLB — Momentum Agent
Evaluates recent team performance trends and streaks.
"""
import numpy as np
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion
from sports.mlb.data.historical_loader import historical_loader

class MomentumAgent(BaseAgent):
    """Evaluates team momentum and recent performance trends."""
    def __init__(self):
        super().__init__("MomentumAnalyst", "trend", weight=0.7)

    def analyze(self, context: dict) -> AgentOpinion:
        team_id = context.get("team_id")
        if not team_id:
            return self._neutral()

        recent_games = historical_loader.get_team_recent_results(team_id, 10)
        if len(recent_games) < 3:
            return self._neutral()

        wins = 0
        total_runs = []
        for g in recent_games:
            is_home = g["home_team"]["id"] == team_id
            team_score = g["home_team"]["score"] if is_home else g["away_team"]["score"]
            opp_score = g["away_team"]["score"] if is_home else g["home_team"]["score"]
            if team_score > opp_score:
                wins += 1
            total_runs.append(team_score)

        win_rate = wins / len(recent_games)
        avg_runs = np.mean(total_runs) if total_runs else 4.5

        momentum = 0.85 + 0.3 * win_rate

        streak = self._detect_streak(recent_games, team_id)

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=self.adjust_confidence(0.6, len(recent_games)),
            weight=self.weight,
            projection={
                "momentum_factor": round(momentum, 3),
                "recent_win_rate": round(win_rate, 3),
                "avg_runs_scored": round(avg_runs, 2),
                "streak": streak,
            },
            reasoning=f"Last {len(recent_games)} games: {wins}W, {avg_runs:.1f} R/G, {streak}",
            adjustments={"runs_multiplier": momentum},
        )

    def _detect_streak(self, games: list, team_id: int) -> str:
        if not games:
            return "N/A"
        streak_type = None
        streak_count = 0
        for g in reversed(games):
            is_home = g["home_team"]["id"] == team_id
            team_score = g["home_team"]["score"] if is_home else g["away_team"]["score"]
            opp_score = g["away_team"]["score"] if is_home else g["home_team"]["score"]
            won = team_score > opp_score
            if streak_type is None:
                streak_type = "W" if won else "L"
                streak_count = 1
            elif (won and streak_type == "W") or (not won and streak_type == "L"):
                streak_count += 1
            else:
                break
        return f"{streak_type}{streak_count}"

    def _neutral(self) -> AgentOpinion:
        return AgentOpinion(
            agent_name=self.name, agent_type=self.agent_type,
            confidence=0.1, weight=0.1,
            projection={"momentum_factor": 1.0},
            reasoning="Insufficient data for momentum analysis",
            adjustments={"runs_multiplier": 1.0},
        )
