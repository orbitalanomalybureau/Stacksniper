"""
STACKSNIPER MLB — DraftKings Lineup Optimizer (PuLP LP Solver)
Uses integer linear programming for mathematically optimal lineups.
"""
from __future__ import annotations
import numpy as np
from typing import List, Dict, Optional
from sports.mlb.config.settings import DK_SALARY_CAP, DK_ROSTER_SLOTS
from sports.mlb.config.dk_scoring import POSITION_MAP
from sports.mlb.data.models import PlayerProjection
from sports.mlb.optimizer.gto_leverage import GTOLeverageOptimizer
from sports.mlb.utils.logger import get_logger
from sports.mlb.optimizer.slate_manager import SlateManager
from sports.mlb.optimizer.bringback import BringBackManager

log = get_logger("Optimizer")

# Module-level singletons for slate and bringback management
_slate_manager = SlateManager()
_bringback_manager = BringBackManager()

try:
    import pulp
    HAS_PULP = True
except ImportError:
    HAS_PULP = False
    log.warning("PuLP not installed — falling back to greedy optimizer")


class DKOptimizer:
    """
    DraftKings MLB lineup optimizer using PuLP integer linear programming.
    Falls back to greedy approach if PuLP is not available.
    """

    def __init__(self, salary_cap: int = DK_SALARY_CAP):
        self.salary_cap = salary_cap
        self.roster_slots = DK_ROSTER_SLOTS  # ["P", "P", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF"]

    def optimize(self, players: List[PlayerProjection],
                 num_lineups: int = 20,
                 max_exposure: float = 0.6,
                 min_salary: int = None,
                 contest_type: str = "gpp",
                 slate_type: Optional[str] = None,
                 game_times: Optional[Dict[int, str]] = None,
                 require_bringback: bool = False,
                 leverage_mode: bool = False,
                 leverage_aggressiveness: float = 0.5) -> List[dict]:
        """Generate optimal lineups.

        Args:
            slate_type:        If set, filter players to the given slate
                               ('main', 'early', 'night', 'turbo') before
                               optimising.  Requires *game_times*.
            game_times:        Mapping of game_pk -> UTC datetime string.
                               Required when *slate_type* is not None.
            require_bringback: If True, every lineup must contain at least
                               one hitter from the opponent of the primary
                               stack (bring-back rule).  Only enforced in
                               the PuLP path.
            leverage_mode:     When True, applies GTO leverage adjustments
                               that overweight low-owned high-ceiling players
                               and fade chalk.  Only active for GPP contests.
            leverage_aggressiveness:
                               0.0 = pure projection, 1.0 = maximum contrarian.
                               Only used when *leverage_mode* is True.
        """
        if not players:
            return []

        # Phase 3.6 — slate filtering
        if slate_type and slate_type != "main" and game_times:
            players = _slate_manager.filter_by_slate(players, slate_type, game_times)
            if len(players) < 10:
                log.warning(f"Slate '{slate_type}' has only {len(players)} players — too few to optimise")
                return []

        # Handle zero-salary players
        has_salaries = any(p.salary > 0 for p in players)
        if not has_salaries:
            min_salary = 0
        else:
            min_salary = min_salary or int(self.salary_cap * 0.70)

        # Phase 3.5 — GTO Leverage Mode
        leverage_values: Optional[Dict[int, float]] = None
        if leverage_mode and contest_type == "gpp":
            gto = GTOLeverageOptimizer(aggressiveness=leverage_aggressiveness)
            leverage_values = gto.apply_leverage(players)
            log.info("GTO leverage mode active — adjusted player values for optimizer")

        if HAS_PULP and len(players) >= 10:
            lineups = self._optimize_pulp(players, num_lineups, max_exposure,
                                          min_salary, contest_type, require_bringback,
                                          leverage_values)
            if lineups:
                return lineups
            # PuLP failed (solver binary issue or infeasible) — fall through to greedy
            log.warning("PuLP returned 0 lineups, falling back to greedy optimizer")

        return self._optimize_greedy(players, num_lineups, max_exposure,
                                     min_salary, leverage_values)

    def _optimize_pulp(self, players: List[PlayerProjection],
                        num_lineups: int, max_exposure: float,
                        min_salary: int, contest_type: str,
                        require_bringback: bool = False,
                        leverage_values: Optional[Dict[int, float]] = None) -> List[dict]:
        """Generate lineups using PuLP integer linear programming."""
        lineups = []
        exposure_count = {p.player_id: 0 for p in players}
        max_per_player = max(1, int(num_lineups * max_exposure))

        # Position eligibility lookup (v3: check all positions in multi-position list)
        player_positions = {}
        for p in players:
            eligible_slots = set()
            # Collect all positions to check: primary position + multi-position list
            all_positions = {p.position}
            if hasattr(p, 'positions') and p.positions:
                all_positions.update(p.positions)
            for dk_slot, positions in POSITION_MAP.items():
                if any(pos in positions for pos in all_positions):
                    eligible_slots.add(dk_slot)
            player_positions[p.player_id] = eligible_slots

        # Count required slots per position
        slot_counts = {}
        for slot in self.roster_slots:
            slot_counts[slot] = slot_counts.get(slot, 0) + 1

        for lineup_num in range(num_lineups * 3):
            if len(lineups) >= num_lineups:
                break

            try:
                prob = pulp.LpProblem(f"DK_Lineup_{lineup_num}", pulp.LpMaximize)

                # Decision variables: 1 if player is in lineup, 0 otherwise
                player_vars = {}
                for p in players:
                    player_vars[p.player_id] = pulp.LpVariable(
                        f"p_{p.player_id}", cat="Binary"
                    )

                # Objective: maximize projected points with noise for diversity
                # Phase 3.5: When leverage_values are provided, blend them
                # into the objective to tilt toward GTO-optimal selections.
                noise_scale = 0.15 if contest_type == "gpp" else 0.05
                obj_values = {}
                for p in players:
                    if leverage_values and p.player_id in leverage_values:
                        # Use leverage-adjusted value as the base
                        base_val = leverage_values[p.player_id]
                    elif contest_type == "gpp":
                        base_val = p.dk_points * 0.6 + p.ceiling * 0.4
                    elif contest_type == "cash":
                        base_val = p.dk_points * 0.7 + p.floor * 0.3
                    else:
                        base_val = p.dk_points

                    noise = np.random.normal(0, abs(base_val) * noise_scale)
                    obj_values[p.player_id] = base_val + noise

                prob += pulp.lpSum(
                    obj_values[p.player_id] * player_vars[p.player_id]
                    for p in players
                )

                # Constraint: total roster size = 10
                prob += pulp.lpSum(player_vars[p.player_id] for p in players) == 10

                # Constraint: salary cap
                prob += pulp.lpSum(
                    p.salary * player_vars[p.player_id] for p in players
                ) <= self.salary_cap

                # Constraint: minimum salary
                prob += pulp.lpSum(
                    p.salary * player_vars[p.player_id] for p in players
                ) >= min_salary

                # Constraint: position requirements
                for slot, count in slot_counts.items():
                    eligible = [p for p in players if slot in player_positions.get(p.player_id, set())]
                    prob += pulp.lpSum(
                        player_vars[p.player_id] for p in eligible
                    ) >= count

                # Constraint: exposure limits
                for p in players:
                    if exposure_count.get(p.player_id, 0) >= max_per_player:
                        prob += player_vars[p.player_id] == 0

                # Constraint: at least 2 different games
                # (We ensure this by requiring players from at least 2 game groups)
                game_groups = {}
                for p in players:
                    gk = f"{p.team}_{p.opponent}"
                    game_groups.setdefault(gk, []).append(p)

                if len(game_groups) >= 2:
                    game_vars = {}
                    for gk, gplayers in game_groups.items():
                        gv = pulp.LpVariable(f"game_{gk}", cat="Binary")
                        game_vars[gk] = gv
                        # Link: if any player from this game is selected, game var = 1
                        prob += pulp.lpSum(player_vars[p.player_id] for p in gplayers) >= gv
                        prob += pulp.lpSum(player_vars[p.player_id] for p in gplayers) <= 10 * gv
                    prob += pulp.lpSum(game_vars.values()) >= 2

                # Phase 3.7 — bring-back constraint
                if require_bringback:
                    _tc: Dict[str, int] = {}
                    _to: Dict[str, str] = {}
                    for p in players:
                        if p.position not in ("SP", "RP", "P"):
                            _tc[p.team] = _tc.get(p.team, 0) + 1
                            if p.opponent:
                                _to[p.team] = p.opponent
                    if _tc:
                        _top = max(_tc, key=_tc.get)
                        _opp = _to.get(_top, "")
                        if _opp:
                            bb_cst = _bringback_manager.build_bringback_constraint(
                                players, player_vars, _top, _opp, min_bringback=1
                            )
                            if bb_cst is not None:
                                prob += bb_cst

                # Solve
                prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=5))

                if prob.status != 1:
                    continue

                # Extract lineup
                selected = [p for p in players if player_vars[p.player_id].varValue and player_vars[p.player_id].varValue > 0.5]

                if len(selected) != 10:
                    continue

                # Check uniqueness
                lineup_ids = tuple(sorted(p.player_id for p in selected))
                if any(tuple(sorted(p.player_id for p in l["players"])) == lineup_ids for l in lineups):
                    continue

                total_salary = sum(p.salary for p in selected)
                lineup = {
                    "players": selected,
                    "salary": total_salary,
                    "salary_remaining": self.salary_cap - total_salary,
                    "projected_points": round(sum(p.dk_points for p in selected), 2),
                    "ceiling": round(sum(p.ceiling for p in selected), 2),
                    "floor": round(sum(p.floor for p in selected), 2),
                }

                lineups.append(lineup)
                for p in selected:
                    exposure_count[p.player_id] = exposure_count.get(p.player_id, 0) + 1

            except Exception as e:
                log.warning(f"PuLP solve error: {e}")
                continue

        lineups.sort(key=lambda l: l["projected_points"], reverse=True)
        log.info(f"Generated {len(lineups)} optimal lineups (PuLP)")
        return lineups[:num_lineups]

    def _optimize_greedy(self, players: List[PlayerProjection],
                          num_lineups: int, max_exposure: float,
                          min_salary: int,
                          leverage_values: Optional[Dict[int, float]] = None) -> List[dict]:
        """Fallback greedy optimizer (original v1 approach)."""
        by_position = self._group_by_position(players)
        lineups = []
        exposure_count = {p.player_id: 0 for p in players}
        max_per_player = max(1, int(num_lineups * max_exposure))

        for i in range(num_lineups * 5):
            if len(lineups) >= num_lineups:
                break
            lineup = self._build_greedy_lineup(by_position, exposure_count,
                                                max_per_player, min_salary,
                                                leverage_values)
            if lineup and self._is_valid_lineup(lineup):
                lineup_ids = tuple(sorted(p.player_id for p in lineup["players"]))
                if not any(tuple(sorted(p.player_id for p in l["players"])) == lineup_ids for l in lineups):
                    lineups.append(lineup)
                    for p in lineup["players"]:
                        exposure_count[p.player_id] = exposure_count.get(p.player_id, 0) + 1

        lineups.sort(key=lambda l: l["projected_points"], reverse=True)
        log.info(f"Generated {len(lineups)} lineups (greedy)")
        return lineups[:num_lineups]

    def _group_by_position(self, players: List[PlayerProjection]) -> Dict[str, list]:
        groups = {slot: [] for slot in set(self.roster_slots)}
        for player in players:
            if player.salary <= 0:
                continue
            # v3: check all positions in multi-position list
            all_positions = {player.position}
            if hasattr(player, 'positions') and player.positions:
                all_positions.update(player.positions)
            for dk_slot, eligible_positions in POSITION_MAP.items():
                if any(pos in eligible_positions for pos in all_positions):
                    groups.setdefault(dk_slot, []).append(player)
        return groups

    def _build_greedy_lineup(self, by_position, exposure, max_per, min_salary,
                              leverage_values=None):
        lineup = []
        used_ids = set()
        total_salary = 0
        slots_remaining = list(self.roster_slots)
        np.random.shuffle(slots_remaining)

        for slot in slots_remaining:
            candidates = [
                p for p in by_position.get(slot, [])
                if p.player_id not in used_ids
                and exposure.get(p.player_id, 0) < max_per
                and total_salary + p.salary <= self.salary_cap
            ]
            if not candidates:
                return None

            # Phase 3.5: use leverage-adjusted values when available
            if leverage_values:
                weights = np.array([max(0.1, leverage_values.get(p.player_id, p.dk_points))
                                    for p in candidates])
            else:
                weights = np.array([max(0.1, p.dk_points) for p in candidates])
            noise = np.random.exponential(1.0, len(weights))
            weights = weights * noise
            weights = weights / weights.sum()

            try:
                idx = np.random.choice(len(candidates), p=weights)
            except ValueError:
                idx = 0

            selected = candidates[idx]
            lineup.append(selected)
            used_ids.add(selected.player_id)
            total_salary += selected.salary

        if total_salary < min_salary or len(lineup) != len(self.roster_slots):
            return None

        return {
            "players": lineup,
            "salary": total_salary,
            "salary_remaining": self.salary_cap - total_salary,
            "projected_points": round(sum(p.dk_points for p in lineup), 2),
            "ceiling": round(sum(p.ceiling for p in lineup), 2),
            "floor": round(sum(p.floor for p in lineup), 2),
        }

    def _is_valid_lineup(self, lineup: dict) -> bool:
        players = lineup["players"]
        if len(players) != len(self.roster_slots):
            return False
        if lineup["salary"] > self.salary_cap:
            return False
        games = set()
        for p in players:
            games.add(f"{p.team}_{p.opponent}")
        if len(games) < 2:
            return False
        return True

    def find_stacks(self, players: List[PlayerProjection],
                     min_stack_size: int = 3,
                     max_stack_size: int = 5) -> list:
        """Identify high-value team stacks."""
        from sports.mlb.agents.agent_pool import agent_pool

        by_team = {}
        for p in players:
            if p.position not in ("SP", "RP", "P"):
                by_team.setdefault(p.team, []).append(p)

        stacks = []
        for team, team_players in by_team.items():
            team_players.sort(key=lambda p: p.dk_points, reverse=True)
            for size in range(min_stack_size, min(max_stack_size + 1, len(team_players) + 1)):
                stack_players = team_players[:size]
                total_pts = sum(p.dk_points for p in stack_players)
                total_salary = sum(p.salary for p in stack_players)

                stack_context = {
                    "stack_players": [
                        {"team": p.team, "lineup_position": i + 1}
                        for i, p in enumerate(stack_players)
                    ]
                }
                corr_analysis = agent_pool.get_stack_analysis(stack_context)

                stacks.append({
                    "team": team,
                    "players": [
                        {"name": p.name, "position": p.position,
                         "dk_pts": p.dk_points, "salary": p.salary}
                        for p in stack_players
                    ],
                    "size": size,
                    "total_points": round(total_pts, 2),
                    "total_salary": total_salary,
                    "avg_points": round(total_pts / size, 2),
                    "stack_quality": corr_analysis.projection.get("stack_quality", 0),
                    "opponent": stack_players[0].opponent if stack_players else "",
                })

        stacks.sort(key=lambda s: s["total_points"] * (1 + s["stack_quality"] * 0.2), reverse=True)
        return stacks[:30]
