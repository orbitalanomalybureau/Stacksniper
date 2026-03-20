"""
STACKSNIPER MLB — Accuracy Tracker
Compares projected DK fantasy points against actual boxscore results.
"""
import math
from datetime import date, datetime, timedelta
from sports.mlb.utils.logger import get_logger

log = get_logger("Accuracy")


class AccuracyTracker:
    def __init__(self, db=None):
        self.db = db

    def _get_db(self):
        """Lazy-load database singleton if not injected."""
        if self.db is None:
            from sports.mlb.data.database import db
            self.db = db
        return self.db

    def update_daily_accuracy(self, date_str):
        """
        Fetch yesterday's boxscores, compare to stored projections, save accuracy records.
        Returns a summary dict with count of records processed.
        """
        from sports.mlb.data.mlb_api import MLBStatsAPI
        from sports.mlb.config.dk_scoring import calculate_hitter_dkfp, calculate_pitcher_dkfp

        api = MLBStatsAPI()
        db = self._get_db()
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # 1. Fetch schedule for the target date to get game_pks
        games = api.get_schedule(game_date=target_date)
        if not games:
            log.info(f"No games found for {date_str}")
            return {"date": date_str, "games": 0, "records": 0}

        # 2. Load stored projections for that date
        conn = db._conn()
        try:
            conn.row_factory = None
            proj_rows = conn.execute(
                "SELECT player_id, projected_dkfp FROM projections WHERE date = ?",
                (date_str,)
            ).fetchall()
        finally:
            conn.close()

        projection_map = {}
        for row in proj_rows:
            player_id, projected = row[0], row[1]
            if player_id not in projection_map:
                projection_map[player_id] = projected

        if not projection_map:
            log.info(f"No projections stored for {date_str}")
            return {"date": date_str, "games": len(games), "records": 0}

        # 3. Fetch boxscores for each game and extract actual stats
        records_saved = 0
        game_pks = [g["game_pk"] for g in games if g.get("game_pk")]
        boxscores = api.fetch_boxscores_batch(game_pks) if game_pks else {}

        for game_pk, box in boxscores.items():
            if not box:
                continue

            teams_data = box.get("teams", {})
            for side in ("away", "home"):
                team_data = teams_data.get(side, {})
                players = team_data.get("players", {})

                for player_key, player_data in players.items():
                    player_id = player_data.get("person", {}).get("id")
                    player_name = player_data.get("person", {}).get("fullName", "Unknown")
                    position = player_data.get("position", {}).get("abbreviation", "")

                    if player_id not in projection_map:
                        continue

                    # Determine if hitter or pitcher from boxscore
                    batting_stats = player_data.get("stats", {}).get("batting", {})
                    pitching_stats = player_data.get("stats", {}).get("pitching", {})

                    actual_dkfp = 0.0
                    if pitching_stats and pitching_stats.get("inningsPitched", "0.0") != "0.0":
                        # Pitcher
                        ip_str = pitching_stats.get("inningsPitched", "0.0")
                        try:
                            ip_val = float(ip_str)
                        except (ValueError, TypeError):
                            ip_val = 0.0

                        p_stats = {
                            "innings_pitched": ip_val,
                            "strikeouts": int(pitching_stats.get("strikeOuts", 0)),
                            "earned_runs": int(pitching_stats.get("earnedRuns", 0)),
                            "hits_against": int(pitching_stats.get("hits", 0)),
                            "walks_against": int(pitching_stats.get("baseOnBalls", 0)),
                            "hbp_against": int(pitching_stats.get("hitByPitch", 0)),
                            "win": 1 if pitching_stats.get("wins", 0) else 0,
                            "complete_game": bool(pitching_stats.get("completeGames", 0)),
                            "shutout": bool(pitching_stats.get("shutouts", 0)),
                            "no_hitter": (
                                bool(pitching_stats.get("completeGames", 0))
                                and int(pitching_stats.get("hits", 0)) == 0
                            ),
                        }
                        actual_dkfp = calculate_pitcher_dkfp(p_stats)
                    elif batting_stats and int(batting_stats.get("plateAppearances", 0)) > 0:
                        # Hitter
                        hits = int(batting_stats.get("hits", 0))
                        doubles = int(batting_stats.get("doubles", 0))
                        triples = int(batting_stats.get("triples", 0))
                        home_runs = int(batting_stats.get("homeRuns", 0))
                        singles = hits - doubles - triples - home_runs

                        h_stats = {
                            "singles": singles,
                            "doubles": doubles,
                            "triples": triples,
                            "home_runs": home_runs,
                            "rbi": int(batting_stats.get("rbi", 0)),
                            "runs": int(batting_stats.get("runs", 0)),
                            "walks": int(batting_stats.get("baseOnBalls", 0)),
                            "hbp": int(batting_stats.get("hitByPitch", 0)),
                            "stolen_bases": int(batting_stats.get("stolenBases", 0)),
                            "caught_stealing": int(batting_stats.get("caughtStealing", 0)),
                        }
                        actual_dkfp = calculate_hitter_dkfp(h_stats)
                    else:
                        continue

                    projected_dkfp = projection_map[player_id]

                    # Save accuracy record
                    conn2 = db._conn()
                    try:
                        conn2.execute(
                            """INSERT OR REPLACE INTO accuracy_records
                               (date, player_name, player_id, position, projected_dkfp, actual_dkfp)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (date_str, player_name, player_id, position, projected_dkfp, actual_dkfp),
                        )
                        conn2.commit()
                    finally:
                        conn2.close()

                    # Also update the projections table with actual results
                    conn3 = db._conn()
                    try:
                        conn3.execute(
                            """UPDATE projections
                               SET actual_dkfp = ?, error = ?
                               WHERE date = ? AND player_id = ?""",
                            (actual_dkfp, projected_dkfp - actual_dkfp, date_str, player_id),
                        )
                        conn3.commit()
                    finally:
                        conn3.close()

                    records_saved += 1

        summary = {
            "date": date_str,
            "games": len(games),
            "records": records_saved,
        }
        log.info(f"Accuracy update for {date_str}: {records_saved} records from {len(games)} games")
        return summary

    def get_accuracy_summary(self, days=30):
        """
        Get accuracy metrics over the last N days.
        Returns: mae, rmse, r_squared, calibration_score, per_position breakdown, daily_trend.
        """
        db = self._get_db()
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        conn = db._conn()
        try:
            rows = conn.execute(
                """SELECT date, player_name, player_id, position, projected_dkfp, actual_dkfp
                   FROM accuracy_records
                   WHERE date >= ? AND date <= ?
                   ORDER BY date DESC""",
                (str(start_date), str(end_date)),
            ).fetchall()
        finally:
            conn.close()

        if not rows:
            return {
                "days": days,
                "total_records": 0,
                "mae": 0.0,
                "rmse": 0.0,
                "r_squared": 0.0,
                "calibration_score": 0.0,
                "per_position": {},
                "daily_trend": [],
            }

        projected_vals = []
        actual_vals = []
        errors = []
        position_data = {}
        daily_data = {}

        for row in rows:
            dt, name, pid, pos, proj, actual = row
            if proj is None or actual is None:
                continue

            err = proj - actual
            projected_vals.append(proj)
            actual_vals.append(actual)
            errors.append(err)

            # Per-position
            pos_key = pos if pos else "UNK"
            if pos_key not in position_data:
                position_data[pos_key] = {"errors": [], "count": 0}
            position_data[pos_key]["errors"].append(abs(err))
            position_data[pos_key]["count"] += 1

            # Daily
            if dt not in daily_data:
                daily_data[dt] = {"errors": [], "count": 0}
            daily_data[dt]["errors"].append(abs(err))
            daily_data[dt]["count"] += 1

        n = len(errors)
        if n == 0:
            return {
                "days": days,
                "total_records": 0,
                "mae": 0.0,
                "rmse": 0.0,
                "r_squared": 0.0,
                "calibration_score": 0.0,
                "per_position": {},
                "daily_trend": [],
            }

        # MAE
        abs_errors = [abs(e) for e in errors]
        mae = sum(abs_errors) / n

        # RMSE
        rmse = math.sqrt(sum(e ** 2 for e in errors) / n)

        # R-squared
        mean_actual = sum(actual_vals) / n
        ss_res = sum((p - a) ** 2 for p, a in zip(projected_vals, actual_vals))
        ss_tot = sum((a - mean_actual) ** 2 for a in actual_vals)
        r_squared = round(1 - (ss_res / ss_tot), 4) if ss_tot > 0 else 0.0

        # Calibration score: percentage of projections within 5 DKFP of actual
        within_5 = sum(1 for e in abs_errors if e <= 5.0)
        calibration_score = round((within_5 / n) * 100, 1)

        # Per-position breakdown
        per_position = {}
        for pos_key, pdata in position_data.items():
            pos_mae = sum(pdata["errors"]) / len(pdata["errors"])
            per_position[pos_key] = {
                "mae": round(pos_mae, 2),
                "count": pdata["count"],
            }

        # Daily trend (last N days, sorted ascending)
        daily_trend = []
        for dt in sorted(daily_data.keys()):
            d = daily_data[dt]
            daily_mae = sum(d["errors"]) / len(d["errors"])
            daily_trend.append({
                "date": dt,
                "mae": round(daily_mae, 2),
                "count": d["count"],
            })

        return {
            "days": days,
            "total_records": n,
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r_squared": r_squared,
            "calibration_score": calibration_score,
            "per_position": per_position,
            "daily_trend": daily_trend,
        }

    def get_daily_detail(self, date_str):
        """
        Get player-by-player projected vs actual for a specific date.
        Returns sorted list of {player, position, projected, actual, error}.
        """
        db = self._get_db()
        conn = db._conn()
        try:
            rows = conn.execute(
                """SELECT player_name, position, projected_dkfp, actual_dkfp
                   FROM accuracy_records
                   WHERE date = ?
                   ORDER BY actual_dkfp DESC""",
                (date_str,),
            ).fetchall()
        finally:
            conn.close()

        results = []
        for row in rows:
            name, pos, proj, actual = row
            if proj is None or actual is None:
                continue
            error = round(proj - actual, 2)
            results.append({
                "player": name,
                "position": pos or "",
                "projected": round(proj, 2),
                "actual": round(actual, 2),
                "error": error,
                "abs_error": round(abs(error), 2),
            })

        # Sort by absolute error ascending (best predictions first)
        results.sort(key=lambda x: x["abs_error"])
        return results


accuracy_tracker = AccuracyTracker()
