"""
STACKSNIPER MLB — Rest Days Agent
Analyzes player rest patterns and fatigue.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion
from sports.mlb.data.historical_loader import historical_loader

class RestDaysAgent(BaseAgent):
    """Analyzes rest patterns and fatigue for pitchers and hitters."""

    def __init__(self):
        super().__init__("RestDaysAnalyst", "fatigue", weight=0.6)

    def analyze(self, context: dict) -> AgentOpinion:
        player_id = context.get("player_id") or context.get("batter_id") or context.get("pitcher_id")
        player_type = context.get("type", "batter")

        if not player_id:
            return self._neutral()

        stat_group = "pitching" if player_type == "pitcher" else "hitting"
        recent = historical_loader.get_player_recent_games(player_id, 20, stat_group)

        if not recent:
            return self._neutral()

        if player_type == "pitcher":
            return self._analyze_pitcher_rest(recent, context)
        else:
            return self._analyze_hitter_fatigue(recent, context)

    def _analyze_pitcher_rest(self, recent: list, context: dict) -> AgentOpinion:
        """Analyze pitcher rest days since last start."""
        if len(recent) < 2:
            return self._neutral()

        # Check days between last two appearances
        dates = [g.get("date", "") for g in recent if g.get("date")]
        if len(dates) < 2:
            multiplier = 1.0
            reasoning = "Insufficient date data"
        else:
            # Estimate days of rest (standard is 4-5 days)
            # Extra rest = slight boost, short rest = penalty
            games_in_window = len(recent)
            if games_in_window <= 3:
                multiplier = 1.03  # Extra rest
                reasoning = f"Extended rest ({games_in_window} starts in window) — slight boost"
            elif games_in_window >= 8:
                multiplier = 0.97  # Heavy workload
                reasoning = f"Heavy workload ({games_in_window} appearances) — slight fatigue"
            else:
                multiplier = 1.0
                reasoning = "Normal rest pattern"

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.45,
            weight=self.weight,
            projection={"rest_multiplier": multiplier},
            reasoning=reasoning,
            adjustments={
                "pitcher_er_multiplier": 2.0 - multiplier,  # Inverse: more rest = fewer ER
                "ip_multiplier": multiplier,
            },
        )

    def _analyze_hitter_fatigue(self, recent: list, context: dict) -> AgentOpinion:
        """Analyze hitter fatigue from consecutive games."""
        games_played = len(recent)

        if games_played >= 15:
            multiplier = 0.97  # Slight fatigue after 15+ consecutive
            reasoning = f"{games_played} consecutive games — minor fatigue factor"
        elif games_played <= 3:
            multiplier = 0.95  # Rust factor — just returned
            reasoning = f"Only {games_played} recent games — possible rust factor"
        else:
            multiplier = 1.0
            reasoning = "Normal game frequency"

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.40,
            weight=self.weight,
            projection={"fatigue_multiplier": multiplier},
            reasoning=reasoning,
            adjustments={
                "hits_multiplier": multiplier,
                "runs_multiplier": multiplier,
            },
        )

    def _neutral(self) -> AgentOpinion:
        return AgentOpinion(
            agent_name=self.name, agent_type=self.agent_type,
            confidence=0.1, weight=0.1,
            projection={"rest_multiplier": 1.0},
            reasoning="Insufficient data for rest analysis",
            adjustments={},
        )
