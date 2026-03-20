"""
STACKSNIPER MLB — DraftKings Showdown (Single Game) Optimizer
Captain + 5 FLEX from the same game. Captain gets 1.5× scoring.
"""
from __future__ import annotations
import numpy as np
from typing import List
from sports.mlb.data.models import PlayerProjection
from sports.mlb.utils.logger import get_logger

log = get_logger("ShowdownOptimizer")

try:
    import pulp
    HAS_PULP = True
except ImportError:
    HAS_PULP = False

SHOWDOWN_SALARY_CAP = 50000
SHOWDOWN_ROSTER_SIZE = 6  # 1 CPT + 5 FLEX
CAPTAIN_MULTIPLIER = 1.5


class ShowdownOptimizer:
    """DraftKings Showdown single-game optimizer."""

    def __init__(self, salary_cap: int = SHOWDOWN_SALARY_CAP):
        self.salary_cap = salary_cap

    def optimize(self, players: List[PlayerProjection],
                 game_pk: int = None,
                 num_lineups: int = 20,
                 max_exposure: float = 0.8) -> List[dict]:
        """Generate Showdown lineups for a single game."""
        # Filter to single game if specified
        if game_pk:
            game_players = [p for p in players if getattr(p, 'game_pk', 0) == game_pk]
        else:
            # Use the game with the most players / highest implied total
            games = {}
            for p in players:
                gk = f"{p.team}_{p.opponent}"
                games.setdefault(gk, []).append(p)
            if not games:
                return []
            best_game = max(games.values(), key=lambda ps: sum(p.dk_points for p in ps))
            game_players = best_game

        if len(game_players) < SHOWDOWN_ROSTER_SIZE:
            log.warning(f"Not enough players for Showdown ({len(game_players)})")
            return []

        if HAS_PULP:
            return self._optimize_pulp(game_players, num_lineups, max_exposure)
        return self._optimize_greedy(game_players, num_lineups, max_exposure)

    def _optimize_pulp(self, players, num_lineups, max_exposure):
        lineups = []
        exposure = {p.player_id: 0 for p in players}
        max_per = max(1, int(num_lineups * max_exposure))

        for attempt in range(num_lineups * 4):
            if len(lineups) >= num_lineups:
                break
            try:
                prob = pulp.LpProblem(f"Showdown_{attempt}", pulp.LpMaximize)

                # Variables: captain selection and flex selection
                cpt_vars = {p.player_id: pulp.LpVariable(f"cpt_{p.player_id}", cat="Binary") for p in players}
                flex_vars = {p.player_id: pulp.LpVariable(f"flex_{p.player_id}", cat="Binary") for p in players}

                # Objective: maximize points (captain gets 1.5x)
                # Use ceiling-weighted for captain to pick high-upside players
                noise = {p.player_id: np.random.normal(0, p.dk_points * 0.1) for p in players}
                prob += pulp.lpSum(
                    (p.ceiling * CAPTAIN_MULTIPLIER + noise[p.player_id]) * cpt_vars[p.player_id]
                    + (p.dk_points + noise[p.player_id] * 0.5) * flex_vars[p.player_id]
                    for p in players
                )

                # Exactly 1 captain
                prob += pulp.lpSum(cpt_vars[p.player_id] for p in players) == 1

                # Exactly 5 flex
                prob += pulp.lpSum(flex_vars[p.player_id] for p in players) == 5

                # A player can only be captain OR flex (not both)
                for p in players:
                    prob += cpt_vars[p.player_id] + flex_vars[p.player_id] <= 1

                # Salary constraint (captain salary stays the same in DK Showdown)
                prob += pulp.lpSum(
                    p.salary * (cpt_vars[p.player_id] + flex_vars[p.player_id])
                    for p in players
                ) <= self.salary_cap

                # Exposure limits
                for p in players:
                    if exposure.get(p.player_id, 0) >= max_per:
                        prob += cpt_vars[p.player_id] == 0
                        prob += flex_vars[p.player_id] == 0

                prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=5))
                if prob.status != 1:
                    continue

                captain = None
                flex = []
                for p in players:
                    if cpt_vars[p.player_id].varValue and cpt_vars[p.player_id].varValue > 0.5:
                        captain = p
                    elif flex_vars[p.player_id].varValue and flex_vars[p.player_id].varValue > 0.5:
                        flex.append(p)

                if not captain or len(flex) != 5:
                    continue

                all_players = [captain] + flex
                lineup_ids = tuple(sorted((p.player_id, p == captain) for p in all_players))
                if any(l.get("_ids") == lineup_ids for l in lineups):
                    continue

                total_salary = sum(p.salary for p in all_players)
                cpt_pts = captain.dk_points * CAPTAIN_MULTIPLIER
                flex_pts = sum(p.dk_points for p in flex)
                cpt_ceil = captain.ceiling * CAPTAIN_MULTIPLIER
                flex_ceil = sum(p.ceiling for p in flex)

                lineups.append({
                    "captain": {
                        "name": captain.name, "team": captain.team,
                        "position": captain.position, "salary": captain.salary,
                        "dk_points": round(cpt_pts, 2),
                    },
                    "flex": [
                        {"name": p.name, "team": p.team, "position": p.position,
                         "salary": p.salary, "dk_points": round(p.dk_points, 2)}
                        for p in flex
                    ],
                    "players": all_players,
                    "salary": total_salary,
                    "salary_remaining": self.salary_cap - total_salary,
                    "projected_points": round(cpt_pts + flex_pts, 2),
                    "ceiling": round(cpt_ceil + flex_ceil, 2),
                    "contest_type": "showdown",
                    "_ids": lineup_ids,
                })
                for p in all_players:
                    exposure[p.player_id] = exposure.get(p.player_id, 0) + 1

            except Exception as e:
                log.warning(f"Showdown PuLP error: {e}")
                continue

        # Clean internal keys
        for lu in lineups:
            lu.pop("_ids", None)

        lineups.sort(key=lambda l: l["projected_points"], reverse=True)
        log.info(f"Generated {len(lineups)} Showdown lineups")
        return lineups[:num_lineups]

    def _optimize_greedy(self, players, num_lineups, max_exposure):
        """Greedy fallback for Showdown."""
        lineups = []
        exposure = {p.player_id: 0 for p in players}
        max_per = max(1, int(num_lineups * max_exposure))

        for _ in range(num_lineups * 5):
            if len(lineups) >= num_lineups:
                break

            # Pick captain: weight by ceiling
            cpt_cands = [p for p in players if exposure.get(p.player_id, 0) < max_per]
            if len(cpt_cands) < SHOWDOWN_ROSTER_SIZE:
                break
            ceil_weights = np.array([max(0.1, p.ceiling) for p in cpt_cands])
            ceil_weights = ceil_weights * np.random.exponential(1.0, len(ceil_weights))
            ceil_weights /= ceil_weights.sum()
            captain = cpt_cands[np.random.choice(len(cpt_cands), p=ceil_weights)]

            # Pick 5 flex from remaining
            flex_cands = [p for p in cpt_cands if p.player_id != captain.player_id
                          and sum(p2.salary for p2 in [captain]) + p.salary <= self.salary_cap]
            if len(flex_cands) < 5:
                continue

            flex_weights = np.array([max(0.1, p.dk_points) for p in flex_cands])
            flex_weights = flex_weights * np.random.exponential(1.0, len(flex_weights))
            flex_weights /= flex_weights.sum()

            try:
                flex_idx = np.random.choice(len(flex_cands), size=5, replace=False, p=flex_weights)
            except ValueError:
                flex_idx = np.random.choice(len(flex_cands), size=5, replace=False)
            flex = [flex_cands[i] for i in flex_idx]

            all_p = [captain] + flex
            total_sal = sum(p.salary for p in all_p)
            if total_sal > self.salary_cap:
                continue

            cpt_pts = captain.dk_points * CAPTAIN_MULTIPLIER
            lineups.append({
                "captain": {"name": captain.name, "team": captain.team,
                            "position": captain.position, "salary": captain.salary,
                            "dk_points": round(cpt_pts, 2)},
                "flex": [{"name": p.name, "team": p.team, "position": p.position,
                          "salary": p.salary, "dk_points": round(p.dk_points, 2)} for p in flex],
                "players": all_p,
                "salary": total_sal,
                "salary_remaining": self.salary_cap - total_sal,
                "projected_points": round(cpt_pts + sum(p.dk_points for p in flex), 2),
                "ceiling": round(captain.ceiling * CAPTAIN_MULTIPLIER + sum(p.ceiling for p in flex), 2),
                "contest_type": "showdown",
            })
            for p in all_p:
                exposure[p.player_id] = exposure.get(p.player_id, 0) + 1

        lineups.sort(key=lambda l: l["projected_points"], reverse=True)
        return lineups[:num_lineups]
