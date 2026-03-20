"""
STACKSNIPER MLB — Team Mappings & Park Factors
"""

MLB_TEAMS = {
    108: {"name": "Los Angeles Angels", "abbr": "LAA", "park": "Angel Stadium", "league": "AL", "dome": False, "retractable_roof": False, "lat": 33.800, "lng": -117.883, "elevation_ft": 160, "field_orientation_deg": 68, "dimensions": {"lf": 330, "cf": 396, "rf": 330}},
    109: {"name": "Arizona Diamondbacks", "abbr": "ARI", "park": "Chase Field", "league": "NL", "dome": False, "retractable_roof": True, "lat": 33.445, "lng": -112.067, "elevation_ft": 1100, "field_orientation_deg": 0, "dimensions": {"lf": 330, "cf": 407, "rf": 334}},
    110: {"name": "Baltimore Orioles", "abbr": "BAL", "park": "Camden Yards", "league": "AL", "dome": False, "retractable_roof": False, "lat": 39.284, "lng": -76.622, "elevation_ft": 30, "field_orientation_deg": 68, "dimensions": {"lf": 333, "cf": 410, "rf": 318}},
    111: {"name": "Boston Red Sox", "abbr": "BOS", "park": "Fenway Park", "league": "AL", "dome": False, "retractable_roof": False, "lat": 42.346, "lng": -71.098, "elevation_ft": 20, "field_orientation_deg": 67, "dimensions": {"lf": 310, "cf": 390, "rf": 302}},
    112: {"name": "Chicago Cubs", "abbr": "CHC", "park": "Wrigley Field", "league": "NL", "dome": False, "retractable_roof": False, "lat": 41.948, "lng": -87.656, "elevation_ft": 600, "field_orientation_deg": 54, "dimensions": {"lf": 355, "cf": 400, "rf": 353}},
    113: {"name": "Cincinnati Reds", "abbr": "CIN", "park": "Great American Ball Park", "league": "NL", "dome": False, "retractable_roof": False, "lat": 39.097, "lng": -84.508, "elevation_ft": 490, "field_orientation_deg": 75, "dimensions": {"lf": 328, "cf": 404, "rf": 325}},
    114: {"name": "Cleveland Guardians", "abbr": "CLE", "park": "Progressive Field", "league": "AL", "dome": False, "retractable_roof": False, "lat": 41.496, "lng": -81.685, "elevation_ft": 660, "field_orientation_deg": 55, "dimensions": {"lf": 325, "cf": 405, "rf": 325}},
    115: {"name": "Colorado Rockies", "abbr": "COL", "park": "Coors Field", "league": "NL", "dome": False, "retractable_roof": False, "lat": 39.756, "lng": -104.994, "elevation_ft": 5280, "field_orientation_deg": 68, "dimensions": {"lf": 347, "cf": 415, "rf": 350}},
    116: {"name": "Detroit Tigers", "abbr": "DET", "park": "Comerica Park", "league": "AL", "dome": False, "retractable_roof": False, "lat": 42.339, "lng": -83.049, "elevation_ft": 600, "field_orientation_deg": 54, "dimensions": {"lf": 345, "cf": 420, "rf": 330}},
    117: {"name": "Houston Astros", "abbr": "HOU", "park": "Minute Maid Park", "league": "AL", "dome": False, "retractable_roof": True, "lat": 29.757, "lng": -95.355, "elevation_ft": 40, "field_orientation_deg": 62, "dimensions": {"lf": 315, "cf": 409, "rf": 326}},
    118: {"name": "Kansas City Royals", "abbr": "KC", "park": "Kauffman Stadium", "league": "AL", "dome": False, "retractable_roof": False, "lat": 39.051, "lng": -94.480, "elevation_ft": 820, "field_orientation_deg": 70, "dimensions": {"lf": 330, "cf": 410, "rf": 330}},
    119: {"name": "Los Angeles Dodgers", "abbr": "LAD", "park": "Dodger Stadium", "league": "NL", "dome": False, "retractable_roof": False, "lat": 34.074, "lng": -118.240, "elevation_ft": 515, "field_orientation_deg": 55, "dimensions": {"lf": 330, "cf": 395, "rf": 330}},
    120: {"name": "Washington Nationals", "abbr": "WSH", "park": "Nationals Park", "league": "NL", "dome": False, "retractable_roof": False, "lat": 38.873, "lng": -77.008, "elevation_ft": 25, "field_orientation_deg": 72, "dimensions": {"lf": 336, "cf": 403, "rf": 335}},
    121: {"name": "New York Mets", "abbr": "NYM", "park": "Citi Field", "league": "NL", "dome": False, "retractable_roof": False, "lat": 40.757, "lng": -73.846, "elevation_ft": 15, "field_orientation_deg": 68, "dimensions": {"lf": 335, "cf": 408, "rf": 330}},
    133: {"name": "Oakland Athletics", "abbr": "OAK", "park": "Sutter Health Park", "league": "AL", "dome": False, "retractable_roof": False, "lat": 38.580, "lng": -121.508, "elevation_ft": 25, "field_orientation_deg": 60, "dimensions": {"lf": 330, "cf": 403, "rf": 325}},
    134: {"name": "Pittsburgh Pirates", "abbr": "PIT", "park": "PNC Park", "league": "NL", "dome": False, "retractable_roof": False, "lat": 40.447, "lng": -80.006, "elevation_ft": 730, "field_orientation_deg": 60, "dimensions": {"lf": 325, "cf": 399, "rf": 320}},
    135: {"name": "San Diego Padres", "abbr": "SD", "park": "Petco Park", "league": "NL", "dome": False, "retractable_roof": False, "lat": 32.707, "lng": -117.157, "elevation_ft": 15, "field_orientation_deg": 67, "dimensions": {"lf": 336, "cf": 396, "rf": 322}},
    136: {"name": "Seattle Mariners", "abbr": "SEA", "park": "T-Mobile Park", "league": "AL", "dome": False, "retractable_roof": True, "lat": 47.591, "lng": -122.333, "elevation_ft": 20, "field_orientation_deg": 68, "dimensions": {"lf": 331, "cf": 405, "rf": 326}},
    137: {"name": "San Francisco Giants", "abbr": "SF", "park": "Oracle Park", "league": "NL", "dome": False, "retractable_roof": False, "lat": 37.778, "lng": -122.389, "elevation_ft": 10, "field_orientation_deg": 62, "dimensions": {"lf": 339, "cf": 399, "rf": 309}},
    138: {"name": "St. Louis Cardinals", "abbr": "STL", "park": "Busch Stadium", "league": "NL", "dome": False, "retractable_roof": False, "lat": 38.623, "lng": -90.193, "elevation_ft": 465, "field_orientation_deg": 55, "dimensions": {"lf": 336, "cf": 400, "rf": 335}},
    139: {"name": "Tampa Bay Rays", "abbr": "TB", "park": "Tropicana Field", "league": "AL", "dome": True, "retractable_roof": False, "lat": 27.768, "lng": -82.653, "elevation_ft": 45, "field_orientation_deg": 0, "dimensions": {"lf": 315, "cf": 404, "rf": 322}},
    140: {"name": "Texas Rangers", "abbr": "TEX", "park": "Globe Life Field", "league": "AL", "dome": False, "retractable_roof": True, "lat": 32.747, "lng": -97.084, "elevation_ft": 545, "field_orientation_deg": 58, "dimensions": {"lf": 329, "cf": 407, "rf": 326}},
    141: {"name": "Toronto Blue Jays", "abbr": "TOR", "park": "Rogers Centre", "league": "AL", "dome": False, "retractable_roof": True, "lat": 43.641, "lng": -79.389, "elevation_ft": 270, "field_orientation_deg": 0, "dimensions": {"lf": 328, "cf": 400, "rf": 328}},
    142: {"name": "Minnesota Twins", "abbr": "MIN", "park": "Target Field", "league": "AL", "dome": False, "retractable_roof": False, "lat": 44.982, "lng": -93.278, "elevation_ft": 815, "field_orientation_deg": 52, "dimensions": {"lf": 339, "cf": 404, "rf": 328}},
    143: {"name": "Philadelphia Phillies", "abbr": "PHI", "park": "Citizens Bank Park", "league": "NL", "dome": False, "retractable_roof": False, "lat": 39.906, "lng": -75.167, "elevation_ft": 20, "field_orientation_deg": 68, "dimensions": {"lf": 329, "cf": 401, "rf": 330}},
    144: {"name": "Atlanta Braves", "abbr": "ATL", "park": "Truist Park", "league": "NL", "dome": False, "retractable_roof": False, "lat": 33.891, "lng": -84.468, "elevation_ft": 1050, "field_orientation_deg": 65, "dimensions": {"lf": 335, "cf": 400, "rf": 325}},
    145: {"name": "Chicago White Sox", "abbr": "CWS", "park": "Guaranteed Rate Field", "league": "AL", "dome": False, "retractable_roof": False, "lat": 41.830, "lng": -87.634, "elevation_ft": 595, "field_orientation_deg": 67, "dimensions": {"lf": 330, "cf": 400, "rf": 335}},
    146: {"name": "Miami Marlins", "abbr": "MIA", "park": "LoanDepot Park", "league": "NL", "dome": False, "retractable_roof": True, "lat": 25.778, "lng": -80.220, "elevation_ft": 10, "field_orientation_deg": 67, "dimensions": {"lf": 344, "cf": 407, "rf": 335}},
    147: {"name": "New York Yankees", "abbr": "NYY", "park": "Yankee Stadium", "league": "AL", "dome": False, "retractable_roof": False, "lat": 40.829, "lng": -73.927, "elevation_ft": 15, "field_orientation_deg": 67, "dimensions": {"lf": 318, "cf": 408, "rf": 314}},
    158: {"name": "Milwaukee Brewers", "abbr": "MIL", "park": "American Family Field", "league": "NL", "dome": False, "retractable_roof": True, "lat": 43.028, "lng": -87.971, "elevation_ft": 640, "field_orientation_deg": 55, "dimensions": {"lf": 344, "cf": 400, "rf": 345}},
}

