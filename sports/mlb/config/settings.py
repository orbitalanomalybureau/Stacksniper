"""
STACKSNIPER MLB — Global Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
HISTORICAL_DIR = DATA_DIR / "historical"
EXPORTS_DIR = DATA_DIR / "exports"

# Ensure dirs exist
for d in [CACHE_DIR, HISTORICAL_DIR, EXPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# API
MLB_API_BASE = os.getenv("MLB_STATS_API_BASE", "https://statsapi.mlb.com/api/v1")
BALLDONTLIE_KEY = os.getenv("BALLDONTLIE_API_KEY", "")

# Simulation
DEFAULT_SIM_COUNT = int(os.getenv("DEFAULT_SIM_COUNT", "500"))
MAX_SIM_COUNT = int(os.getenv("MAX_SIM_COUNT", "10000"))
AGENT_COUNT = int(os.getenv("AGENT_COUNT", "12"))

# Validation
if DEFAULT_SIM_COUNT < 1:
    DEFAULT_SIM_COUNT = 500
if MAX_SIM_COUNT < DEFAULT_SIM_COUNT:
    MAX_SIM_COUNT = DEFAULT_SIM_COUNT
if MAX_SIM_COUNT > 50000:
    MAX_SIM_COUNT = 50000

# Server
FLASK_PORT = int(os.getenv("FLASK_PORT", "5555"))
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "3333"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Security
API_TOKEN = os.getenv("API_TOKEN", "")

# DraftKings Classic MLB Roster
DK_SALARY_CAP = int(os.getenv("DK_SALARY_CAP", "50000"))
DK_ROSTER_SLOTS = ["P", "P", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF"]
DK_ROSTER_SIZE = 10
DK_MIN_PLAYERS_PER_GAME = 2

# Cache TTL (seconds)
CACHE_TTL = {
    "schedule": 3600,       # 1 hour
    "rosters": 7200,        # 2 hours
    "player_stats": 1800,   # 30 min
    "weather": 900,         # 15 min
    "odds": 300,            # 5 min
    "lineups": 600,         # 10 min
}
