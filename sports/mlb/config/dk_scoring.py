"""
STACKSNIPER MLB — DraftKings Classic MLB Scoring
Official scoring rules for DK Classic MLB contests.
"""

# ═══════════════════════════════════════════════════
# HITTER SCORING
# ═══════════════════════════════════════════════════
HITTER_SCORING = {
    "single": 3.0,
    "double": 5.0,
    "triple": 8.0,
    "home_run": 10.0,
    "rbi": 2.0,
    "run": 2.0,
    "walk": 2.0,
    "hbp": 2.0,
    "stolen_base": 5.0,
    "caught_stealing": -1.0,  # v3 Phase 1.3
}

# ═══════════════════════════════════════════════════
# PITCHER SCORING
# ═══════════════════════════════════════════════════
PITCHER_SCORING = {
    "win": 4.0,
    "earned_run": -2.0,
    "strikeout": 2.0,
    "inning_pitched": 2.25,      # per full inning (0.75 per out)
    "hit_against": -0.6,
    "walk_against": -0.6,
    "hbp_against": -0.6,
    "complete_game": 2.5,
    "complete_game_shutout": 2.5, # bonus on top of CG
    "no_hitter": 5.0,            # bonus on top of CGSO
}

def calculate_hitter_dkfp(stats: dict) -> float:
    """Calculate DraftKings fantasy points for a hitter stat line."""
    pts = 0.0
    pts += max(0, stats.get("singles", 0)) * HITTER_SCORING["single"]
    pts += max(0, stats.get("doubles", 0)) * HITTER_SCORING["double"]
    pts += max(0, stats.get("triples", 0)) * HITTER_SCORING["triple"]
    pts += max(0, stats.get("home_runs", 0)) * HITTER_SCORING["home_run"]
    pts += max(0, stats.get("rbi", 0)) * HITTER_SCORING["rbi"]
    pts += max(0, stats.get("runs", 0)) * HITTER_SCORING["run"]
    pts += max(0, stats.get("walks", 0)) * HITTER_SCORING["walk"]
    pts += max(0, stats.get("hbp", 0)) * HITTER_SCORING["hbp"]
    pts += max(0, stats.get("stolen_bases", 0)) * HITTER_SCORING["stolen_base"]
    # v3 Phase 1.3: Caught stealing penalty
    pts += max(0, stats.get("caught_stealing", 0)) * HITTER_SCORING["caught_stealing"]
    return round(pts, 2)

def calculate_pitcher_dkfp(stats: dict) -> float:
    """Calculate DraftKings fantasy points for a pitcher stat line."""
    pts = 0.0
    pts += max(0, stats.get("win", 0)) * PITCHER_SCORING["win"]
    pts += max(0, stats.get("earned_runs", 0)) * PITCHER_SCORING["earned_run"]
    pts += max(0, stats.get("strikeouts", 0)) * PITCHER_SCORING["strikeout"]

    # Innings pitched: stored as float (e.g. 6.2 = 6 and 2/3)
    ip_raw = max(0, stats.get("innings_pitched", 0))
    full_innings = int(ip_raw)
    partial = round((ip_raw - full_innings) * 10)  # .1 = 1 out, .2 = 2 outs
    total_outs = (full_innings * 3) + partial
    pts += total_outs * 0.75  # 2.25 per inning = 0.75 per out

    pts += max(0, stats.get("hits_against", 0)) * PITCHER_SCORING["hit_against"]
    pts += max(0, stats.get("walks_against", 0)) * PITCHER_SCORING["walk_against"]
    pts += max(0, stats.get("hbp_against", 0)) * PITCHER_SCORING["hbp_against"]

    if stats.get("complete_game", False):
        pts += PITCHER_SCORING["complete_game"]
    if stats.get("shutout", False):
        pts += PITCHER_SCORING["complete_game_shutout"]
    if stats.get("no_hitter", False):
        pts += PITCHER_SCORING["no_hitter"]

    return round(pts, 2)

# Position eligibility map
POSITION_MAP = {
    "P": ["SP", "RP", "P"],
    "C": ["C"],
    "1B": ["1B", "DH"],
    "2B": ["2B"],
    "3B": ["3B"],
    "SS": ["SS"],
    "OF": ["LF", "CF", "RF", "OF", "DH"],
}
