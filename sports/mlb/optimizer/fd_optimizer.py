"""
STACKSNIPER MLB — FanDuel Lineup Optimizer
Uses PuLP LP solver with FanDuel-specific constraints.
"""
from __future__ import annotations
import numpy as np
from typing import List, Dict, Optional
from sports.mlb.config.fd_scoring import FD_SALARY_CAP, FD_ROSTER_SLOTS, FD_ROSTER_SIZE, FD_POSITION_MAP
from sports.mlb.data.models import PlayerProjection
from sports.mlb.optimizer.gto_leverage import GTOLeverageOptimizer
from sports.mlb.utils.logger import get_logger

log = get_logger("FDOptimizer")

try:
    import pulp
    HAS_PULP = True
except ImportError:
    HAS_PULP = False


class FDOptimizer:
    """FanDuel MLB lineup optimizer."""

    def __init__(self, salary_cap: int = FD_SALARY_CAP):
        self.salary_cap = salary_cap
        self.roster_slots = FD_ROSTER_SLOTS
        self.roster_size = FD_ROSTER_SIZE

    def optimize(self, players: List[PlayerProjection],
                 num_lineups: int = 20,
                 max_exposure: float = 0.6,
                 min_salary: int = None,
                 contest_type: str = "gpp",
                 leverage_mode: bool = False,
                 leverage_aggressiveness: float = 0.5) -> List[dict]:
        """Generate optimal FanDuel lineups.

        Args:
            leverage_mode:     When True, applies GTO leverage adjustments
                               that overweight low-owned high-ceiling players.
                               Only active for GPP contests.
            leverage_aggressiveness:
                               0.0 = pure projection, 1.0 = maximum contrarian.
        """
        min_salary = min_salary or int(self.salary_cap * 0.85)

        # Phase 3.5 — GTO Leverage Mode
        leverage_values: Optional[Dict[int, float]] = None
        if leverage_mode and contest_type == "gpp":
            gto = GTOLeverageOptimizer(aggressiveness=leverage_aggressiveness)
            leverage_values = gto.apply_leverage(players)
            log.info("GTO leverage mode active for FanDuel optimizer")

        if HAS_PULP and len(players) >= self.roster_size:
            return self._optimize_pulp(players, num_lineups, max_exposure,
                                       min_salary, contest_type, leverage_values)
        return self._optimize_greedy(players, num_lineups, max_exposure,
                                     min_salary, leverage_values)

    def _get_eligible_slots(self, player: PlayerProjection) -> set:
        all_positions = {player.position}
        if hasattr(player, 'positions') and player.positions:
            all_positions.update(player.positions)
        eligible = set()
        for slot, positions in FD_POSITION_MAP.items():
            if any(pos in positions for pos in all_positions):
                eligible.add(slot)
        return eligible

    def _optimize_pulp(self, players, num_lineups, max_exposure, min_salary,
                        contest_type, leverage_values=None):
        lineups = []
        exposure_count = {p.player_id: 0 for p in players}
        max_per = max(1, int(num_lineups * max_exposure))

        player_slots = {p.player_id: self._get_eligible_slots(p) for p in players}

        slot_counts = {}
        for slot in self.roster_slots:
            slot_counts[slot] = slot_counts.get(slot, 0) + 1

        for attempt in range(num_lineups * 3):
            if len(lineups) >= num_lineups:
                break
            try:
                prob = pulp.LpProblem(f"FD_Lineup_{attempt}", pulp.LpMaximize)
                pvars = {p.player_id: pulp.LpVariable(f"p_{p.player_id}", cat="Binary") for p in players}

                noise_scale = 0.15 if contest_type == "gpp" else 0.05
                for p in players:
                    # Phase 3.5: use leverage-adjusted values when available
                    if leverage_values and p.player_id in leverage_values:
                        base = leverage_values[p.player_id]
                    elif contest_type == "gpp":
                        base = p.dk_points * 0.6 + p.ceiling * 0.4
                    else:
                        base = p.dk_points * 0.7 + p.floor * 0.3
                    noise = np.random.normal(0, abs(base) * noise_scale)
                    pvars[p.player_id].obj_val = base + noise

                prob += pulp.lpSum(pvars[p.player_id].obj_val * pvars[p.player_id] for p in players)
                prob += pulp.lpSum(pvars[p.player_id] for p in players) == self.roster_size
                prob += pulp.lpSum(p.salary * pvars[p.player_id] for p in players) <= self.salary_cap
                prob += pulp.lpSum(p.salary * pvars[p.player_id] for p in players) >= min_salary

                for slot, count in slot_counts.items():
                    eligible = [p for p in players if slot in player_slots.get(p.player_id, set())]
                    prob += pulp.lpSum(pvars[p.player_id] for p in eligible) >= count

                for p in players:
                    if exposure_count.get(p.player_id, 0) >= max_per:
                        prob += pvars[p.player_id] == 0

                prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=5))
                if prob.status != 1:
                    continue

                selected = [p for p in players if pvars[p.player_id].varValue and pvars[p.player_id].varValue > 0.5]
                if len(selected) != self.roster_size:
                    continue

                lineup_ids = tuple(sorted(p.player_id for p in selected))
                if any(tuple(sorted(p.player_id for p in l["players"])) == lineup_ids for l in lineups):
                    continue

                total_salary = sum(p.salary for p in selected)
                lineups.append({
                    "players": selected,
                    "salary": total_salary,
                    "salary_remaining": self.salary_cap - total_salary,
                    "projected_points": round(sum(p.dk_points for p in selected), 2),
                    "ceiling": round(sum(p.ceiling for p in selected), 2),
                    "floor": round(sum(p.floor for p in selected), 2),
                    "platform": "fanduel",
                })
                for p in selected:
                    exposure_count[p.player_id] = exposure_count.get(p.player_id, 0) + 1

            except Exception as e:
                log.warning(f"FD PuLP error: {e}")
                continue

        lineups.sort(key=lambda l: l["projected_points"], reverse=True)
        log.info(f"Generated {len(lineups)} FanDuel lineups")
        return lineups[:num_lineups]

    def _optimize_greedy(self, players, num_lineups, max_exposure, min_salary,
                          leverage_values=None):
        """Greedy fallback for FanDuel."""
        lineups = []
        exposure_count = {p.player_id: 0 for p in players}
        max_per = max(1, int(num_lineups * max_exposure))

        by_slot = {}
        for slot in set(self.roster_slots):
            by_slot[slot] = [p for p in players if slot in self._get_eligible_slots(p) and p.salary > 0]

        for _ in range(num_lineups * 5):
            if len(lineups) >= num_lineups:
                break
            lineup, used, total_sal = [], set(), 0
            slots = list(self.roster_slots)
            np.random.shuffle(slots)

            ok = True
            for slot in slots:
                cands = [p for p in by_slot.get(slot, [])
                         if p.player_id not in used
                         and exposure_count.get(p.player_id, 0) < max_per
                         and total_sal + p.salary <= self.salary_cap]
                if not cands:
                    ok = False
                    break
                # Phase 3.5: use leverage-adjusted values when available
                if leverage_values:
                    w = np.array([max(0.1, leverage_values.get(p.player_id, p.dk_points))
                                  for p in cands])
                else:
                    w = np.array([max(0.1, p.dk_points) for p in cands])
                w = w * np.random.exponential(1.0, len(w))
                w /= w.sum()
                sel = cands[np.random.choice(len(cands), p=w)]
                lineup.append(sel)
                used.add(sel.player_id)
                total_sal += sel.salary

            if not ok or total_sal < min_salary:
                continue

            lid = tuple(sorted(p.player_id for p in lineup))
            if any(tuple(sorted(p.player_id for p in l["players"])) == lid for l in lineups):
                continue

            lineups.append({
                "players": lineup, "salary": total_sal,
                "salary_remaining": self.salary_cap - total_sal,
                "projected_points": round(sum(p.dk_points for p in lineup), 2),
                "ceiling": round(sum(p.ceiling for p in lineup), 2),
                "floor": round(sum(p.floor for p in lineup), 2),
                "platform": "fanduel",
            })
            for p in lineup:
                exposure_count[p.player_id] = exposure_count.get(p.player_id, 0) + 1

        lineups.sort(key=lambda l: l["projected_points"], reverse=True)
        return lineups[:num_lineups]
