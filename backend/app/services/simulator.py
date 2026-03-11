"""Monte Carlo simulator for DFS contest outcomes."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.models.projection import Projection

logger = logging.getLogger(__name__)


# ---- Correlation coefficients ----
CORR_QB_WR_SAME = 0.45     # Same team QB-WR
CORR_QB_TE_SAME = 0.35     # Same team QB-TE
CORR_RB_QB_SAME = 0.12     # Same team RB-QB (game script)
CORR_QB_DST_OPP = -0.30    # Opposing QB-DST
CORR_BRINGBACK_WR = 0.15   # Same game bring-back WR


class Simulator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_simulation(
        self,
        season: int,
        week: int,
        num_sims: int = 10000,
        config: Optional[Dict] = None,
    ) -> Dict:
        """Run full Monte Carlo simulation.

        Returns dict with:
          players: list of player dicts with sim stats
          lineup_scores: array of best-lineup scores per sim
          stacks: top co-occurring player pairs
        """
        config = config or {}
        locked_ids = set(config.get("locked_players", []))
        excluded_ids = set(config.get("excluded_players", []))

        # Load projections + player info
        players, means, std_devs = await self._load_projections(
            season, week, locked_ids, excluded_ids
        )
        if not players:
            return {"players": [], "lineup_scores": [], "stacks": []}

        n = len(players)
        corr = self._build_correlation_matrix(players)

        # Generate correlated samples: (num_sims, n_players)
        sim_matrix = self.correlated_sample(means, std_devs, corr, num_sims)

        # Analyse per-player results
        player_results = self._analyze_players(sim_matrix, players, means)

        # Find top stacks (most frequently co-occurring top performers)
        stacks = self._find_stacks(sim_matrix, players, top_n=10)

        # Distribution of best possible lineup score per sim
        lineup_scores = self._sim_lineup_scores(sim_matrix)

        return {
            "players": player_results,
            "lineup_scores": lineup_scores.tolist(),
            "stacks": stacks,
        }

    # ------------------------------------------------------------------
    # Correlation matrix
    # ------------------------------------------------------------------

    def _build_correlation_matrix(self, players: List[Dict]) -> np.ndarray:
        n = len(players)
        corr = np.eye(n)

        for i in range(n):
            for j in range(i + 1, n):
                rho = self._pair_correlation(players[i], players[j])
                corr[i, j] = rho
                corr[j, i] = rho

        # Ensure positive semi-definite
        eigvals = np.linalg.eigvalsh(corr)
        if eigvals.min() < 0:
            corr += (-eigvals.min() + 1e-6) * np.eye(n)
            # Re-normalise diagonal to 1
            d = np.sqrt(np.diag(corr))
            corr = corr / np.outer(d, d)

        return corr

    @staticmethod
    def _pair_correlation(p1: Dict, p2: Dict) -> float:
        """Return correlation coefficient for a player pair."""
        same_team = p1["team"] == p2["team"]
        # Detect same-game (same opponent or one's team is other's opponent)
        same_game = (
            p1.get("opponent") == p2["team"]
            or p2.get("opponent") == p1["team"]
            or (p1.get("opponent") and p1["opponent"] == p2.get("opponent"))
        )

        pos1, pos2 = p1["position"], p2["position"]

        if same_team:
            pair = frozenset([pos1, pos2])
            if pair == frozenset(["QB", "WR"]):
                return CORR_QB_WR_SAME
            if pair == frozenset(["QB", "TE"]):
                return CORR_QB_TE_SAME
            if pair == frozenset(["QB", "RB"]):
                return CORR_RB_QB_SAME
            if pair == frozenset(["RB", "WR"]):
                return 0.05
            return 0.05  # Mild same-team default

        if same_game:
            # Opposing QB-DST
            if frozenset([pos1, pos2]) == frozenset(["QB", "DST"]):
                return CORR_QB_DST_OPP
            # Bring-back WR
            if "WR" in (pos1, pos2) and "QB" in (pos1, pos2):
                return CORR_BRINGBACK_WR
            return 0.0

        return 0.0

    # ------------------------------------------------------------------
    # Correlated sampling
    # ------------------------------------------------------------------

    @staticmethod
    def correlated_sample(
        means: np.ndarray,
        std_devs: np.ndarray,
        correlation_matrix: np.ndarray,
        n_sims: int,
    ) -> np.ndarray:
        """Generate correlated samples using Cholesky decomposition."""
        cov_matrix = np.outer(std_devs, std_devs) * correlation_matrix
        samples = np.random.multivariate_normal(means, cov_matrix, size=n_sims)
        return np.maximum(samples, 0)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _analyze_players(
        self, sim_matrix: np.ndarray, players: List[Dict], means: np.ndarray
    ) -> List[Dict]:
        """Calculate per-player simulation statistics."""
        results = []
        for i, p in enumerate(players):
            col = sim_matrix[:, i]
            proj = means[i]
            # Boom = exceeds projection by 25%; Bust = below 50% of projection
            # Use std-based alternative if tighter: proj + 1.5*std
            std = float(np.std(col))
            boom_threshold = min(proj * 1.25, proj + 1.5 * std)
            bust_threshold = max(proj * 0.5, proj - 1.5 * std)

            results.append({
                "player_id": p["player_id"],
                "name": p["name"],
                "position": p["position"],
                "team": p["team"],
                "salary": p["salary"],
                "projected_points": round(float(proj), 1),
                "avg_points": round(float(np.mean(col)), 1),
                "median_points": round(float(np.median(col)), 1),
                "std_dev": round(float(np.std(col)), 2),
                "floor": round(float(np.percentile(col, 10)), 1),
                "ceiling": round(float(np.percentile(col, 90)), 1),
                "percentile_25": round(float(np.percentile(col, 25)), 1),
                "percentile_75": round(float(np.percentile(col, 75)), 1),
                "boom_rate": round(float(np.mean(col >= boom_threshold) * 100), 1),
                "bust_rate": round(float(np.mean(col <= bust_threshold) * 100), 1),
            })
        return results

    def _find_stacks(
        self, sim_matrix: np.ndarray, players: List[Dict], top_n: int = 10
    ) -> List[Dict]:
        """Find most frequently co-occurring top performers."""
        n_sims, n_players = sim_matrix.shape
        if n_players < 2:
            return []

        # For each sim, find the top 5 scorers
        top_k = min(5, n_players)
        top_indices = np.argpartition(sim_matrix, -top_k, axis=1)[:, -top_k:]

        # Count pair co-occurrences
        pair_counts: Dict[Tuple[int, int], int] = {}
        for sim_row in top_indices:
            sorted_row = sorted(sim_row)
            for a_idx in range(len(sorted_row)):
                for b_idx in range(a_idx + 1, len(sorted_row)):
                    pair = (sorted_row[a_idx], sorted_row[b_idx])
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1

        # Top N pairs
        sorted_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

        stacks = []
        for (i, j), count in sorted_pairs:
            stacks.append({
                "player_1": players[i]["name"],
                "player_2": players[j]["name"],
                "team_1": players[i]["team"],
                "team_2": players[j]["team"],
                "frequency": round(count / n_sims * 100, 1),
            })
        return stacks

    def _sim_lineup_scores(self, sim_matrix: np.ndarray) -> np.ndarray:
        """For each sim, sum the top 9 scorers as proxy best lineup score."""
        n_sims, n_players = sim_matrix.shape
        top_k = min(9, n_players)
        # partitioned top-k per row, then sum
        top_indices = np.argpartition(sim_matrix, -top_k, axis=1)[:, -top_k:]
        scores = np.array([
            sim_matrix[i, top_indices[i]].sum() for i in range(n_sims)
        ])
        return scores

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    async def _load_projections(
        self,
        season: int,
        week: int,
        locked_ids: set,
        excluded_ids: set,
    ) -> Tuple[List[Dict], np.ndarray, np.ndarray]:
        """Load players + projections, return (players, means, std_devs)."""
        stmt = (
            select(Player, Projection)
            .join(Projection, Player.id == Projection.player_id)
            .where(Projection.season == season, Projection.week == week)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        players = []
        means_list = []
        std_list = []

        for player, proj in rows:
            if player.id in excluded_ids:
                continue
            if locked_ids and player.id not in locked_ids:
                # If lock list is provided, only include locked players + all others
                # Actually, locked means "must include" — we still include everyone
                pass

            std = proj.std_dev if proj.std_dev and proj.std_dev > 0 else 1.0
            if proj.ceiling and proj.floor:
                std = max((proj.ceiling - proj.floor) / 3.29, 0.5)

            players.append({
                "player_id": player.id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "salary": player.salary or 5000,
                "opponent": getattr(player, "opponent", None),
            })
            means_list.append(proj.projected_points)
            std_list.append(std)

        return players, np.array(means_list), np.array(std_list)
