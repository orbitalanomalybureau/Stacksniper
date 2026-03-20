"""
STACKSNIPER MLB — Recent Form Agent
Computes a form multiplier based on rolling performance over recent games.
Replaces the crude form_factor inside BatterAgent with a more sophisticated
rolling wOBA proxy approach.
"""
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion
from sports.mlb.data.historical_loader import historical_loader


class RecentFormAgent(BaseAgent):
    """Analyzes recent batting form using rolling wOBA proxy and streaks."""

    # wOBA weights (simplified, standard linear weights)
    WOBA_WEIGHTS = {
        "bb": 0.69,
        "hbp": 0.72,
        "single": 0.88,
        "double": 1.27,
        "triple": 1.62,
        "hr": 2.10,
    }
    WOBA_SCALE = 1.15  # Normalizing denominator scale

    def __init__(self):
        super().__init__("RecentFormAnalyst", "recent_form", weight=0.8)

    def analyze(self, context: dict) -> AgentOpinion:
        batter_id = context.get("batter_id")

        if not batter_id:
            return self._neutral_opinion()

        # Fetch recent game logs (up to 30 games)
        game_log = historical_loader.get_player_recent_games(
            batter_id, 30, "hitting"
        ) if batter_id else []

        if not game_log or len(game_log) < 3:
            return self._neutral_opinion()

        season_woba = self._estimate_season_woba(context)

        # Compute rolling wOBA for last-10 and last-30 windows
        last_10 = game_log[-10:] if len(game_log) >= 10 else game_log
        last_30 = game_log  # Already capped at 30

        woba_10 = self._compute_woba(last_10)
        woba_30 = self._compute_woba(last_30)

        # Choose weighting based on data availability
        if len(game_log) >= 10:
            # 85% season + 15% last-10
            blended_woba = 0.85 * season_woba + 0.15 * woba_10
            window_label = f"L10 wOBA {woba_10:.3f}"
        else:
            # 70% season + 30% last-30 (really however many games we have)
            blended_woba = 0.70 * season_woba + 0.30 * woba_30
            window_label = f"L{len(game_log)} wOBA {woba_30:.3f}"

        # Compute form multiplier
        if season_woba > 0:
            form_multiplier = blended_woba / season_woba
        else:
            form_multiplier = 1.0

        form_multiplier = max(0.80, min(1.25, form_multiplier))

        # Streak analysis — consecutive good/bad games as confidence modifier
        streak_length, streak_positive = self._compute_streak(game_log, season_woba)

        # Streaks modify confidence: long streaks = higher confidence in form
        base_confidence = self.adjust_confidence(0.7, len(game_log))
        streak_bonus = min(0.15, streak_length * 0.02) if streak_length >= 3 else 0.0
        confidence = min(1.0, base_confidence + streak_bonus)

        reasoning = (
            f"Form: {window_label}, season wOBA {season_woba:.3f}, "
            f"blended {blended_woba:.3f} -> multiplier {form_multiplier:.3f}. "
            f"Streak: {'+' if streak_positive else '-'}{streak_length} games"
        )

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=confidence,
            weight=self.weight,
            projection={
                "woba_last_10": round(woba_10, 3) if len(game_log) >= 10 else None,
                "woba_last_30": round(woba_30, 3),
                "season_woba": round(season_woba, 3),
                "blended_woba": round(blended_woba, 3),
                "streak_length": streak_length,
                "streak_positive": streak_positive,
                "games_analyzed": len(game_log),
            },
            reasoning=reasoning,
            adjustments={
                "form_multiplier": round(form_multiplier, 3),
                "hits_multiplier": round(form_multiplier, 3),
                "hr_multiplier": round(form_multiplier, 3),
            },
        )

    def _compute_woba(self, games: list) -> float:
        """Compute a wOBA proxy from game log data."""
        total_numerator = 0.0
        total_pa = 0

        for g in games:
            pa = int(g.get("plateAppearances", 0)) or (
                int(g.get("atBats", 0)) + int(g.get("baseOnBalls", 0)) +
                int(g.get("hitByPitch", 0)) + int(g.get("sacFlies", 0))
            )
            if pa == 0:
                continue

            hits = int(g.get("hits", 0))
            doubles = int(g.get("doubles", 0))
            triples = int(g.get("triples", 0))
            hr = int(g.get("homeRuns", 0))
            singles = hits - doubles - triples - hr
            bb = int(g.get("baseOnBalls", 0))
            hbp = int(g.get("hitByPitch", 0))

            numerator = (
                self.WOBA_WEIGHTS["bb"] * bb +
                self.WOBA_WEIGHTS["hbp"] * hbp +
                self.WOBA_WEIGHTS["single"] * max(0, singles) +
                self.WOBA_WEIGHTS["double"] * doubles +
                self.WOBA_WEIGHTS["triple"] * triples +
                self.WOBA_WEIGHTS["hr"] * hr
            )
            total_numerator += numerator
            total_pa += pa

        if total_pa == 0:
            return 0.320  # League average fallback

        return total_numerator / (total_pa * self.WOBA_SCALE)

    def _estimate_season_woba(self, context: dict) -> float:
        """Estimate season wOBA from context stats."""
        obp = float(context.get("batter_obp", 0.320))
        slg = float(context.get("batter_slg", 0.400))
        # Rough wOBA approximation: wOBA ~ 0.7 * OBP + 0.3 * SLG (simplified)
        woba = 0.7 * obp + 0.3 * slg
        return max(0.200, min(0.500, woba))

    def _compute_streak(self, games: list, season_woba: float) -> tuple:
        """
        Compute streak length and direction.
        A 'good' game is one where the single-game wOBA proxy >= season_woba.
        Returns (streak_length, is_positive).
        """
        if not games:
            return (0, True)

        streak_length = 0
        streak_positive = None

        # Walk backwards from most recent game
        for g in reversed(games):
            game_woba = self._compute_woba([g])
            is_good = game_woba >= season_woba

            if streak_positive is None:
                streak_positive = is_good

            if is_good == streak_positive:
                streak_length += 1
            else:
                break

        return (streak_length, streak_positive if streak_positive is not None else True)

    def _neutral_opinion(self) -> AgentOpinion:
        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.1,
            weight=0.1,
            projection={"games_analyzed": 0},
            reasoning="Insufficient recent game data for form analysis",
            adjustments={"form_multiplier": 1.0, "hits_multiplier": 1.0},
        )
