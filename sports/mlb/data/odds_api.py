"""
STACKSNIPER MLB — The Odds API Integration
"""
import requests
from sports.mlb.utils.cache import get_cached, set_cached
from sports.mlb.utils.logger import get_logger

log = get_logger("OddsAPI")

ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/"

# Team name mapping from Odds API names to MLB API abbreviations
ODDS_TEAM_MAP = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
}

def fetch_odds(api_key: str) -> dict:
    """Fetch MLB odds from The Odds API. Returns dict keyed by 'AWAY@HOME' team abbrs."""
    if not api_key:
        return {}

    cache_key = "odds_api_mlb_current"
    cached = get_cached(cache_key, "odds")
    if cached:
        return cached

    try:
        resp = requests.get(ODDS_API_BASE, params={
            "apiKey": api_key,
            "regions": "us",
            "markets": "h2h,totals",
            "oddsFormat": "american",
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        result = {}
        for game in data:
            home = ODDS_TEAM_MAP.get(game.get("home_team", ""), "")
            away = ODDS_TEAM_MAP.get(game.get("away_team", ""), "")
            if not home or not away:
                continue

            game_key = f"{away}@{home}"
            odds_data = {"home_team": home, "away_team": away}

            for bookmaker in game.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market["key"] == "h2h":
                        for outcome in market.get("outcomes", []):
                            team_abbr = ODDS_TEAM_MAP.get(outcome.get("name", ""), "")
                            if team_abbr == home:
                                odds_data["home_ml"] = outcome.get("price", 0)
                            elif team_abbr == away:
                                odds_data["away_ml"] = outcome.get("price", 0)
                    elif market["key"] == "totals":
                        for outcome in market.get("outcomes", []):
                            if outcome.get("name") == "Over":
                                odds_data["total"] = outcome.get("point", 8.5)
                break  # Use first bookmaker only

            result[game_key] = odds_data

        set_cached(cache_key, result, "odds")
        log.info(f"Fetched odds for {len(result)} games")
        return result
    except Exception as e:
        log.warning(f"Odds API error: {e}")
        return {}

def match_odds_to_games(odds: dict, games: list) -> dict:
    """Match odds data to MLB API game_pk values."""
    result = {}
    for game in games:
        away_abbr = game.get("away_team", {}).get("abbr", "")
        home_abbr = game.get("home_team", {}).get("abbr", "")
        game_key = f"{away_abbr}@{home_abbr}"
        if game_key in odds:
            result[str(game.get("game_pk", ""))] = odds[game_key]
    return result
