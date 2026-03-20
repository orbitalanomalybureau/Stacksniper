"""
STACKSNIPER MLB — FanDuel MLB Scoring
Official scoring rules for FanDuel MLB contests.
"""

# ═══════════════════════════════════════════════════
# HITTER SCORING
# ═══════════════════════════════════════════════════
FD_HITTER_SCORING = {
    "single": 3.0,
    "double": 6.0,
    "triple": 9.0,
    "home_run": 12.0,
    "rbi": 3.5,
    "run": 3.2,
    "walk": 3.0,
    "hbp": 3.0,
    "stolen_base": 6.0,
    "caught_stealing": -3.0,
}

# ═══════════════════════════════════════════════════
# PITCHER SCORING
# ═══════════════════════════════════════════════════
FD_PITCHER_SCORING = {
    "win": 6.0,
    "quality_start": 4.0,
    "earned_run": -3.0,
    "strikeout": 3.0,
    "inning_pitched": 3.0,
}

# ═══════════════════════════════════════════════════
# ROSTER CONFIGURATION
# ═══════════════════════════════════════════════════
FD_SALARY_CAP = 35000
FD_ROSTER_SLOTS = ["P", "C/1B", "2B", "3B", "SS", "OF", "OF", "OF", "UTIL"]
FD_ROSTER_SIZE = 9

FD_POSITION_MAP = {
    "P": ["SP", "RP", "P"],
    "C/1B": ["C", "1B"],
    "2B": ["2B"],
    "3B": ["3B"],
    "SS": ["SS"],
    "OF": ["LF", "CF", "RF", "OF"],
    "UTIL": ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "OF", "SP", "RP", "P"],
}


def calculate_hitter_fdfp(stats: dict) -> float:
    """Calculate FanDuel fantasy points for a hitter stat line."""
    pts = 0.0
    pts += stats.get("singles", 0) * FD_HITTER_SCORING["single"]
    pts += stats.get("doubles", 0) * FD_HITTER_SCORING["double"]
    pts += stats.get("triples", 0) * FD_HITTER_SCORING["triple"]
    pts += stats.get("home_runs", 0) * FD_HITTER_SCORING["home_run"]
    pts += stats.get("rbi", 0) * FD_HITTER_SCORING["rbi"]
    pts += stats.get("runs", 0) * FD_HITTER_SCORING["run"]
    pts += stats.get("walks", 0) * FD_HITTER_SCORING["walk"]
    pts += stats.get("hbp", 0) * FD_HITTER_SCORING["hbp"]
    pts += stats.get("stolen_bases", 0) * FD_HITTER_SCORING["stolen_base"]
    pts += stats.get("caught_stealing", 0) * FD_HITTER_SCORING["caught_stealing"]
    return round(pts, 2)


def calculate_pitcher_fdfp(stats: dict) -> float:
    """Calculate FanDuel fantasy points for a pitcher stat line."""
    pts = 0.0
    pts += stats.get("win", 0) * FD_PITCHER_SCORING["win"]
    pts += stats.get("earned_runs", 0) * FD_PITCHER_SCORING["earned_run"]
    pts += stats.get("strikeouts", 0) * FD_PITCHER_SCORING["strikeout"]

    # Innings pitched: 3 pts per full inning
    ip_raw = stats.get("innings_pitched", 0)
    full_innings = int(ip_raw)
    partial = round((ip_raw - full_innings) * 10)
    total_outs = (full_innings * 3) + partial
    pts += total_outs  # 3 per inning = 1 per out

    # Quality start bonus
    if ip_raw >= 6 and stats.get("earned_runs", 0) <= 3:
        pts += FD_PITCHER_SCORING["quality_start"]

    return round(pts, 2)