# Park factors (1.0 = neutral, >1.0 = hitter-friendly, <1.0 = pitcher-friendly)
PARK_FACTORS = {
    "COL": {"runs": 1.38, "hr": 1.30, "hits": 1.15, "doubles": 1.20, "triples": 1.50},
    "CIN": {"runs": 1.12, "hr": 1.18, "hits": 1.05, "doubles": 1.02, "triples": 0.90},
    "BOS": {"runs": 1.10, "hr": 0.95, "hits": 1.08, "doubles": 1.35, "triples": 0.55},
    "NYY": {"runs": 1.08, "hr": 1.22, "hits": 1.00, "doubles": 0.92, "triples": 0.70},
    "PHI": {"runs": 1.06, "hr": 1.12, "hits": 1.02, "doubles": 1.00, "triples": 0.85},
    "TEX": {"runs": 1.04, "hr": 1.08, "hits": 1.02, "doubles": 1.00, "triples": 0.90},
    "CHC": {"runs": 1.03, "hr": 1.10, "hits": 1.00, "doubles": 1.00, "triples": 0.80},
    "ATL": {"runs": 1.02, "hr": 1.05, "hits": 1.00, "doubles": 1.00, "triples": 1.00},
    "MIL": {"runs": 1.01, "hr": 1.08, "hits": 0.98, "doubles": 1.00, "triples": 0.85},
    "MIN": {"runs": 1.00, "hr": 1.05, "hits": 1.00, "doubles": 1.00, "triples": 0.90},
    "HOU": {"runs": 1.00, "hr": 1.05, "hits": 1.00, "doubles": 0.98, "triples": 0.85},
    "CLE": {"runs": 0.98, "hr": 0.95, "hits": 1.00, "doubles": 1.00, "triples": 1.00},
    "BAL": {"runs": 0.98, "hr": 1.08, "hits": 0.98, "doubles": 0.95, "triples": 0.80},
    "WSH": {"runs": 0.98, "hr": 1.00, "hits": 0.98, "doubles": 1.00, "triples": 0.90},
    "DET": {"runs": 0.97, "hr": 0.92, "hits": 1.00, "doubles": 1.02, "triples": 1.00},
    "ARI": {"runs": 0.97, "hr": 1.00, "hits": 0.98, "doubles": 1.02, "triples": 1.10},
    "STL": {"runs": 0.96, "hr": 0.95, "hits": 0.98, "doubles": 1.00, "triples": 1.00},
    "LAD": {"runs": 0.95, "hr": 0.92, "hits": 0.98, "doubles": 1.00, "triples": 0.90},
    "LAA": {"runs": 0.95, "hr": 0.95, "hits": 0.98, "doubles": 0.98, "triples": 0.90},
    "TOR": {"runs": 0.95, "hr": 1.05, "hits": 0.95, "doubles": 0.95, "triples": 0.60},
    "CWS": {"runs": 0.95, "hr": 1.02, "hits": 0.95, "doubles": 0.98, "triples": 0.80},
    "KC":  {"runs": 0.94, "hr": 0.88, "hits": 1.00, "doubles": 1.05, "triples": 1.20},
    "PIT": {"runs": 0.93, "hr": 0.88, "hits": 0.98, "doubles": 1.00, "triples": 1.00},
    "NYM": {"runs": 0.92, "hr": 0.90, "hits": 0.96, "doubles": 0.98, "triples": 0.85},
    "TB":  {"runs": 0.92, "hr": 0.95, "hits": 0.95, "doubles": 0.95, "triples": 0.70},
    "SD":  {"runs": 0.90, "hr": 0.85, "hits": 0.95, "doubles": 0.98, "triples": 1.00},
    "SF":  {"runs": 0.88, "hr": 0.82, "hits": 0.95, "doubles": 1.00, "triples": 1.10},
    "SEA": {"runs": 0.88, "hr": 0.85, "hits": 0.95, "doubles": 0.98, "triples": 0.85},
    "MIA": {"runs": 0.87, "hr": 0.80, "hits": 0.95, "doubles": 1.00, "triples": 0.90},
    "OAK": {"runs": 0.95, "hr": 0.90, "hits": 0.95, "doubles": 0.95, "triples": 0.90},
}

