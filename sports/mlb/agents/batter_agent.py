"""
STACKSNIPER MLB — Batter Analysis Agent
Projects individual hitter performance against the opposing pitcher.
"""
import numpy as np
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion
from sports.mlb.data.mlb_api import mlb_api
from sports.mlb.data.historical_loader import historical_loader

class BatterAgent(BaseAgent):
    """Analyzes batter performance and projects DFS hitting stats."""
    def __init__(self):
        super().__init__("BatterAnalyst", "batter", weight=1.5)

    def analyze(self, context: dict) -> AgentOpinion:
        batter_id = context.get("batter_id")
        opp_pitcher_id = context.get("opp_pitcher_id")
        season = context.get("season")

        # v6 Opt 5: Use pre-fetched data from engine context if available
        season_stats = context.get("_prefetched_season_stats") or (
            mlb_api.get_player_stats(batter_id, season, "hitting", "season")
            if batter_id else {}
        )

        recent = context.get("_prefetched_recent_games") or (
            historical_loader.get_player_recent_games(batter_id, 15, "hitting")
            if batter_id else []
        )

        bvp = context.get("_prefetched_bvp") or (
            historical_loader.get_batter_vs_pitcher(batter_id, opp_pitcher_id)
            if batter_id and opp_pitcher_id else {}
        )

        splits = historical_loader.get_batter_splits(
            batter_id, season
        ) if batter_id else {}

        proj = self._project_batter(season_stats, recent, bvp, splits, context)

        confidence = self.adjust_confidence(
            0.8 if season_stats else 0.3,
            len(recent)
        )

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=confidence,
            weight=self.weight,
            projection=proj,
            reasoning=f"Season avg {season_stats.get('avg', 'N/A')}, {len(recent)} recent games analyzed",
        )

    def _project_batter(self, season: dict, recent: list, bvp: dict,
                         splits: dict, context: dict) -> dict:
        if not season:
            return self._default_batter_projection()

        games = max(1, int(season.get("gamesPlayed", 1)))
        ab_pg = float(season.get("atBats", 0)) / games
        pa_pg = float(season.get("plateAppearances", 0)) / games

        avg = float(season.get("avg", ".250"))
        obp = float(season.get("obp", ".320"))
        slg = float(season.get("slg", ".400"))

        hits_pg = float(season.get("hits", 0)) / games
        hr_pg = float(season.get("homeRuns", 0)) / games
        doubles_pg = float(season.get("doubles", 0)) / games
        triples_pg = float(season.get("triples", 0)) / games
        singles_pg = hits_pg - hr_pg - doubles_pg - triples_pg
        rbi_pg = float(season.get("rbi", 0)) / games
        runs_pg = float(season.get("runs", 0)) / games
        walks_pg = float(season.get("baseOnBalls", 0)) / games
        hbp_pg = float(season.get("hitByPitch", 0)) / games
        sb_pg = float(season.get("stolenBases", 0)) / games
        k_pg = float(season.get("strikeOuts", 0)) / games

        if len(recent) >= 5:
            recent_5 = recent[-5:]
            recent_avg = np.mean([float(g.get("avg", avg)) for g in recent_5
                                   if g.get("avg")])
            form_factor = 0.7 + 0.3 * (recent_avg / max(0.001, avg)) if avg > 0 else 1.0
            form_factor = max(0.7, min(1.4, form_factor))
        else:
            form_factor = 1.0

        bvp_factor = 1.0
        if bvp and int(bvp.get("atBats", 0)) >= 10:
            bvp_avg = float(bvp.get("avg", avg))
            bvp_factor = 0.75 + 0.25 * (bvp_avg / max(0.001, avg)) if avg > 0 else 1.0
            bvp_factor = max(0.6, min(1.5, bvp_factor))

        opp_throws = context.get("opp_pitcher_throws", "R")
        split_key = f"vs {opp_throws}HP" if opp_throws else None
        platoon_factor = 1.0
        if split_key and split_key in splits:
            split_avg = float(splits[split_key].get("avg", avg))
            platoon_factor = 0.7 + 0.3 * (split_avg / max(0.001, avg)) if avg > 0 else 1.0
            platoon_factor = max(0.7, min(1.4, platoon_factor))

        adj = form_factor * bvp_factor * platoon_factor

        return {
            "plate_appearances": round(pa_pg, 1),
            "at_bats": round(ab_pg, 1),
            "singles": round(max(0, singles_pg * adj), 2),
            "doubles": round(doubles_pg * adj, 3),
            "triples": round(triples_pg * adj, 3),
            "home_runs": round(hr_pg * adj, 3),
            "rbi": round(rbi_pg * adj, 2),
            "runs": round(runs_pg * adj, 2),
            "walks": round(walks_pg, 2),
            "hbp": round(hbp_pg, 3),
            "stolen_bases": round(sb_pg, 3),
            "strikeouts": round(k_pg, 2),
            "avg": avg,
            "obp": obp,
            "slg": slg,
            "form_factor": round(form_factor, 3),
            "bvp_factor": round(bvp_factor, 3),
            "platoon_factor": round(platoon_factor, 3),
        }

    def _default_batter_projection(self) -> dict:
        return {
            "plate_appearances": 3.8,
            "at_bats": 3.5,
            "singles": 0.60,
            "doubles": 0.18,
            "triples": 0.02,
            "home_runs": 0.10,
            "rbi": 0.50,
            "runs": 0.50,
            "walks": 0.30,
            "hbp": 0.03,
            "stolen_bases": 0.05,
            "strikeouts": 0.90,
            "avg": .250,
            "obp": .320,
            "slg": .400,
        }
