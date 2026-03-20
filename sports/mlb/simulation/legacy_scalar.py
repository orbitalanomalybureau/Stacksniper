"""
STACKSNIPER MLB — Legacy Scalar Simulation Methods
These are the original per-simulation-loop methods, preserved for debugging
and reference. Production code uses the vectorized versions in engine.py.

DEPRECATED: Do not use in production. These are 279× slower than vectorized.
"""
import numpy as np
from scipy.stats import truncnorm
from sports.mlb.config.dk_scoring import calculate_hitter_dkfp, calculate_pitcher_dkfp
from sports.mlb.data.models import PlayerProjection


def sim_pitcher_game_scalar(p: PlayerProjection, corr_factor: float = 1.0, return_stats: bool = False):
    """[DEPRECATED] Scalar pitcher sim. Use engine._sim_pitcher_game_vectorized() instead."""
    mu = p.innings_pitched
    sigma = 1.2
    a, b = (0.33 - mu) / sigma, (9.0 - mu) / sigma
    ip = float(truncnorm.rvs(a, b, loc=mu, scale=sigma))

    full_innings = int(ip)
    partial = round((ip - full_innings) * 3)
    total_outs = full_innings * 3 + partial

    k_per_ip = p.pitcher_strikeouts / max(1, p.innings_pitched)
    strikeouts = np.random.poisson(k_per_ip * ip)

    er_per_ip = p.earned_runs / max(1, p.innings_pitched)
    earned_runs = np.random.poisson(er_per_ip * ip * corr_factor)

    h_per_ip = p.hits_against / max(1, p.innings_pitched)
    hits = np.random.poisson(h_per_ip * ip * corr_factor)

    bb_per_ip = p.walks_against / max(1, p.innings_pitched)
    walks = np.random.poisson(bb_per_ip * ip)

    hbp = np.random.poisson(max(0.01, p.hbp_against / max(1, p.innings_pitched) * ip))

    if earned_runs > 5:
        win = 0
    elif ip >= 5.0:
        adjusted_wp = p.win_probability * max(0.05, 1.0 - (earned_runs * 0.15))
        win = 1 if np.random.random() < adjusted_wp else 0
    elif ip >= 4.0:
        adjusted_wp = p.win_probability * 0.4 * max(0.05, 1.0 - (earned_runs * 0.15))
        win = 1 if np.random.random() < adjusted_wp else 0
    else:
        win = 0

    complete_game = ip >= 9.0
    shutout = complete_game and earned_runs == 0
    no_hitter = shutout and hits == 0

    stats = {
        "innings_pitched": ip, "strikeouts": int(strikeouts),
        "earned_runs": int(earned_runs), "hits_against": int(hits),
        "walks_against": int(walks), "hbp_against": int(hbp),
        "win": win, "complete_game": complete_game,
        "shutout": shutout, "no_hitter": no_hitter,
    }
    dkfp = calculate_pitcher_dkfp(stats)
    if return_stats:
        return dkfp, {"strikeouts": int(strikeouts), "earned_runs": int(earned_runs),
                       "outs_recorded": total_outs, "hits_against": int(hits)}
    return dkfp


def sim_hitter_game_scalar(p: PlayerProjection, corr_factor: float = 1.0) -> float:
    """[DEPRECATED] Scalar hitter sim. Use engine._sim_hitter_game_vectorized() instead."""
    if np.random.random() < 0.015:
        return 0.0

    pa = max(2, round(np.random.normal(p.plate_appearances, 0.8)))
    hit_rate = (p.singles + p.doubles + p.triples + p.home_runs) / max(1, p.plate_appearances)
    walk_rate = p.walks / max(1, p.plate_appearances)
    hbp_rate = p.hbp / max(1, p.plate_appearances)
    hit_rate = min(1.0, hit_rate * corr_factor)

    total_hits_expected = p.singles + p.doubles + p.triples + p.home_runs
    if total_hits_expected > 0:
        double_pct = p.doubles / total_hits_expected
        triple_pct = p.triples / total_hits_expected
        hr_pct = p.home_runs / total_hits_expected
    else:
        _single_pct, double_pct, triple_pct, hr_pct = 0.6, 0.2, 0.02, 0.08  # noqa: F841

    stats = {"singles": 0, "doubles": 0, "triples": 0, "home_runs": 0,
             "rbi": 0, "runs": 0, "walks": 0, "hbp": 0,
             "stolen_bases": 0, "caught_stealing": 0}

    for _ in range(pa):
        r = np.random.random()
        if r < walk_rate:
            stats["walks"] += 1
        elif r < walk_rate + hbp_rate:
            stats["hbp"] += 1
        elif r < walk_rate + hbp_rate + hit_rate:
            hit_r = np.random.random()
            if hit_r < hr_pct:
                stats["home_runs"] += 1
            elif hit_r < hr_pct + triple_pct:
                stats["triples"] += 1
            elif hit_r < hr_pct + triple_pct + double_pct:
                stats["doubles"] += 1
            else:
                stats["singles"] += 1

    rbi_opportunities = stats["home_runs"] + (stats["doubles"] + stats["triples"]) * 0.5 + stats["singles"] * 0.2
    stats["rbi"] = stats["home_runs"]
    rbi_rate = (p.rbi / max(1, p.plate_appearances)) * corr_factor
    for _ in range(int(rbi_opportunities)):
        if np.random.random() < rbi_rate:
            stats["rbi"] += 1
    stats["rbi"] = min(stats["rbi"], 10)

    run_opportunities = (stats["singles"] + stats["doubles"] + stats["triples"] +
                         stats["walks"] + stats["hbp"])
    stats["runs"] = stats["home_runs"]
    run_rate = (p.runs / max(1, p.plate_appearances)) * corr_factor
    for _ in range(run_opportunities):
        if np.random.random() < run_rate:
            stats["runs"] += 1

    on_base_for_sb = stats["singles"] + stats["walks"] + stats["hbp"]
    if on_base_for_sb > 0:
        sb_rate = p.stolen_bases / max(1, p.singles + p.walks + p.hbp)
        sb_chances = stats["singles"] + stats["walks"]
        total_sb_attempts = sum(1 for _ in range(sb_chances) if np.random.random() < sb_rate)
        total_sb_attempts = min(total_sb_attempts, 5)
        for _ in range(total_sb_attempts):
            if np.random.random() < 0.74:
                stats["stolen_bases"] += 1
            else:
                stats["caught_stealing"] += 1
        stats["stolen_bases"] = min(stats["stolen_bases"], 3)

    return calculate_hitter_dkfp(stats)