def get_park_factor(team_abbr: str, stat: str = "runs") -> float:
    """Get park factor for a team's home park."""
    factors = PARK_FACTORS.get(team_abbr, {})
    return factors.get(stat, 1.0)

def get_venue_info(team_abbr: str) -> dict:
    """Get venue info for a team including dome/roof status and coordinates."""
    for team_id, info in MLB_TEAMS.items():
        if info["abbr"] == team_abbr:
            return {
                "dome": info.get("dome", False),
                "retractable_roof": info.get("retractable_roof", False),
                "lat": info.get("lat", 0),
                "lng": info.get("lng", 0),
                "park": info.get("park", ""),
            }
    return {"dome": False, "retractable_roof": False, "lat": 0, "lng": 0}

def is_indoor_game(team_abbr: str) -> bool:
    """Check if a game at this team's park would be indoors."""
    info = get_venue_info(team_abbr)
    return info["dome"] or info["retractable_roof"]

def get_elevation_factor(team_abbr: str) -> float:
    """HR factor from altitude. Coors = ~1.10"""
    team = MLB_TEAMS.get(team_abbr, {})
    if not team:
        # Lookup by abbreviation
        for tid, t in MLB_TEAMS.items():
            if t["abbr"] == team_abbr:
                team = t
                break
    elevation = team.get("elevation_ft", 0)
    return 1.0 + max(0, elevation - 500) * 0.00002

def get_wind_impact(team_abbr: str, wind_speed: float, wind_deg: float) -> dict:
    """Calculate wind impact on HR/hits based on field orientation."""
    team = MLB_TEAMS.get(team_abbr, {})
    if not team:
        # Lookup by abbreviation
        for tid, t in MLB_TEAMS.items():
            if t["abbr"] == team_abbr:
                team = t
                break
    orientation = team.get("field_orientation_deg", 0)
    # Wind blowing out to CF = boost HR
    relative_angle = abs((wind_deg - orientation + 180) % 360 - 180)
    if relative_angle < 45:  # Blowing out
        hr_factor = 1.0 + wind_speed * 0.008
    elif relative_angle > 135:  # Blowing in
        hr_factor = 1.0 - wind_speed * 0.006
    else:  # Crosswind
        hr_factor = 1.0
    return {"hr_factor": round(hr_factor, 3), "relative_angle": round(relative_angle, 1)}
