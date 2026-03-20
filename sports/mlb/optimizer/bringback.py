"""
STACKSNIPER MLB v3.0 — Phase 3.7: Bring-Back Stacking
Enforces and recommends "bring-back" players — hitters from the opposing
team of your primary stack, correlated via the same high-scoring game
environment.
"""
from __future__ import annotations
from typing import List, Dict, Tuple
from sports.mlb.data.models import PlayerProjection
from sports.mlb.utils.logger import get_logger

log = get_logger("BringBack")

# Batting-order positions that get the most plate appearances and
# therefore the highest bring-back upside.
_PREMIUM_LINEUP_SPOTS = {1, 2, 3, 4, 5}  # leadoff through cleanup + 5-hole

# Positions that are never a bring-back (pitchers)
_PITCHER_POSITIONS = {"SP", "RP", "P"}


class BringBackManager:
    """Identify, score, and enforce bring-back stacking rules.

    A "bring-back" is a hitter from the *opposing* team of the lineup's
    primary stack.  Including one (or more) brings the lineup's ceiling
    exposure to both sides of a high-total game.
    """

    def __init__(self):
        pass

    # ── Validation ────────────────────────────────────────────────────

    def apply_bringback(
        self,
        lineup: dict,
        stacks: List[dict],
        min_bringback: int = 1,
    ) -> dict:
        """Validate that *lineup* contains at least *min_bringback* opposing
        players relative to the largest stack in the lineup.

        Args:
            lineup:        Lineup dict with a 'players' list of PlayerProjection.
            stacks:        Stack info dicts (from DKOptimizer.find_stacks) so we
                           know which team is the "primary stack".
            min_bringback: Minimum number of bring-back players required.

        Returns:
            Dict with keys:
                valid (bool), primary_stack_team (str), opponent (str),
                bringback_players (list of names), count (int),
                message (str).
        """
        players: List[PlayerProjection] = lineup.get("players", [])
        if not players:
            return self._result(False, "", "", [], "Lineup has no players")

        # Determine the primary stack team (most hitters from one team)
        stack_team, opponent = self._detect_primary_stack(players)
        if not stack_team:
            return self._result(False, "", "", [], "No clear team stack detected")

        # Find bring-back players in the lineup
        bringbacks = [
            p for p in players
            if p.team == opponent and p.position not in _PITCHER_POSITIONS
        ]

        valid = len(bringbacks) >= min_bringback
        names = [p.name for p in bringbacks]
        if valid:
            msg = (
                f"Lineup has {len(bringbacks)} bring-back(s) from {opponent} "
                f"opposing {stack_team} stack"
            )
        else:
            msg = (
                f"Lineup needs {min_bringback} bring-back(s) from {opponent} "
                f"but only has {len(bringbacks)}"
            )

        return self._result(valid, stack_team, opponent, names, msg)

    # ── Candidate Discovery ──────────────────────────────────────────

    def find_bringback_candidates(
        self,
        stack_team: str,
        opponent_team: str,
        players: List[PlayerProjection],
        top_n: int = 10,
    ) -> List[dict]:
        """Return the best opposing-team hitters to use as bring-backs.

        Scoring formula prioritises:
          - High ceiling (GPP upside)
          - Premium batting-order spots (leadoff / cleanup)
          - Good value (pts / salary)

        Args:
            stack_team:    The team you are stacking.
            opponent_team: The opposing team (bring-back source).
            players:       Full player pool.
            top_n:         Max candidates to return.

        Returns:
            Sorted list of dicts with player info + bringback_score.
        """
        candidates: List[Tuple[float, PlayerProjection]] = []

        for p in players:
            if p.team != opponent_team:
                continue
            if p.position in _PITCHER_POSITIONS:
                continue
            if p.salary <= 0:
                continue

            score = self._score_bringback(p)
            candidates.append((score, p))

        # Sort descending by score
        candidates.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, p in candidates[:top_n]:
            results.append({
                "player_id": p.player_id,
                "name": p.name,
                "team": p.team,
                "position": p.position,
                "salary": p.salary,
                "dk_points": round(p.dk_points, 2),
                "ceiling": round(p.ceiling, 2),
                "value": round(p.value, 2),
                "bringback_score": round(score, 3),
                "opposing_stack": stack_team,
            })

        log.info(
            f"Found {len(results)} bring-back candidates from {opponent_team} "
            f"vs {stack_team} stack"
        )
        return results

    # ── PuLP Constraint Helper ───────────────────────────────────────

    def build_bringback_constraint(
        self,
        players: List[PlayerProjection],
        player_vars: dict,
        stack_team: str,
        opponent_team: str,
        min_bringback: int = 1,
    ):
        """Return a PuLP constraint expression requiring at least
        *min_bringback* hitters from *opponent_team*.

        Usage inside the optimizer:
            constraint = bringback_mgr.build_bringback_constraint(...)
            if constraint is not None:
                prob += constraint

        Returns:
            A PuLP LpConstraint, or None if there are no eligible players.
        """
        try:
            import pulp
        except ImportError:
            log.warning("PuLP not available — cannot build bring-back constraint")
            return None

        eligible = [
            p for p in players
            if p.team == opponent_team and p.position not in _PITCHER_POSITIONS
        ]
        if not eligible:
            log.warning(f"No eligible bring-back players from {opponent_team}")
            return None

        return (
            pulp.lpSum(player_vars[p.player_id] for p in eligible if p.player_id in player_vars)
            >= min_bringback
        )

    # ── Internals ─────────────────────────────────────────────────────

    def _detect_primary_stack(
        self, players: List[PlayerProjection]
    ) -> Tuple[str, str]:
        """Find the most-represented non-pitcher team in the lineup and
        return (stack_team, opponent_team)."""
        team_counts: Dict[str, int] = {}
        team_opponents: Dict[str, str] = {}

        for p in players:
            if p.position in _PITCHER_POSITIONS:
                continue
            team_counts[p.team] = team_counts.get(p.team, 0) + 1
            if p.opponent:
                team_opponents[p.team] = p.opponent

        if not team_counts:
            return ("", "")

        stack_team = max(team_counts, key=team_counts.get)
        opponent = team_opponents.get(stack_team, "")
        return (stack_team, opponent)

    def _score_bringback(self, p: PlayerProjection) -> float:
        """Compute a bring-back desirability score for a single player.

        Weights:
          - 50% ceiling (high upside is the whole point)
          - 30% projected DK points
          - 20% value (pts per $1k salary)
        """
        ceiling_score = p.ceiling if p.ceiling > 0 else p.dk_points * 1.3
        value_score = p.value if p.value > 0 else 0.0

        score = (
            0.50 * ceiling_score
            + 0.30 * p.dk_points
            + 0.20 * value_score
        )
        return score

    @staticmethod
    def _result(valid, stack_team, opponent, names, message) -> dict:
        return {
            "valid": valid,
            "primary_stack_team": stack_team,
            "opponent": opponent,
            "bringback_players": names,
            "count": len(names),
            "message": message,
        }
