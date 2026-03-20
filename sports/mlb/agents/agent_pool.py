"""
STACKSNIPER MLB — Agent Pool Manager
Manages the swarm of specialist agents and aggregates their opinions.
"""
import numpy as np
from typing import List
from sports.mlb.agents.base_agent import AgentOpinion
from sports.mlb.agents.pitcher_agent import PitcherAgent
from sports.mlb.agents.batter_agent import BatterAgent
from sports.mlb.agents.park_agent import ParkAgent
from sports.mlb.agents.weather_agent import WeatherAgent
from sports.mlb.agents.matchup_agent import MatchupAgent
from sports.mlb.agents.momentum_agent import MomentumAgent
from sports.mlb.agents.bullpen_agent import BullpenAgent
from sports.mlb.agents.vegas_agent import VegasAgent
from sports.mlb.agents.lineup_order_agent import LineupOrderAgent
from sports.mlb.agents.correlation_agent import CorrelationAgent
from sports.mlb.agents.umpire_agent import UmpireAgent
from sports.mlb.agents.rest_days_agent import RestDaysAgent
from sports.mlb.agents.handedness_agent import HandednessAgent
from sports.mlb.agents.implied_runs_agent import ImpliedRunsAgent
from sports.mlb.agents.home_away_agent import HomeAwayAgent
from sports.mlb.agents.recent_form_agent import RecentFormAgent
from sports.mlb.utils.logger import get_logger

log = get_logger("AgentPool")

