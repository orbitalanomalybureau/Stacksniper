"""
STACKSNIPER MLB — GTO Leverage Mode (Phase 3.5)

Adjusts player values based on projected ownership to find +EV leverage spots.
Overweights low-owned, high-ceiling players; penalizes over-owned chalk.

Key formula:
    leverage_score = ceiling / projected_ownership

Integration:
    Called by DK/FD optimizers when ``leverage_mode=True``.
"""
from __future__ import annotations
import numpy as np
from typing import List, Dict, Optional
from sports.mlb.data.models import PlayerProjection
from sports.mlb.utils.logger import get_logger

log = get_logger("GTOLeverage")


class GTOLeverageOptimizer:
    """
    Applies Game-Theory-Optimal leverage adjustments to player values.

    The core idea: in large-field GPPs the optimal strategy is to overweight
    players whose ceiling-per-ownership-point is high (low-owned upside)
    and underweight "chalk" whose ownership exceeds their edge.

    Parameters
    ----------
    aggressiveness : float
        0.0 = pure projection (no leverage applied).
        1.0 = maximum contrarian tilt.
        Default 0.5 is a balanced blend.
    """

    def __init__(self, aggressiveness: float = 0.5):
        self.aggressiveness = max(0.0, min(1.0, aggressiveness))

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def apply_leverage(
        self,
        players: List[PlayerProjection],
        ownership_data: Optional[Dict[int, float]] = None,
        aggressiveness: Optional[float] = None,
    ) -> Dict[int, float]:
        """
        Compute leverage-adjusted values for every player.

        Parameters
        ----------
        players : list[PlayerProjection]
            Player pool with projections and ``ownership_proj`` set.
        ownership_data : dict[player_id, float] | None
            External ownership map.  If *None*, uses each player's
            ``ownership_proj`` attribute (set by the ownership model).
        aggressiveness : float | None
            Override the instance-level aggressiveness for this call.

        Returns
        -------
        dict[int, float]
            Mapping of ``player_id`` -> leverage-adjusted fantasy-point value.
            The optimizer should use these values as the objective instead of
            raw ``dk_points``.
        """
        agg = aggressiveness if aggressiveness is not None else self.aggressiveness

        if not players:
            return {}

        # Build ownership lookup
        own_map = self._build_ownership_map(players, ownership_data)

        # Compute raw leverage scores
        leverage_scores = self._compute_leverage_scores(players, own_map)

        # Anti-correlation guard: dampen extreme all-chalk or all-contrarian
        leverage_scores = self._anti_correlation_adjustment(
            players, leverage_scores, own_map
        )

        # Blend leverage-adjusted values with raw projections
        adjusted: Dict[int, float] = {}
        for p in players:
            raw = p.dk_points
            lev = leverage_scores.get(p.player_id, raw)
            # Linear blend: agg=0 -> pure raw, agg=1 -> pure leverage
            adjusted[p.player_id] = raw * (1 - agg) + lev * agg

        n_boosted = sum(
            1 for p in players if adjusted[p.player_id] > p.dk_points * 1.05
        )
        n_faded = sum(
            1 for p in players if adjusted[p.player_id] < p.dk_points * 0.95
        )
        log.info(
            f"GTO Leverage applied (agg={agg:.2f}): "
            f"{n_boosted} boosted, {n_faded} faded"
        )

        return adjusted

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_ownership_map(
        players: List[PlayerProjection],
        ownership_data: Optional[Dict[int, float]],
    ) -> Dict[int, float]:
        """Resolve ownership from external data or player attributes."""
        if ownership_data:
            return ownership_data
        return {
            p.player_id: max(0.5, p.ownership_proj)
            for p in players
        }

    @staticmethod
    def _compute_leverage_scores(
        players: List[PlayerProjection],
        own_map: Dict[int, float],
    ) -> Dict[int, float]:
        """
        Core leverage formula:
            leverage_score = ceiling / ownership

        Then rescale so the median leverage score roughly equals the median
        raw projection (keeps the optimizer's scale consistent).
        """
        raw_scores: Dict[int, float] = {}
        for p in players:
            own = own_map.get(p.player_id, 5.0)
            ceiling = max(0.1, p.ceiling if p.ceiling > 0 else p.dk_points)
            raw_scores[p.player_id] = ceiling / max(0.5, own)

        # Rescale: match the median of raw dk_points
        if not raw_scores:
            return raw_scores

        dk_vals = [p.dk_points for p in players if p.dk_points > 0]
        lev_vals = list(raw_scores.values())

        if dk_vals and lev_vals:
            median_dk = float(np.median(dk_vals))
            median_lev = float(np.median(lev_vals)) if lev_vals else 1.0
            if median_lev > 0:
                scale = median_dk / median_lev
                raw_scores = {
                    pid: score * scale for pid, score in raw_scores.items()
                }

        return raw_scores

    @staticmethod
    def _anti_correlation_adjustment(
        players: List[PlayerProjection],
        leverage_scores: Dict[int, float],
        own_map: Dict[int, float],
    ) -> Dict[int, float]:
        """
        Prevent lineups that are ALL chalk or ALL contrarian.

        We dampen the most extreme leverage scores toward the mean, so
        the optimizer naturally builds a mix of leverage and projection plays.

        Logic:
        - Players in the top 15% of ownership who also rank top 15% in raw
          projection get a partial boost back (they are chalk *for a reason*).
        - Players in the bottom 15% of ownership with bottom 15% projection
          get dampened (low-owned AND bad is not leverage, it's a trap).
        """
        if len(players) < 5:
            return leverage_scores

        # Sort thresholds
        own_vals = sorted(own_map.values())
        dk_vals = sorted([p.dk_points for p in players])

        high_own_thresh = own_vals[int(len(own_vals) * 0.85)]
        low_own_thresh = own_vals[int(len(own_vals) * 0.15)]
        high_dk_thresh = dk_vals[int(len(dk_vals) * 0.85)]
        low_dk_thresh = dk_vals[int(len(dk_vals) * 0.15)]

        adjusted = dict(leverage_scores)

        for p in players:
            own = own_map.get(p.player_id, 5.0)
            lev = adjusted.get(p.player_id, p.dk_points)

            # High ownership + high projection = justified chalk
            # Give partial credit back (don't fade studs too hard)
            if own >= high_own_thresh and p.dk_points >= high_dk_thresh:
                boost = (p.dk_points - lev) * 0.3  # Recover 30% of the fade
                adjusted[p.player_id] = lev + boost

            # Low ownership + low projection = trap, not leverage
            # Pull toward (lower) raw projection
            if own <= low_own_thresh and p.dk_points <= low_dk_thresh:
                pull = (p.dk_points - lev) * 0.5  # Pull 50% toward raw
                adjusted[p.player_id] = lev + pull

        return adjusted
