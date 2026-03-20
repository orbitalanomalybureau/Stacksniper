"""
STACKSNIPER MLB — Correlation Agent
Models intra-game correlations for DFS stacking.
"""
import numpy as np
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion

class CorrelationAgent(BaseAgent):
    """Models correlations between teammates for stacking."""
    def __init__(self):
        super().__init__("CorrelationAnalyst", "correlation", weight=1.0)

    ADJACENT_CORRELATION = 0.35
    SAME_TEAM_CORRELATION = 0.15
    OPP_PITCHER_NEGATIVE_CORR = -0.25

    def analyze(self, context: dict) -> AgentOpinion:
        players = context.get("stack_players", [])
        if len(players) < 2:
            return self._default()

        n = len(players)
        corr_matrix = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                corr = self._calculate_pair_correlation(players[i], players[j])
                corr_matrix[i][j] = corr
                corr_matrix[j][i] = corr

        stack_quality = self._evaluate_stack_quality(players, corr_matrix)

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.75,
            weight=self.weight,
            projection={
                "stack_quality": stack_quality,
                "stack_size": n,
                "avg_correlation": round(np.mean(corr_matrix[np.triu_indices(n, k=1)]), 3),
            },
            reasoning=f"Stack of {n} players, quality score: {stack_quality:.2f}",
            adjustments={"stack_boost": 1 + (stack_quality * 0.05)},
        )

    def _calculate_pair_correlation(self, p1: dict, p2: dict) -> float:
        if p1.get("team") == p2.get("team"):
            pos1 = p1.get("lineup_position", 5)
            pos2 = p2.get("lineup_position", 5)
            if abs(pos1 - pos2) <= 1:
                return self.ADJACENT_CORRELATION
            return self.SAME_TEAM_CORRELATION
        return 0.0

    def _evaluate_stack_quality(self, players: list, corr_matrix) -> float:
        if len(players) < 2:
            return 0.0
        score = 0.0
        positions = [p.get("lineup_position", 5) for p in players]
        sorted_pos = sorted(positions)
        for i in range(len(sorted_pos) - 1):
            if sorted_pos[i + 1] - sorted_pos[i] == 1:
                score += 0.15
        hot_count = sum(1 for p in positions if 2 <= p <= 5)
        score += hot_count * 0.1
        score += len(players) * 0.05
        return min(1.0, score)

    def _default(self) -> AgentOpinion:
        return AgentOpinion(
            agent_name=self.name, agent_type=self.agent_type,
            confidence=0.1, weight=0.1,
            projection={"stack_quality": 0.0},
            reasoning="Insufficient data for correlation analysis",
            adjustments={},
        )
