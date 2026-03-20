"""
STACKSNIPER MLB v3.0 — Backtesting Engine
Historical backtest runner: re-run simulations against past results
to measure projection accuracy and calibrate the engine.
"""
from __future__ import annotations
import numpy as np
from datetime import date, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from sports.mlb.utils.logger import get_logger

log = get_logger("Backtester")


@dataclass
class BacktestResult:
    """Result of a single-date backtest."""
    game_date: str
    num_players: int = 0
    num_games: int = 0
    mae: float = 0.0          # Mean absolute error
    rmse: float = 0.0         # Root mean squared error
    correlation: float = 0.0   # Pearson correlation proj vs actual
    hit_rate_10pct: float = 0.0  # % within 10% of actual
    hit_rate_20pct: float = 0.0  # % within 20% of actual
    top10_overlap: float = 0.0   # % of top-10 projected in actual top-10
    ceiling_hit_rate: float = 0.0  # % of players who hit their ceiling (p90+)
    floor_miss_rate: float = 0.0   # % of players who missed their floor
    player_results: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class BacktestSummary:
    """Aggregate results across multiple backtest dates."""
    start_date: str
    end_date: str
    num_dates: int = 0
    total_players: int = 0
    avg_mae: float = 0.0
    avg_rmse: float = 0.0
    avg_correlation: float = 0.0
    avg_hit_rate_10pct: float = 0.0
    avg_hit_rate_20pct: float = 0.0
    avg_top10_overlap: float = 0.0
    by_position: Dict[str, Dict] = field(default_factory=dict)
    by_date: List[BacktestResult] = field(default_factory=list)
    calibration_suggestions: List[str] = field(default_factory=list)


