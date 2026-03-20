"""
STACKSNIPER MLB — Monte Carlo Simulation Engine
Core engine that runs N simulations using agent consensus projections.
Each simulation randomizes player outcomes based on projected distributions.

v6 Performance: Vectorized pitcher sim (279× speedup), modern numpy Generator,
float32 output, removed ThreadPoolExecutor for CPU-bound work, timing instrumentation.
"""
import time
import numpy as np
# v6 Opt 8: scipy.stats imported lazily inside methods that need it (saves 2.2s startup)
from datetime import datetime, date
from typing import Optional
from sports.mlb.config.settings import DEFAULT_SIM_COUNT, MAX_SIM_COUNT
from sports.mlb.agents.agent_pool import agent_pool
from sports.mlb.data.mlb_api import mlb_api
from sports.mlb.data.models import PlayerProjection, GameProjection, SimulationResult
from sports.mlb.utils.logger import get_logger

log = get_logger("SimEngine")

class SimulationEngine:
    """
    Monte Carlo simulation engine for MLB DFS projections.
    For each game on the slate:
    1. Agent pool produces consensus projections
    2. Each simulation run randomizes outcomes from projected distributions
    3. Results are aggregated across all simulations
    """
    def __init__(self, num_sims: int = None):
        self.num_sims = min(num_sims or DEFAULT_SIM_COUNT, MAX_SIM_COUNT)
        self._rng = np.random.default_rng()  # Default; overridden per-run with seed

    def run_full_slate(self, game_date: Optional[date] = None,
                        vegas_data: dict = None,
                        seed: int = None,
                        on_progress=None) -> SimulationResult:
        game_date = game_date or date.today()
        timings = {}

        # v6 Change 4: Modern numpy Generator (thread-safe, faster, better stats)
        if seed is None:
            seed = int(game_date.toordinal() * 1000)
        self._rng = np.random.default_rng(seed)

        log.info(f"▶ Starting {self.num_sims}-sim slate for {game_date} (seed={seed})")

        t0 = time.perf_counter()
        games = mlb_api.get_schedule(game_date)
        if on_progress: on_progress("roster", 0.05, "Fetching rosters...")
        timings["schedule_fetch"] = time.perf_counter() - t0

        if not games:
            log.warning("No games found for this date")
            return SimulationResult(
                sim_id=0, timestamp=datetime.now().isoformat(),
                num_sims=0, games=[], player_projections=[],
                seed=seed, timings=timings,
            )

        log.info(f"  Found {len(games)} games on the slate")

        t0 = time.perf_counter()
        all_player_contexts = []
        game_projections = []
        for game in games:
            gp, player_contexts = self._build_game_context(game, vegas_data)
            game_projections.append(gp)
            all_player_contexts.extend(player_contexts)

        log.info(f"  Built contexts for {len(all_player_contexts)} players")
        if on_progress: on_progress("agents", 0.20, f"Agent analysis for {len(games)} games...")

        # v6 Opt 5: Pre-fetch shared data once per team and per player
        # Eliminates ~520 redundant API/cache calls across agents
        t_prefetch = time.perf_counter()
        self._prefetch_contexts(all_player_contexts, game_date.year)
        timings["prefetch"] = time.perf_counter() - t_prefetch

        player_projections = []
        for ctx in all_player_contexts:
            proj = self._get_player_projection(ctx)
            if proj:
                player_projections.append(proj)

        log.info(f"  Generated projections for {len(player_projections)} players")
        if on_progress: on_progress("agents", 0.40, f"Projected {len(player_projections)} players")
        timings["agent_analysis"] = time.perf_counter() - t0

        # Simulate game-level run environments for correlated outcomes
        t0 = time.perf_counter()
        if on_progress: on_progress("simulation", 0.50, "Running Monte Carlo simulations...")
        game_envs = self._simulate_game_environments(game_projections, player_projections)
        timings["game_environments"] = time.perf_counter() - t0

        # Attach game environment data to each player
        for player in player_projections:
            player._game_envs = game_envs.get(player.game_pk, None)

        # v6 Change 3: Sequential simulation (numpy is CPU-bound; GIL makes threads slower)
        t0 = time.perf_counter()
        log.info(f"  Running {self.num_sims} Monte Carlo simulations...")
        for player in player_projections:
            try:
                self._simulate_player(player)
            except Exception as e:
                log.warning(f"Sim failed for {player.name}: {e}")
                player.sim_points = np.zeros(10, dtype=np.float32)
        timings["simulation"] = time.perf_counter() - t0

        if on_progress: on_progress("aggregation", 0.85, "Aggregating results...")

        # v3 Phase 5.2: Use numpy aggregation on np.ndarray sim_points
        t0 = time.perf_counter()
        for player in player_projections:
            pts = player.sim_points
            if isinstance(pts, np.ndarray) and pts.size > 0:
                player.dk_points = round(float(np.mean(pts)), 2)
                player.dk_points_std = round(float(np.std(pts)), 2)
                player.ceiling = round(float(np.percentile(pts, 95)), 2)
                player.floor = round(float(np.percentile(pts, 10)), 2)
                player.median = round(float(np.median(pts)), 2)
                if player.salary > 0:
                    player.value = round(player.dk_points / player.salary * 1000, 2)

        # Assign default DK-style salaries if no salary data loaded
        any_salary = any(p.salary > 0 for p in player_projections)
        if not any_salary and player_projections:
            self._assign_default_salaries(player_projections)
            # Recalculate value with new salaries
            for player in player_projections:
                if player.salary > 0 and player.dk_points > 0:
                    player.value = round(player.dk_points / player.salary * 1000, 2)

        player_projections.sort(key=lambda p: p.dk_points, reverse=True)
        timings["aggregation"] = time.perf_counter() - t0

        result = SimulationResult(
            sim_id=int(datetime.now().timestamp()),
            timestamp=datetime.now().isoformat(),
            num_sims=self.num_sims,
            games=game_projections,
            player_projections=player_projections,
            confidence_score=self._calculate_confidence(player_projections),
            seed=seed,
            timings=timings,
        )

        total_time = sum(timings.values())
        log.info(f"⏱ Timing: {' | '.join(f'{k}={v:.2f}s' for k, v in timings.items())} | total={total_time:.2f}s")
        log.info(f"✅ Simulation complete: {len(player_projections)} players projected")
        if on_progress: on_progress("complete", 1.0, "Simulation complete")
        return result

    def _assign_default_salaries(self, players: list) -> None:
        """Assign realistic DK-style salaries based on projected DK points.
        Used when no salary CSV has been uploaded so the optimizer can function.
        DK MLB cap is $50,000 for 10 players (2P + 8 hitters).
        Budget: ~$9k avg for pitchers, ~$4k avg for hitters."""
        if not players:
            return

        # Sort by dk_points to rank players
        ranked = sorted(players, key=lambda p: p.dk_points, reverse=True)

        for i, p in enumerate(ranked):
            if p.position in ("SP", "RP", "P"):
                # Pitchers: $6000 - $10400 range (2 pitchers avg ~$8k = $16k)
                base = 7500
                pts_factor = max(0, p.dk_points - 8.0) * 500
                salary = int(min(10400, max(6000, base + pts_factor)))
            else:
                # Hitters: $2000 - $5800 range (8 hitters avg ~$4k = $32k)
                # Total lineup ~$48k, under $50k cap, above $45k min
                base = 3200
                pts_factor = max(0, p.dk_points - 5.0) * 400
                salary = int(min(5800, max(2000, base + pts_factor)))

            # Round to nearest 100
            p.salary = round(salary / 100) * 100

        log.info(f"Assigned default salaries to {len(players)} players")

    def _simulate_game_environments(self, games: list, player_projections: list) -> dict:
        """Simulate game-level run totals to correlate teammate outcomes (vectorized)."""
        game_envs = {}  # game_pk -> dict of numpy arrays

        for game in games:
            game_pk = game.game_pk
            total = game.total_runs or 8.5
            home_pct = 0.52  # slight home advantage

            # v3 Phase 5: Vectorized game environment generation
            game_totals = np.maximum(0, self._rng.normal(total, 2.5, size=self.num_sims))
            rounded_totals = np.rint(game_totals).astype(int)
            # v6 Change 2: Native array binomial (8× speedup, no list comprehension)
            home_runs = self._rng.binomial(rounded_totals, home_pct)
            away_runs = rounded_totals - home_runs

            game_envs[game_pk] = {
                "home_runs": home_runs,
                "away_runs": away_runs,
                "totals": game_totals,
            }

        return game_envs

    def _build_game_context(self, game: dict, vegas_data: dict = None) -> tuple:
        away = game["away_team"]
        home = game["home_team"]

        gp = GameProjection(
            game_pk=game["game_pk"],
            away_team=away.get("abbr", ""),
            home_team=home.get("abbr", ""),
            away_pitcher=away.get("probable_pitcher", {}).get("name", "TBD"),
            home_pitcher=home.get("probable_pitcher", {}).get("name", "TBD"),
            venue=game.get("venue", {}).get("name", ""),
            weather_impact=1.0,
            park_factor=1.0,
        )

        game_vegas = {}
        if vegas_data:
            game_vegas = vegas_data.get(str(game["game_pk"]), {})
        gp.total_runs = game_vegas.get("total", 8.5)

        player_contexts = []
        for side, team_data in [("away", away), ("home", home)]:
            team_id = team_data.get("id")
            opp_data = home if side == "away" else away
            is_home = side == "home"

            if not team_id:
                continue

            roster = mlb_api.get_roster(team_id)

            sp = team_data.get("probable_pitcher", {})
            if sp.get("id"):
                player_contexts.append({
                    "type": "pitcher",
                    "player_id": sp["id"],
                    "player_name": sp.get("name", "TBD"),
                    "team": team_data.get("abbr", ""),
                    "team_id": team_id,
                    "opponent_team_id": opp_data.get("id"),
                    "opponent": opp_data.get("abbr", ""),
                    "position": "SP",
                    "is_home": is_home,
                    "pitcher_id": sp["id"],
                    "pitcher_name": sp.get("name", "TBD"),
                    "opp_pitcher_id": opp_data.get("probable_pitcher", {}).get("id"),
                    "opp_pitcher_name": opp_data.get("probable_pitcher", {}).get("name", "TBD"),
                    "home_team_abbr": home.get("abbr", ""),
                    "weather": game.get("weather", {}),
                    "season": date.today().year,
                    "game_pk": game["game_pk"],
                    "total": game_vegas.get("total"),
                    "home_ml": game_vegas.get("home_ml"),
                    "away_ml": game_vegas.get("away_ml"),
                })

            # Try to get confirmed lineup from boxscore
            batting_order = []
            is_confirmed = False
            try:
                boxscore = mlb_api.get_boxscore(game.get("game_pk", 0))
                team_key = "home" if is_home else "away"
                team_box = boxscore.get("teams", {}).get(team_key, {})
                batting_order_ids = team_box.get("battingOrder", [])
                if batting_order_ids:
                    is_confirmed = True
                    # Build ordered player list from batting order
                    roster_by_id = {p["id"]: p for p in roster}
                    for pid in batting_order_ids:
                        if pid in roster_by_id:
                            batting_order.append(roster_by_id[pid])
            except Exception:
                pass

            if not batting_order:
                batting_order = [p for p in roster if p.get("position_type") != "Pitcher" and p.get("status") == "A"][:9]

            for i, batter in enumerate(batting_order):
                player_contexts.append({
                    "type": "batter",
                    "player_id": batter["id"],
                    "player_name": batter.get("name", ""),
                    "team": team_data.get("abbr", ""),
                    "team_id": team_id,
                    "opponent_team_id": opp_data.get("id"),
                    "opponent": opp_data.get("abbr", ""),
                    "position": batter.get("position", "OF"),
                    "is_home": is_home,
                    "is_confirmed_lineup": is_confirmed,
                    "opp_pitcher_id": opp_data.get("probable_pitcher", {}).get("id"),
                    "opp_pitcher_name": opp_data.get("probable_pitcher", {}).get("name", "TBD"),
                    "home_team_abbr": home.get("abbr", ""),
                    "weather": game.get("weather", {}),
                    "season": date.today().year,
                    "lineup_position": i + 1,
                    "game_pk": game["game_pk"],
                    "total": game_vegas.get("total"),
                    "home_ml": game_vegas.get("home_ml"),
                    "away_ml": game_vegas.get("away_ml"),
                    "batter_id": batter["id"],
                })

        return gp, player_contexts

    def _prefetch_contexts(self, contexts: list, season: int) -> None:
        """v6 Opt 5: Pre-fetch shared data once per player/team to eliminate redundant calls."""
        try:
            from sports.mlb.data.historical_loader import historical_loader
        except ImportError:
            return  # historical_loader not available

        # Pre-fetch team-level data once per team
        team_data_cache = {}
        for ctx in contexts:
            team_id = ctx.get("team_id")
            if team_id and team_id not in team_data_cache:
                team_data_cache[team_id] = {
                    "team_stats_pitching": mlb_api.get_team_stats(team_id, season, "pitching"),
                }

        for ctx in contexts:
            ctx["_team_data"] = team_data_cache.get(ctx.get("team_id"), {})

            if ctx["type"] == "batter":
                batter_id = ctx.get("batter_id")
                opp_pitcher_id = ctx.get("opp_pitcher_id")
                if batter_id:
                    ctx["_prefetched_season_stats"] = mlb_api.get_player_stats(
                        batter_id, season, "hitting", "season")
                    ctx["_prefetched_recent_games"] = historical_loader.get_player_recent_games(
                        batter_id, 15, "hitting")
                if batter_id and opp_pitcher_id:
                    ctx["_prefetched_bvp"] = historical_loader.get_batter_vs_pitcher(
                        batter_id, opp_pitcher_id)

            elif ctx["type"] == "pitcher":
                pitcher_id = ctx.get("pitcher_id")
                opp_team_id = ctx.get("opponent_team_id")
                if pitcher_id:
                    ctx["_prefetched_season_stats"] = mlb_api.get_player_stats(
                        pitcher_id, season, "pitching", "season")
                    ctx["_prefetched_recent_games"] = historical_loader.get_player_recent_games(
                        pitcher_id, 7, "pitching")
                if pitcher_id and opp_team_id:
                    ctx["_prefetched_vs_team"] = historical_loader.get_pitcher_vs_team(
                        pitcher_id, opp_team_id, season)

    def _get_player_projection(self, context: dict) -> Optional[PlayerProjection]:
        try:
            if context["type"] == "pitcher":
                proj = agent_pool.get_consensus_pitcher_projection(context)
            else:
                proj = agent_pool.get_consensus_hitter_projection(context)

            if not proj:
                return None

            pp = PlayerProjection(
                player_id=context["player_id"],
                name=context["player_name"],
                team=context["team"],
                position=context["position"],
                opponent=context["opponent"],
                is_home=context["is_home"],
            )
            pp.game_pk = context.get("game_pk", 0)

            if context["type"] == "pitcher":
                pp.innings_pitched = proj.get("innings_pitched", 5.0)
                pp.pitcher_strikeouts = proj.get("strikeouts", 5.0)
                pp.earned_runs = proj.get("earned_runs", 3.0)
                pp.hits_against = proj.get("hits_against", 6.0)
                pp.walks_against = proj.get("walks_against", 2.5)
                pp.hbp_against = proj.get("hbp_against", 0.3)
                pp.win_probability = proj.get("win_probability", 0.4)
            else:
                pp.plate_appearances = proj.get("plate_appearances", 3.8)
                pp.at_bats = proj.get("at_bats", 3.5)
                pp.singles = proj.get("singles", 0.6)
                pp.doubles = proj.get("doubles", 0.18)
                pp.triples = proj.get("triples", 0.02)
                pp.home_runs = proj.get("home_runs", 0.10)
                pp.rbi = proj.get("rbi", 0.50)
                pp.runs = proj.get("runs", 0.50)
                pp.walks = proj.get("walks", 0.30)
                pp.hbp = proj.get("hbp", 0.03)
                pp.stolen_bases = proj.get("stolen_bases", 0.05)

            return pp
        except Exception as e:
            log.warning(f"Failed projection for {context.get('player_name')}: {e}")
            return None

    def _compute_corr_factors(self, player: PlayerProjection, n_sims: int) -> np.ndarray:
        """Compute per-sim correlation factors from game environment arrays."""
        game_envs = getattr(player, '_game_envs', None)
        if game_envs is None:
            return np.ones(n_sims)

        if player.is_home:
            team_runs = game_envs["home_runs"][:n_sims]
            expected = game_envs["totals"][:n_sims] * 0.52
        else:
            team_runs = game_envs["away_runs"][:n_sims]
            expected = game_envs["totals"][:n_sims] * 0.48

        safe_expected = np.maximum(expected, 1e-6)
        corr = 0.7 + 0.3 * (team_runs / safe_expected)
        return np.clip(corr, 0.5, 2.0)

    def _simulate_player(self, player: PlayerProjection):
        n = self.num_sims
        corr_factors = self._compute_corr_factors(player, n)

        if player.position in ("SP", "RP", "P"):
            # v6 Change 1: Vectorized pitcher simulation (279× faster than scalar loop)
            player.sim_points = self._sim_pitcher_game_vectorized(player, corr_factors)
        else:
            # v3 Phase 5.1: Vectorized hitter simulation
            player.sim_points = self._sim_hitter_game_vectorized(player, corr_factors)

        player.actual_sims_used = len(player.sim_points)

    def _sim_pitcher_game_vectorized(self, p: PlayerProjection, corr_factors: np.ndarray) -> np.ndarray:
        """
        v6 Change 1: Vectorized pitcher simulation — all N sims in one pass.
        Replaces the scalar _sim_pitcher_game() loop. 279× measured speedup.
        Uses modern numpy Generator API for all random draws.
        """
        from sports.mlb.config.dk_scoring import PITCHER_SCORING
        from scipy.stats import truncnorm  # Lazy import — 2.2s cost on first sim only
        n = len(corr_factors)
        rng = self._rng

        # Vectorized truncated normal for IP (279× faster than scalar loop)
        mu = max(0.5, p.innings_pitched)
        sigma = 1.2
        a, b = (0.33 - mu) / sigma, (9.0 - mu) / sigma
        ip_arr = truncnorm.rvs(a, b, loc=mu, scale=sigma, size=n, random_state=rng)

        # Vectorized Poisson draws for all stats
        k_per_ip = p.pitcher_strikeouts / max(1, p.innings_pitched)
        er_per_ip = p.earned_runs / max(1, p.innings_pitched)
        h_per_ip = p.hits_against / max(1, p.innings_pitched)
        bb_per_ip = p.walks_against / max(1, p.innings_pitched)
        hbp_per_ip = p.hbp_against / max(1, p.innings_pitched)

        strikeouts = rng.poisson(np.maximum(0.01, k_per_ip * ip_arr))
        earned_runs = rng.poisson(np.maximum(0.01, er_per_ip * ip_arr * corr_factors))
        hits = rng.poisson(np.maximum(0.01, h_per_ip * ip_arr * corr_factors))
        walks_arr = rng.poisson(np.maximum(0.01, bb_per_ip * ip_arr))
        hbp_arr = rng.poisson(np.maximum(0.01, hbp_per_ip * ip_arr))

        # Vectorized win logic (matches scalar conditional exactly)
        adjusted_wp = p.win_probability * np.maximum(0.05, 1.0 - earned_runs * 0.15)
        win_rolls = rng.random(n)
        wins = np.zeros(n, dtype=np.float64)

        # IP >= 5.0 and ER <= 5: full win probability
        mask_full = (ip_arr >= 5.0) & (earned_runs <= 5)
        wins[mask_full] = (win_rolls[mask_full] < adjusted_wp[mask_full]).astype(np.float64)

        # IP >= 4.0 and < 5.0 and ER <= 5: 40% of normal rate
        mask_partial = (ip_arr >= 4.0) & (ip_arr < 5.0) & (earned_runs <= 5)
        wins[mask_partial] = (win_rolls[mask_partial] < adjusted_wp[mask_partial] * 0.4).astype(np.float64)

        # ER > 5 or IP < 4.0: no win (wins stays 0)

        # IP → outs for scoring
        full_innings = ip_arr.astype(int)
        partial_outs = np.rint((ip_arr - full_innings) * 3).astype(int)
        total_outs = full_innings * 3 + partial_outs

        # Vectorized scoring
        pts = (
            wins * PITCHER_SCORING["win"] +
            earned_runs * PITCHER_SCORING["earned_run"] +
            strikeouts * PITCHER_SCORING["strikeout"] +
            total_outs * 0.75 +  # 2.25 per inning = 0.75 per out
            hits * PITCHER_SCORING["hit_against"] +
            walks_arr * PITCHER_SCORING["walk_against"] +
            hbp_arr * PITCHER_SCORING["hbp_against"]
        )

        # CG / CGSO / No-Hitter bonuses
        cg_mask = ip_arr >= 9.0
        pts[cg_mask] += PITCHER_SCORING["complete_game"]
        cgso_mask = cg_mask & (earned_runs == 0)
        pts[cgso_mask] += PITCHER_SCORING["complete_game_shutout"]
        nh_mask = cgso_mask & (hits == 0)
        pts[nh_mask] += PITCHER_SCORING["no_hitter"]

        # v6 Sprint 5.1: Store per-stat distributions for props analysis
        p.sim_ks = strikeouts.tolist()
        p.sim_er = earned_runs.tolist()
        p.sim_outs = total_outs.tolist()
        p.sim_hits_allowed = hits.tolist()

        # Convergence detection (informational — all sims already computed)
        if n >= 300:
            rolling_means = np.cumsum(pts) / np.arange(1, n + 1)
            deltas = np.abs(np.diff(rolling_means[99::100]))  # Check every 100 sims
            stable_count = 0
            converged_at = n
            for i, d in enumerate(deltas):
                if d < 0.05:
                    stable_count += 1
                else:
                    stable_count = 0
                if stable_count >= 3:
                    converged_at = min(n, (i + 1) * 100)
                    break
            p.actual_sims_used = converged_at

        # v6 Change 5: float32 output (halves memory, 2 decimal places only need 7 digits)
        return np.round(pts, 2).astype(np.float32)

    def _sim_hitter_game_vectorized(self, p: PlayerProjection, corr_factors: np.ndarray) -> np.ndarray:
        """
        v3 Phase 5.1: Vectorized hitter simulation — runs all N sims at once
        using NumPy operations instead of per-sim Python loops.
        Returns np.ndarray of DKFP for each sim.
        """
        from sports.mlb.config.dk_scoring import HITTER_SCORING
        n = len(corr_factors)
        rng = self._rng

        # 1.5% scratch probability per sim
        scratch_mask = rng.random(n) < 0.015

        # Generate PA counts for all sims
        pa_all = np.maximum(2, np.rint(rng.normal(p.plate_appearances, 0.8, size=n)).astype(int))
        pa_all[scratch_mask] = 0

        # Compute rates
        total_hits_expected = p.singles + p.doubles + p.triples + p.home_runs
        base_hit_rate = total_hits_expected / max(1, p.plate_appearances)
        walk_rate = p.walks / max(1, p.plate_appearances)
        hbp_rate = p.hbp / max(1, p.plate_appearances)

        # Hit type percentages
        if total_hits_expected > 0:
            hr_pct = p.home_runs / total_hits_expected
            triple_pct = p.triples / total_hits_expected
            double_pct = p.doubles / total_hits_expected
            _single_pct = p.singles / total_hits_expected  # noqa: F841
        else:
            _single_pct, double_pct, triple_pct, hr_pct = 0.6, 0.2, 0.02, 0.08  # noqa: F841

        # Correlated hit rate per sim (capped at 1.0)
        hit_rates = np.minimum(1.0, base_hit_rate * corr_factors)

        # PA outcome probabilities: [walk, hbp, hit, out]
        # For each sim, generate all PA outcomes at once using np.random.choice
        # We use the max PA across all sims to create a uniform array, then mask
        max_pa = int(pa_all.max()) if pa_all.max() > 0 else 0

        # Initialize stat accumulators
        singles = np.zeros(n, dtype=int)
        doubles = np.zeros(n, dtype=int)
        triples = np.zeros(n, dtype=int)
        home_runs = np.zeros(n, dtype=int)
        walks = np.zeros(n, dtype=int)
        hbps = np.zeros(n, dtype=int)

        if max_pa > 0:
            # For each PA slot, generate outcomes for all sims at once
            for pa_idx in range(max_pa):
                active = pa_idx < pa_all  # which sims have this PA
                n_active = active.sum()
                if n_active == 0:
                    continue

                r = rng.random(n)
                # Determine outcome type for active sims
                is_walk = active & (r < walk_rate)
                is_hbp = active & (~is_walk) & (r < walk_rate + hbp_rate)
                is_hit = active & (~is_walk) & (~is_hbp) & (r < walk_rate + hbp_rate + hit_rates)

                walks += is_walk.astype(int)
                hbps += is_hbp.astype(int)

                # For hits, determine hit type
                n_hits = is_hit.sum()
                if n_hits > 0:
                    hit_r = rng.random(n)
                    is_hr = is_hit & (hit_r < hr_pct)
                    is_triple = is_hit & (~is_hr) & (hit_r < hr_pct + triple_pct)
                    is_double = is_hit & (~is_hr) & (~is_triple) & (hit_r < hr_pct + triple_pct + double_pct)
                    is_single = is_hit & (~is_hr) & (~is_triple) & (~is_double)

                    home_runs += is_hr.astype(int)
                    triples += is_triple.astype(int)
                    doubles += is_double.astype(int)
                    singles += is_single.astype(int)

        # RBI calculation
        rbi_opportunities = home_runs + (doubles + triples) * 0.5 + singles * 0.2
        rbi = home_runs.copy()
        rbi_rate = (p.rbi / max(1, p.plate_appearances)) * corr_factors
        for opp_idx in range(int(np.max(rbi_opportunities)) if rbi_opportunities.max() > 0 else 0):
            eligible = opp_idx < rbi_opportunities.astype(int)
            rbi += (eligible & (rng.random(n) < rbi_rate)).astype(int)
        rbi = np.minimum(rbi, 10)

        # Runs calculation
        on_base = singles + doubles + triples + walks + hbps
        runs = home_runs.copy()
        run_rate = (p.runs / max(1, p.plate_appearances)) * corr_factors
        max_on_base = int(on_base.max()) if on_base.max() > 0 else 0
        for opp_idx in range(max_on_base):
            eligible = opp_idx < on_base
            runs += (eligible & (rng.random(n) < run_rate)).astype(int)

        # Stolen bases (per-opportunity from singles + walks)
        sb_chances = singles + walks
        sb = np.zeros(n, dtype=int)
        cs = np.zeros(n, dtype=int)
        sb_eligible = (singles + walks + hbps) > 0
        if sb_eligible.any():
            sb_rate = p.stolen_bases / max(1, p.singles + p.walks + p.hbp)
            max_sb_chances = int(sb_chances.max()) if sb_chances.max() > 0 else 0
            total_attempts = np.zeros(n, dtype=int)
            for sb_idx in range(max_sb_chances):
                eligible = sb_eligible & (sb_idx < sb_chances)
                total_attempts += (eligible & (rng.random(n) < sb_rate)).astype(int)
            total_attempts = np.minimum(total_attempts, 5)
            # Apply 74% success rate to each attempt
            max_attempts = int(total_attempts.max()) if total_attempts.max() > 0 else 0
            for att_idx in range(max_attempts):
                active = att_idx < total_attempts
                success = active & (rng.random(n) < 0.74)
                sb += success.astype(int)
                cs += (active & ~success).astype(int)
            sb = np.minimum(sb, 3)

        # v3 Phase 5.1: Vectorized scoring — multiply outcome counts by scoring values
        points = (
            singles * HITTER_SCORING["single"] +
            doubles * HITTER_SCORING["double"] +
            triples * HITTER_SCORING["triple"] +
            home_runs * HITTER_SCORING["home_run"] +
            rbi * HITTER_SCORING["rbi"] +
            runs * HITTER_SCORING["run"] +
            walks * HITTER_SCORING["walk"] +
            hbps * HITTER_SCORING["hbp"] +
            sb * HITTER_SCORING["stolen_base"] +
            cs * HITTER_SCORING["caught_stealing"]
        )

        # v6 Sprint 5.1: Store per-stat distributions for props analysis
        total_hits = singles + doubles + triples + home_runs
        total_bases = singles + doubles * 2 + triples * 3 + home_runs * 4
        p.sim_hits = total_hits.tolist()
        p.sim_hrs = home_runs.tolist()
        p.sim_rbi = rbi.tolist()
        p.sim_runs = runs.tolist()
        p.sim_sb = sb.tolist()
        p.sim_total_bases = total_bases.tolist()

        # v6 Change 5: float32 output (halves memory)
        return np.round(points, 2).astype(np.float32)

    def _calculate_confidence(self, projections: list) -> float:
        if not projections:
            return 0.0
        with_data = sum(1 for p in projections if p.dk_points > 0)
        coverage = with_data / max(1, len(projections))
        return round(coverage * 0.8 + 0.2, 2)
