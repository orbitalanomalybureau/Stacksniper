"""
STACKSNIPER MLB — Pitcher Analysis Agent
Evaluates starting pitchers based on season stats, recent form, and matchups.
"""
import numpy as np
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion
from sports.mlb.data.mlb_api import mlb_api
from sports.mlb.data.historical_loader import historical_loader

class PitcherAgent(BaseAgent):
    """Analyzes starting pitcher performance and projects DFS output."""
    def __init__(self):
        super().__init__("PitcherAnalyst", "pitcher", weight=1.5)

    def analyze(self, context: dict) -> AgentOpinion:
        pitcher_id = context.get("pitcher_id")
        opp_team_id = context.get("opponent_team_id")
        season = context.get("season")

        # v6 Opt 5: Use pre-fetched data from engine context if available
        season_stats = context.get("_prefetched_season_stats") or (
            mlb_api.get_player_stats(pitcher_id, season, "pitching", "season")
            if pitcher_id else {}
        )

        recent = context.get("_prefetched_recent_games") or (
            historical_loader.get_player_recent_games(pitcher_id, 7, "pitching")
            if pitcher_id else []
        )

        vs_team = context.get("_prefetched_vs_team") or historical_loader.get_pitcher_vs_team(
            pitcher_id, opp_team_id, season
        ) if pitcher_id and opp_team_id else {}

        proj = self._project_pitcher(season_stats, recent, vs_team)
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
            reasoning=f"Based on {len(recent)} recent starts, season ERA {season_stats.get('era', 'N/A')}",
            adjustments=proj.get("adjustments", {}),
        )

    def _project_pitcher(self, season: dict, recent: list, vs_team: dict) -> dict:
        """Project pitcher performance from available data."""
        if not season:
            return self._default_pitcher_projection()

        games = max(1, int(season.get("gamesStarted", season.get("gamesPlayed", 1))))
        ip_per_start = float(season.get("inningsPitched", 0)) / games
        k_per_start = float(season.get("strikeOuts", 0)) / games
        er_per_start = float(season.get("earnedRuns", 0)) / games
        h_per_start = float(season.get("hits", 0)) / games
        bb_per_start = float(season.get("baseOnBalls", 0)) / games
        hbp_per_start = float(season.get("hitByPitch", 0)) / games

        if len(recent) >= 3:
            recent_3 = recent[-3:]
            recent_ip = np.mean([float(g.get("inningsPitched", 0)) for g in recent_3])
            recent_k = np.mean([float(g.get("strikeOuts", 0)) for g in recent_3])
            recent_er = np.mean([float(g.get("earnedRuns", 0)) for g in recent_3])
            ip_per_start = 0.6 * ip_per_start + 0.4 * recent_ip
            k_per_start = 0.6 * k_per_start + 0.4 * recent_k
            er_per_start = 0.6 * er_per_start + 0.4 * recent_er

        if vs_team and float(vs_team.get("inningsPitched", 0)) >= 10:
            vs_era = float(vs_team.get("era", season.get("era", 4.50)))
            season_era = float(season.get("era", 4.50))
            if season_era > 0:
                era_ratio = vs_era / season_era
                er_per_start *= (0.7 + 0.3 * era_ratio)

        era = float(season.get("era", 4.50))
        win_pct = max(0.15, min(0.65, 0.5 + (4.50 - era) * 0.05))

        return {
            "innings_pitched": round(ip_per_start, 1),
            "strikeouts": round(k_per_start, 1),
            "earned_runs": round(er_per_start, 1),
            "hits_against": round(h_per_start, 1),
            "walks_against": round(bb_per_start, 1),
            "hbp_against": round(hbp_per_start, 1),
            "win_probability": round(win_pct, 3),
            "std_ip": 1.2,
            "std_k": 2.0,
            "std_er": 1.5,
            "adjustments": {
                "form_multiplier": 0.92 if len(recent) >= 3 and
                    np.mean([float(g.get("era", 9)) for g in recent[-3:]]) <
                    float(season.get("era", 4.5)) else 1.10 if len(recent) >= 3 and
                    np.mean([float(g.get("era", 9)) for g in recent[-3:]]) >
                    float(season.get("era", 4.5)) * 1.2 else 1.0
            }
        }

    def _default_pitcher_projection(self) -> dict:
        return {
            "innings_pitched": 5.0,
            "strikeouts": 5.0,
            "earned_runs": 3.0,
            "hits_against": 6.0,
            "walks_against": 2.5,
            "hbp_against": 0.3,
            "win_probability": 0.40,
            "std_ip": 1.5,
            "std_k": 2.5,
            "std_er": 2.0,
        }
