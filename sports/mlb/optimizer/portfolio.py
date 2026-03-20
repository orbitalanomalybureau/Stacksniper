"""
STACKSNIPER MLB — Multi-Contest Portfolio Optimizer
Generates diversified lineups across different contest types (cash, GPP single, GPP multi).
"""
from typing import List, Dict
from sports.mlb.data.models import PlayerProjection
from sports.mlb.optimizer.dk_optimizer import DKOptimizer
from sports.mlb.utils.logger import get_logger

log = get_logger("Portfolio")


class PortfolioOptimizer:
    """Optimizes lineups across multiple contest types for a complete DFS portfolio."""

    def __init__(self):
        self.dk_optimizer = DKOptimizer()

    def optimize_portfolio(self, players: List[PlayerProjection],
                           contests: List[dict]) -> Dict[str, list]:
        """
        Generate optimal lineups across multiple contest types.

        Args:
            players: List of player projections from simulation
            contests: List of contest configurations, e.g.:
                [
                    {"type": "cash", "entries": 3, "fee": 5},
                    {"type": "gpp_single", "entries": 1, "fee": 20},
                    {"type": "gpp_multi", "entries": 20, "fee": 3},
                ]

        Returns:
            Dict mapping contest type -> list of lineups
        """
        results = {}
        total_lineups = 0

        for contest in contests:
            ctype = contest.get("type", "gpp")
            entries = contest.get("entries", 1)

            log.info(f"Optimizing {entries} lineups for {ctype}")

            if ctype == "cash":
                lineups = self._optimize_cash(players, entries)
            elif ctype == "gpp_single":
                lineups = self._optimize_gpp_single(players, entries)
            elif ctype == "gpp_multi":
                max_entries = contest.get("max_entries", 150)
                lineups = self._optimize_gpp_multi(players, entries, max_entries)
            else:
                lineups = self.dk_optimizer.optimize(players, entries)

            results[ctype] = lineups
            total_lineups += len(lineups)

        log.info(f"Portfolio complete: {total_lineups} total lineups across {len(contests)} contests")

        # Add portfolio summary
        results["_summary"] = self._compute_summary(results, contests)
        return results

    def _optimize_cash(self, players: List[PlayerProjection], entries: int) -> list:
        """Cash games: floor-optimized, low variance, high floor players."""
        # Sort by floor to prioritize consistent performers
        floor_adjusted = []
        for p in players:
            p_copy = PlayerProjection(
                player_id=p.player_id, name=p.name, team=p.team,
                position=p.position, salary=p.salary,
                dk_points=p.dk_points * 0.3 + p.floor * 0.7,  # Weight floor heavily
                ceiling=p.ceiling, floor=p.floor,
                opponent=p.opponent, game_pk=p.game_pk,
            )
            # Copy additional attrs
            for attr in ('positions', 'value', 'median', 'dk_points_std'):
                if hasattr(p, attr):
                    setattr(p_copy, attr, getattr(p, attr))
            floor_adjusted.append(p_copy)

        return self.dk_optimizer.optimize(
            floor_adjusted, entries,
            max_exposure=0.4,
            contest_type="cash",
        )

    def _optimize_gpp_single(self, players: List[PlayerProjection], entries: int) -> list:
        """Single-entry GPP: ceiling-optimized, unique stack focus."""
        ceiling_adjusted = []
        for p in players:
            p_copy = PlayerProjection(
                player_id=p.player_id, name=p.name, team=p.team,
                position=p.position, salary=p.salary,
                dk_points=p.dk_points * 0.4 + p.ceiling * 0.6,  # Weight ceiling heavily
                ceiling=p.ceiling, floor=p.floor,
                opponent=p.opponent, game_pk=p.game_pk,
            )
            for attr in ('positions', 'value', 'median', 'dk_points_std'):
                if hasattr(p, attr):
                    setattr(p_copy, attr, getattr(p, attr))
            ceiling_adjusted.append(p_copy)

        return self.dk_optimizer.optimize(
            ceiling_adjusted, entries,
            max_exposure=1.0,  # Full exposure OK for single entry
            contest_type="gpp",
        )

    def _optimize_gpp_multi(self, players: List[PlayerProjection],
                             entries: int, max_entries: int) -> list:
        """Multi-entry GPP: diversified portfolio with controlled overlap."""
        max_exposure = min(0.6, entries / max_entries + 0.1)
        return self.dk_optimizer.optimize(
            players, entries,
            max_exposure=max_exposure,
            contest_type="gpp",
        )

    def _compute_summary(self, results: dict, contests: list) -> dict:
        """Compute portfolio-level summary statistics."""
        total_investment = sum(
            c.get("fee", 0) * c.get("entries", 0) for c in contests
        )
        total_lineups = sum(
            len(v) for k, v in results.items() if k != "_summary"
        )

        # Compute unique players across all lineups
        all_players = set()
        for ctype, lineups in results.items():
            if ctype == "_summary":
                continue
            for lu in lineups:
                for p in lu.get("players", []):
                    if hasattr(p, "player_id"):
                        all_players.add(p.player_id)

        return {
            "total_lineups": total_lineups,
            "total_investment": total_investment,
            "unique_players": len(all_players),
            "contests": len(contests),
        }