class Backtester:
    """
    Historical backtesting engine.
    Runs the simulation engine on past dates and compares
    projections against actual DraftKings results.
    """

    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            try:
                from sports.mlb.data.database import db
                self._db = db
            except ImportError:
                log.warning("Database module not available")
        return self._db

    def run_backtest(self, start_date: date, end_date: date = None,
                     num_sims: int = 500,
                     skip_no_actuals: bool = True) -> BacktestSummary:
        """Run backtest over a date range."""
        end_date = end_date or start_date
        if end_date < start_date:
            start_date, end_date = end_date, start_date

        log.info(f"▶ Backtesting {start_date} to {end_date} ({num_sims} sims/date)")

        results = []
        current = start_date
        while current <= end_date:
            # Skip off days (future optimization: check schedule)
            try:
                result = self._backtest_single_date(current, num_sims, skip_no_actuals)
                if result and result.num_players > 0:
                    results.append(result)
                    log.info(f"  {current}: MAE={result.mae:.2f}, r={result.correlation:.3f}, "
                             f"n={result.num_players}")
            except Exception as e:
                log.warning(f"  {current}: backtest failed — {e}")

            current += timedelta(days=1)

        summary = self._aggregate_results(results, str(start_date), str(end_date))
        summary.calibration_suggestions = self._generate_calibration_suggestions(summary)

        log.info(f"✅ Backtest complete: {summary.num_dates} dates, "
                 f"MAE={summary.avg_mae:.2f}, r={summary.avg_correlation:.3f}")
        return summary

    def _backtest_single_date(self, game_date: date, num_sims: int,
                               skip_no_actuals: bool) -> Optional[BacktestResult]:
        """Run simulation for one date and compare against actuals."""
        from sports.mlb.simulation.engine import SimulationEngine

        result = BacktestResult(game_date=str(game_date))

        # Run simulation
        engine = SimulationEngine(num_sims=num_sims)
        sim_result = engine.run_full_slate(game_date)

        if not sim_result.player_projections:
            return None

        # Get actual results
        actuals = self._get_actual_results(game_date, sim_result)
        if not actuals and skip_no_actuals:
            return None

        result.num_games = len(sim_result.games)
        projected = []
        actual = []
        player_results = []

        for p in sim_result.player_projections:
            actual_pts = actuals.get(p.player_id, actuals.get(p.name))
            if actual_pts is None:
                continue

            projected.append(p.dk_points)
            actual.append(actual_pts)

            error = p.dk_points - actual_pts
            player_results.append({
                "player_id": p.player_id,
                "name": p.name,
                "team": p.team,
                "position": p.position,
                "projected": round(p.dk_points, 2),
                "actual": round(actual_pts, 2),
                "error": round(error, 2),
                "abs_error": round(abs(error), 2),
                "ceiling": round(p.ceiling, 2),
                "floor": round(p.floor, 2),
                "hit_ceiling": actual_pts >= p.ceiling,
                "missed_floor": actual_pts < p.floor,
            })

        if not projected:
            return None

        projected_arr = np.array(projected)
        actual_arr = np.array(actual)
        n = len(projected_arr)

        result.num_players = n
        result.mae = round(float(np.mean(np.abs(projected_arr - actual_arr))), 2)
        result.rmse = round(float(np.sqrt(np.mean((projected_arr - actual_arr) ** 2))), 2)

        # Correlation
        if np.std(projected_arr) > 0 and np.std(actual_arr) > 0:
            result.correlation = round(float(np.corrcoef(projected_arr, actual_arr)[0, 1]), 3)

        # Hit rates
        if n > 0:
            actual_nz = np.where(actual_arr != 0, actual_arr, 1.0)
            pct_error = np.abs(projected_arr - actual_arr) / actual_nz
            result.hit_rate_10pct = round(float(np.mean(pct_error < 0.10)) * 100, 1)
            result.hit_rate_20pct = round(float(np.mean(pct_error < 0.20)) * 100, 1)

        # Top-10 overlap
        if n >= 10:
            proj_top10 = set(np.argsort(projected_arr)[-10:])
            actual_top10 = set(np.argsort(actual_arr)[-10:])
            result.top10_overlap = round(len(proj_top10 & actual_top10) / 10 * 100, 1)

        # Ceiling/floor rates
        ceil_hits = sum(1 for pr in player_results if pr["hit_ceiling"])
        floor_misses = sum(1 for pr in player_results if pr["missed_floor"])
        result.ceiling_hit_rate = round(ceil_hits / max(1, n) * 100, 1)
        result.floor_miss_rate = round(floor_misses / max(1, n) * 100, 1)

        result.player_results = player_results

        # Save to database if available
        if self.db:
            try:
                self.db.save_backtest_result(game_date, result)
            except Exception as e:
                log.warning(f"Failed to save backtest to DB: {e}")

        return result

    def _get_actual_results(self, game_date: date,
                            sim_result) -> Dict:
        """Fetch actual DK scoring for the date. Returns {player_id: actual_pts}."""
        actuals = {}

        # Try database first
        if self.db:
            try:
                db_actuals = self.db.get_actual_scores(game_date)
                if db_actuals:
                    return db_actuals
            except Exception:
                pass

        # Fall back to computing from boxscores
        try:
            from sports.mlb.data.mlb_api import mlb_api
            from sports.mlb.config.dk_scoring import calculate_hitter_dkfp, calculate_pitcher_dkfp

            for game in sim_result.games:
                try:
                    boxscore = mlb_api.get_boxscore(game.game_pk)
                    if not boxscore:
                        continue

                    for side in ["away", "home"]:
                        team_data = boxscore.get("teams", {}).get(side, {})
                        players_data = team_data.get("players", {})

                        for pid_key, pdata in players_data.items():
                            player_id = int(pid_key.replace("ID", ""))
                            stats_data = pdata.get("stats", {})

                            batting = stats_data.get("batting", {})
                            pitching = stats_data.get("pitching", {})

                            if pitching.get("inningsPitched"):
                                ip_str = pitching.get("inningsPitched", "0.0")
                                try:
                                    ip = float(ip_str)
                                except (ValueError, TypeError):
                                    ip = 0.0

                                pitch_stats = {
                                    "innings_pitched": ip,
                                    "strikeouts": pitching.get("strikeOuts", 0),
                                    "earned_runs": pitching.get("earnedRuns", 0),
                                    "hits_against": pitching.get("hits", 0),
                                    "walks_against": pitching.get("baseOnBalls", 0),
                                    "hbp_against": pitching.get("hitByPitch", 0),
                                    "win": 1 if pitching.get("wins", 0) > 0 else 0,
                                    "complete_game": ip >= 9.0,
                                    "shutout": ip >= 9.0 and pitching.get("earnedRuns", 0) == 0,
                                    "no_hitter": ip >= 9.0 and pitching.get("hits", 0) == 0,
                                }
                                actuals[player_id] = calculate_pitcher_dkfp(pitch_stats)

                            elif batting.get("atBats", 0) > 0 or batting.get("plateAppearances", 0) > 0:
                                hits = batting.get("hits", 0)
                                doubles = batting.get("doubles", 0)
                                triples = batting.get("triples", 0)
                                hr = batting.get("homeRuns", 0)
                                singles = hits - doubles - triples - hr

                                bat_stats = {
                                    "singles": max(0, singles),
                                    "doubles": doubles,
                                    "triples": triples,
                                    "home_runs": hr,
                                    "rbi": batting.get("rbi", 0),
                                    "runs": batting.get("runs", 0),
                                    "walks": batting.get("baseOnBalls", 0),
                                    "hbp": batting.get("hitByPitch", 0),
                                    "stolen_bases": batting.get("stolenBases", 0),
                                    "caught_stealing": batting.get("caughtStealing", 0),
                                }
                                actuals[player_id] = calculate_hitter_dkfp(bat_stats)

                except Exception as e:
                    log.warning(f"Failed to get boxscore for game {game.game_pk}: {e}")

        except Exception as e:
            log.warning(f"Failed to compute actuals: {e}")

        return actuals

    def _aggregate_results(self, results: List[BacktestResult],
                           start_date: str, end_date: str) -> BacktestSummary:
        """Aggregate individual date results into a summary."""
        summary = BacktestSummary(
            start_date=start_date,
            end_date=end_date,
            num_dates=len(results),
            by_date=results,
        )

        if not results:
            return summary

        summary.total_players = sum(r.num_players for r in results)
        summary.avg_mae = round(np.mean([r.mae for r in results]), 2)
        summary.avg_rmse = round(np.mean([r.rmse for r in results]), 2)
        valid_corrs = [r.correlation for r in results if r.correlation != 0]
        summary.avg_correlation = round(np.mean(valid_corrs), 3) if valid_corrs else 0.0
        summary.avg_hit_rate_10pct = round(np.mean([r.hit_rate_10pct for r in results]), 1)
        summary.avg_hit_rate_20pct = round(np.mean([r.hit_rate_20pct for r in results]), 1)
        summary.avg_top10_overlap = round(np.mean([r.top10_overlap for r in results]), 1)

        # Aggregate by position
        pos_data = {}
        for r in results:
            for pr in r.player_results:
                pos = pr["position"]
                if pos in ("SP", "RP"):
                    pos = "P"
                pos_data.setdefault(pos, {"projected": [], "actual": [], "errors": []})
                pos_data[pos]["projected"].append(pr["projected"])
                pos_data[pos]["actual"].append(pr["actual"])
                pos_data[pos]["errors"].append(pr["abs_error"])

        for pos, data in pos_data.items():
            proj_arr = np.array(data["projected"])
            act_arr = np.array(data["actual"])
            n = len(proj_arr)
            corr = 0.0
            if n > 2 and np.std(proj_arr) > 0 and np.std(act_arr) > 0:
                corr = float(np.corrcoef(proj_arr, act_arr)[0, 1])
            summary.by_position[pos] = {
                "count": n,
                "mae": round(float(np.mean(data["errors"])), 2),
                "correlation": round(corr, 3),
                "avg_projected": round(float(np.mean(data["projected"])), 2),
                "avg_actual": round(float(np.mean(data["actual"])), 2),
                "bias": round(float(np.mean(proj_arr - act_arr)), 2),
            }

        return summary

    def _generate_calibration_suggestions(self, summary: BacktestSummary) -> List[str]:
        """Generate auto-calibration suggestions based on backtest results."""
        suggestions = []

        if summary.avg_mae > 5.0:
            suggestions.append("High MAE detected (>5.0). Consider increasing simulation count or refining agent weights.")

        if summary.avg_correlation < 0.3:
            suggestions.append("Low correlation (<0.3). Agent projections may need reweighting or additional data sources.")

        if summary.avg_hit_rate_20pct < 30:
            suggestions.append("Low hit rate within 20% (<30%). Variance may be underestimated.")

        # Position-specific suggestions
        for pos, data in summary.by_position.items():
            bias = data.get("bias", 0)
            if abs(bias) > 2.0:
                direction = "over" if bias > 0 else "under"
                suggestions.append(
                    f"{pos} projections are systematically {direction}-projected by {abs(bias):.1f} pts. "
                    f"Adjust {pos} base rates."
                )

            if data.get("correlation", 0) < 0.2:
                suggestions.append(
                    f"{pos} correlation is very low ({data['correlation']:.3f}). "
                    f"Review {pos}-specific agent accuracy."
                )

        if not suggestions:
            suggestions.append("Projections are well-calibrated. No adjustments needed.")

        return suggestions

    def auto_calibrate(self, summary: BacktestSummary) -> Dict[str, float]:
        """Generate calibration adjustments based on backtest bias.

        Returns a dict of adjustment multipliers per position.
        """
        adjustments = {}

        for pos, data in summary.by_position.items():
            avg_proj = data.get("avg_projected", 1)
            avg_actual = data.get("avg_actual", 1)

            if avg_proj > 0 and avg_actual > 0:
                # Multiplier to bring projections closer to actuals
                multiplier = avg_actual / avg_proj
                # Smooth: don't adjust more than ±15% at once
                multiplier = max(0.85, min(1.15, multiplier))
                adjustments[pos] = round(multiplier, 3)
            else:
                adjustments[pos] = 1.0

        log.info(f"Auto-calibration adjustments: {adjustments}")
        return adjustments
