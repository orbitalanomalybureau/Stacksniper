"""DFS lineup optimizer using linear programming (PuLP)."""
from __future__ import annotations

import csv
import io
import logging
from typing import Dict, List, Optional

from pulp import LpMaximize, LpProblem, LpVariable, lpSum

# Try HiGHS Python API (ARM-compatible), fall back to CBC
try:
    from pulp import HiGHS as _SOLVER_CLS
    _SOLVER = _SOLVER_CLS(msg=0)
except Exception:
    from pulp import PULP_CBC_CMD as _SOLVER_CLS
    _SOLVER = _SOLVER_CLS(msg=0)

logger = logging.getLogger(__name__)

# Platform configurations
PLATFORMS = {
    "draftkings": {
        "salary_cap": 50000,
        "roster": {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "FLEX": 1, "DST": 1},
        "roster_size": 9,
        "flex_positions": ["RB", "WR", "TE"],
        "csv_header": ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST"],
    },
    "fanduel": {
        "salary_cap": 60000,
        "roster": {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "K": 1, "DST": 1},
        "roster_size": 9,
        "flex_positions": [],
        "csv_header": ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "K", "D"],
    },
}


class LineupOptimizer:
    def __init__(self, platform: str = "draftkings", contest_type: str = "gpp"):
        self.platform = platform.lower()
        self.contest_type = contest_type.lower()
        self.config = PLATFORMS.get(self.platform, PLATFORMS["draftkings"])

    def optimize(
        self,
        players: List[Dict],
        num_lineups: int = 1,
        salary_cap: Optional[int] = None,
        locked_ids: Optional[List[str]] = None,
        excluded_ids: Optional[List[str]] = None,
        max_per_team: int = 4,
    ) -> List[Dict]:
        """Generate optimal lineups.

        Returns list of lineup dicts with players, total_salary, total_projected.
        """
        cap = salary_cap or self.config["salary_cap"]
        locked = set(locked_ids or [])
        excluded = set(excluded_ids or [])

        # Filter excluded
        pool = [p for p in players if p["id"] not in excluded]

        # Filter to only positions in the roster (+ flex-eligible)
        allowed_positions = set(self.config["roster"].keys()) - {"FLEX"}
        allowed_positions |= set(self.config["flex_positions"])
        pool = [p for p in pool if p.get("position") in allowed_positions]

        # Weight players based on contest type
        weighted = self._apply_contest_weights(pool)

        lineups = []
        for _ in range(num_lineups):
            lineup = self._solve_single(
                weighted, cap, lineups, locked, max_per_team
            )
            if lineup:
                lineups.append(lineup)
            else:
                break

        return lineups

    def _apply_contest_weights(self, players: List[Dict]) -> List[Dict]:
        """Adjust effective score based on contest type."""
        weighted = []
        for p in players:
            w = dict(p)
            proj = p.get("projected_points", 0)
            ceil = p.get("ceiling", proj * 1.3)
            floor = p.get("floor", proj * 0.7)
            ownership = p.get("ownership", 10)

            if self.contest_type == "gpp":
                # GPP: weight toward ceiling, penalise high ownership
                own_penalty = max(0.8, 1.0 - (ownership / 100) * 0.3)
                w["score"] = (proj * 0.5 + ceil * 0.5) * own_penalty
            elif self.contest_type == "cash":
                # Cash: weight toward floor/consistency
                w["score"] = proj * 0.4 + floor * 0.6
            else:
                w["score"] = proj

            weighted.append(w)
        return weighted

    def _solve_single(
        self,
        players: List[Dict],
        salary_cap: int,
        existing_lineups: List[Dict],
        locked_ids: set,
        max_per_team: int,
    ) -> Optional[Dict]:
        """Solve single lineup optimisation problem."""
        prob = LpProblem("DFS_Lineup", LpMaximize)
        pvars = {
            p["id"]: LpVariable(f"p_{p['id'][:8]}", cat="Binary")
            for p in players
        }

        # Objective: maximise weighted score
        prob += lpSum(pvars[p["id"]] * p["score"] for p in players)

        # Salary constraint
        prob += (
            lpSum(pvars[p["id"]] * p.get("salary", 5000) for p in players)
            <= salary_cap
        )

        # Roster size
        roster_size = self.config["roster_size"]
        prob += lpSum(pvars.values()) == roster_size

        # Position constraints
        roster = self.config["roster"]
        flex_positions = self.config["flex_positions"]

        for pos, limit in roster.items():
            if pos == "FLEX":
                continue
            pos_players = [p for p in players if p["position"] == pos]
            if flex_positions and pos in flex_positions:
                # Allow up to limit+1 for flex-eligible positions
                prob += lpSum(pvars[p["id"]] for p in pos_players) >= limit
                prob += lpSum(pvars[p["id"]] for p in pos_players) <= limit + 1
            else:
                prob += lpSum(pvars[p["id"]] for p in pos_players) == limit

        # Max players per team
        teams = set(p["team"] for p in players)
        for team in teams:
            team_players = [p for p in players if p["team"] == team]
            prob += lpSum(pvars[p["id"]] for p in team_players) <= max_per_team

        # Locked players must be included
        for pid in locked_ids:
            if pid in pvars:
                prob += pvars[pid] == 1

        # Diversity: overlap at most 6 with any existing lineup
        for existing in existing_lineups:
            existing_ids = {p["id"] for p in existing["players"]}
            prob += (
                lpSum(pvars[pid] for pid in existing_ids if pid in pvars)
                <= roster_size - 3
            )

        prob.solve(_SOLVER)

        if prob.status != 1:
            return None

        selected = [p for p in players if (pvars[p["id"]].varValue or 0) >= 0.5]
        total_salary = sum(p.get("salary", 5000) for p in selected)
        total_proj = sum(p.get("projected_points", 0) for p in selected)

        return {
            "players": selected,
            "total_salary": total_salary,
            "total_projected": round(total_proj, 1),
        }

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def export_csv(self, lineups: List[Dict]) -> str:
        """Export lineups as CSV string for DK/FD upload."""
        output = io.StringIO()
        header = self.config["csv_header"]
        writer = csv.writer(output)
        writer.writerow(header)

        for lineup in lineups:
            row = self._lineup_to_csv_row(lineup, header)
            writer.writerow(row)

        return output.getvalue()

    def _lineup_to_csv_row(self, lineup: Dict, header: List[str]) -> List[str]:
        """Order players by CSV header slot order."""
        players = list(lineup["players"])
        row = []
        used = set()

        for slot in header:
            filled = False
            # FLEX slot: pick remaining RB/WR/TE
            if slot == "FLEX":
                for p in players:
                    if id(p) not in used and p["position"] in ["RB", "WR", "TE"]:
                        row.append(self._player_csv_id(p))
                        used.add(id(p))
                        filled = True
                        break
            elif slot == "D":
                # FanDuel uses "D" for DST
                for p in players:
                    if id(p) not in used and p["position"] == "DST":
                        row.append(self._player_csv_id(p))
                        used.add(id(p))
                        filled = True
                        break
            else:
                for p in players:
                    if id(p) not in used and p["position"] == slot:
                        row.append(self._player_csv_id(p))
                        used.add(id(p))
                        filled = True
                        break

            if not filled:
                row.append("")

        return row

    @staticmethod
    def _player_csv_id(p: Dict) -> str:
        """Format player for CSV (name or external ID)."""
        return p.get("external_id", p.get("name", ""))