class AgentPool:
    """
    Manages all specialist agents and aggregates their opinions
    using weighted consensus for Monte Carlo simulation inputs.
    """
    def __init__(self):
        self.agents = {
            "pitcher": PitcherAgent(),
            "batter": BatterAgent(),
            "park": ParkAgent(),
            "weather": WeatherAgent(),
            "matchup": MatchupAgent(),
            "momentum": MomentumAgent(),
            "bullpen": BullpenAgent(),
            "vegas": VegasAgent(),
            "lineup_order": LineupOrderAgent(),
            "correlation": CorrelationAgent(),
            "umpire": UmpireAgent(),
            "rest_days": RestDaysAgent(),
            "handedness": HandednessAgent(),
            "implied_runs": ImpliedRunsAgent(),
            "home_away": HomeAwayAgent(),
            "recent_form": RecentFormAgent(),
        }
        log.info(f"Agent pool initialized with {len(self.agents)} agents")

    def get_consensus_hitter_projection(self, context: dict) -> dict:
        opinions = []
        opinions.append(self.agents["batter"].analyze(context))
        opinions.append(self.agents["park"].analyze(context))
        opinions.append(self.agents["weather"].analyze(context))
        opinions.append(self.agents["matchup"].analyze(context))
        opinions.append(self.agents["momentum"].analyze(context))
        opinions.append(self.agents["lineup_order"].analyze(context))
        opinions.append(self.agents["bullpen"].analyze(context))
        opinions.append(self.agents["vegas"].analyze(context))
        opinions.append(self.agents["umpire"].analyze(context))
        opinions.append(self.agents["rest_days"].analyze(context))
        opinions.append(self.agents["handedness"].analyze(context))
        opinions.append(self.agents["home_away"].analyze(context))
        opinions.append(self.agents["recent_form"].analyze(context))
        opinions.append(self.agents["implied_runs"].analyze(context))
        return self._aggregate_hitter_opinions(opinions, context)

    def get_consensus_pitcher_projection(self, context: dict) -> dict:
        opinions = []
        opinions.append(self.agents["pitcher"].analyze(context))
        opinions.append(self.agents["park"].analyze(context))
        opinions.append(self.agents["weather"].analyze(context))
        opinions.append(self.agents["vegas"].analyze(context))
        opinions.append(self.agents["momentum"].analyze(context))
        opinions.append(self.agents["umpire"].analyze(context))
        opinions.append(self.agents["rest_days"].analyze(context))
        return self._aggregate_pitcher_opinions(opinions, context)

    def get_stack_analysis(self, context: dict) -> AgentOpinion:
        return self.agents["correlation"].analyze(context)

    def _aggregate_hitter_opinions(self, opinions: List[AgentOpinion],
                                    context: dict) -> dict:
        base = None
        for op in opinions:
            if op.agent_type == "batter":
                base = op.projection.copy()
                break
        if not base:
            return {}

        adjustments = {
            "runs_multiplier": [],
            "hr_multiplier": [],
            "hits_multiplier": [],
            "pa_multiplier": [],
            "rbi_multiplier": [],
            "sb_multiplier": [],
            "k_rate_multiplier": [],
            "walk_rate_multiplier": [],
            "form_multiplier": [],
            "doubles_multiplier": [],   # v3 Phase 1.7
            "triples_multiplier": [],   # v3 Phase 1.7
        }

        # v3 Phase 1.6: Collect VegasAgent implied totals for later scaling
        vegas_home_target = None
        vegas_away_target = None

        for op in opinions:
            if op.adjustments:
                w = op.weight * op.confidence
                for key, value in op.adjustments.items():
                    if key in adjustments and isinstance(value, (int, float)):
                        adjustments[key].append((value, w))
                # v3 Phase 1.6: Capture Vegas implied team totals
                if op.agent_name == "VegasAnalyst":
                    if "home_runs_target" in op.adjustments:
                        vegas_home_target = op.adjustments["home_runs_target"]
                    if "away_runs_target" in op.adjustments:
                        vegas_away_target = op.adjustments["away_runs_target"]

        final_adj = {}
        for key, values in adjustments.items():
            if values:
                total_w = sum(w for _, w in values)
                if total_w > 0:
                    weighted_avg = sum(v * w for v, w in values) / total_w
                    final_adj[key] = weighted_avg
                else:
                    final_adj[key] = 1.0
            else:
                final_adj[key] = 1.0

        base["singles"] = base.get("singles", 0) * final_adj.get("hits_multiplier", 1.0)
        # v3 Phase 1.7: Apply doubles/triples multipliers separately from hits_multiplier
        base["doubles"] = base.get("doubles", 0) * final_adj.get("doubles_multiplier", 1.0) * final_adj.get("hits_multiplier", 1.0)
        base["triples"] = base.get("triples", 0) * final_adj.get("triples_multiplier", 1.0) * final_adj.get("hits_multiplier", 1.0)
        base["home_runs"] = base.get("home_runs", 0) * final_adj.get("hr_multiplier", 1.0)
        base["rbi"] = base.get("rbi", 0) * final_adj.get("rbi_multiplier", 1.0)
        base["runs"] = base.get("runs", 0) * final_adj.get("runs_multiplier", 1.0)
        base["plate_appearances"] = base.get("plate_appearances", 3.8) * final_adj.get("pa_multiplier", 1.0)
        base["stolen_bases"] = base.get("stolen_bases", 0) * final_adj.get("sb_multiplier", 1.0)
        base["strikeouts"] = base.get("strikeouts", 0) * final_adj.get("k_rate_multiplier", 1.0)
        base["walks"] = base.get("walks", 0) * final_adj.get("walk_rate_multiplier", 1.0)

        # Apply form_multiplier as an additional overall scaling on core stats
        form_mult = final_adj.get("form_multiplier", 1.0)
        if form_mult != 1.0:
            for stat_key in ["singles", "doubles", "triples", "home_runs", "rbi", "runs"]:
                base[stat_key] = base.get(stat_key, 0) * form_mult

        # v3 Phase 1.6: Apply Vegas implied total as a scaling factor
        is_home = context.get("is_home", False)
        implied_total = vegas_home_target if is_home else vegas_away_target

        if implied_total is not None and implied_total > 0:
            # Sum projected runs contribution for this player
            base_projected_runs = base.get("runs", 0) + base.get("rbi", 0) - base.get("home_runs", 0)
            if base_projected_runs > 0:
                # Estimate team total from this player's share (assume ~9 hitters)
                estimated_team_total = base_projected_runs * 9
                if estimated_team_total > 0:
                    vegas_multiplier = implied_total / estimated_team_total
                    # Clamp to avoid extreme adjustments
                    vegas_multiplier = max(0.6, min(1.6, vegas_multiplier))
                    base["runs"] = base.get("runs", 0) * vegas_multiplier
                    base["rbi"] = base.get("rbi", 0) * vegas_multiplier
                    base["home_runs"] = base.get("home_runs", 0) * vegas_multiplier

        # --- Agent disagreement → variance (Section 2.6) ---
        agent_disagreement_score = self._compute_agent_disagreement(adjustments)
        base["agent_disagreement_score"] = round(agent_disagreement_score, 4)
        if agent_disagreement_score > 0.15:
            base["simulation_noise_boost"] = 1.20  # Increase sim noise by 20%
        else:
            base["simulation_noise_boost"] = 1.0

        for key in base:
            if isinstance(base[key], float):
                base[key] = round(base[key], 3)

        base["agent_opinions"] = [
            {"agent": op.agent_name, "confidence": op.confidence, "reasoning": op.reasoning}
            for op in opinions
        ]
        return base

    def _aggregate_pitcher_opinions(self, opinions: List[AgentOpinion],
                                     context: dict) -> dict:
        base = None
        for op in opinions:
            if op.agent_type == "pitcher":
                base = op.projection.copy()
                break
        if not base:
            return {}

        runs_multiplier = 1.0
        er_multiplier = 1.0
        form_multiplier = 1.0
        ip_multiplier = 1.0
        k_rate_multiplier = 1.0

        for op in opinions:
            if not op.adjustments:
                continue

            if "runs_multiplier" in op.adjustments:
                factor = op.adjustments["runs_multiplier"]
                if isinstance(factor, (int, float)):
                    runs_multiplier *= (0.7 + 0.3 * factor)

            if "pitcher_er_multiplier" in op.adjustments:
                factor = op.adjustments["pitcher_er_multiplier"]
                if isinstance(factor, (int, float)):
                    er_multiplier *= (0.7 + 0.3 * factor)

            if "form_multiplier" in op.adjustments:
                factor = op.adjustments["form_multiplier"]
                if isinstance(factor, (int, float)):
                    form_multiplier *= (0.7 + 0.3 * factor)

            if "ip_multiplier" in op.adjustments:
                factor = op.adjustments["ip_multiplier"]
                if isinstance(factor, (int, float)):
                    ip_multiplier *= (0.7 + 0.3 * factor)

            if "k_rate_multiplier" in op.adjustments:
                factor = op.adjustments["k_rate_multiplier"]
                if isinstance(factor, (int, float)):
                    k_rate_multiplier *= (0.7 + 0.3 * factor)

        combined_er = runs_multiplier * er_multiplier * form_multiplier
        base["earned_runs"] = base.get("earned_runs", 3.0) * combined_er
        base["hits_against"] = base.get("hits_against", 6.0) * runs_multiplier
        base["innings_pitched"] = base.get("innings_pitched", 5.5) * ip_multiplier
        base["strikeouts"] = base.get("strikeouts", 5.0) * k_rate_multiplier

        for key in base:
            if isinstance(base[key], float):
                base[key] = round(base[key], 3)

        base["agent_opinions"] = [
            {"agent": op.agent_name, "confidence": op.confidence, "reasoning": op.reasoning}
            for op in opinions
        ]
        return base

    def _compute_agent_disagreement(self, adjustments: dict) -> float:
        """
        Compute the average standard deviation of agent multipliers across
        all adjustment keys. High std means agents disagree significantly.
        """
        stds = []
        for key, values in adjustments.items():
            if len(values) >= 2:
                raw_values = [v for v, _ in values]
                stds.append(float(np.std(raw_values)))
        if stds:
            return float(np.mean(stds))
        return 0.0

# Singleton
agent_pool = AgentPool()
