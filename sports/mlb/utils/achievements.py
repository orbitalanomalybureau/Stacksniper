"""
STACKSNIPER MLB — Achievement System
Gamification layer for user engagement and retention.
"""

ACHIEVEMENT_DEFS = {
    "first_sim": {
        "name": "First Simulation",
        "icon": "\U0001f3af",
        "description": "Run your first simulation",
        "check": lambda u: u.get("total_sims", 0) >= 1,
    },
    "sim_master": {
        "name": "Simulation Master",
        "icon": "\U0001f52c",
        "description": "Run 100 simulations",
        "check": lambda u: u.get("total_sims", 0) >= 100,
    },
    "five_day_streak": {
        "name": "5-Day Streak",
        "icon": "\U0001f525",
        "description": "Use STACKSNIPER 5 days in a row",
        "check": lambda u: u.get("consecutive_days", 0) >= 5,
    },
    "deep_sim": {
        "name": "Deep Dive",
        "icon": "\U0001f30a",
        "description": "Run a 5000+ simulation",
        "check": lambda u: u.get("max_sims", 0) >= 5000,
    },
    "first_win": {
        "name": "First Win",
        "icon": "\U0001f3c6",
        "description": "Log your first contest win",
        "check": lambda u: u.get("wins", 0) >= 1,
    },
    "ai_power_user": {
        "name": "AI Power User",
        "icon": "\U0001f916",
        "description": "Send 50 CoPilot messages",
        "check": lambda u: u.get("ai_chats", 0) >= 50,
    },
    "lineup_king": {
        "name": "Lineup King",
        "icon": "\U0001f451",
        "description": "Generate 500 lineups",
        "check": lambda u: u.get("lineups_generated", 0) >= 500,
    },
    "calibrator": {
        "name": "Calibrator",
        "icon": "\u2699\ufe0f",
        "description": "Run agent calibration",
        "check": lambda u: u.get("calibrations", 0) >= 1,
    },
}


class AchievementSystem:
    """Checks and manages user achievements."""

    def check_achievements(self, user_data, existing_achievements):
        """Check which new achievements the user has unlocked.

        Args:
            user_data: dict with user stats (total_sims, wins, etc.)
            existing_achievements: list of dicts with 'achievement_key' field

        Returns:
            List of newly unlocked achievement dicts.
        """
        newly_unlocked = []
        existing_keys = set(a.get("achievement_key") for a in existing_achievements)
        for key, definition in ACHIEVEMENT_DEFS.items():
            if key not in existing_keys and definition["check"](user_data):
                newly_unlocked.append({"key": key, **definition})
        return newly_unlocked

    def get_all_achievements(self, user_data, existing_achievements):
        """Get all achievements with locked/unlocked status.

        Args:
            user_data: dict with user stats
            existing_achievements: list of dicts with 'achievement_key' field

        Returns:
            List of all achievement dicts with 'unlocked' boolean.
        """
        existing_keys = set(a.get("achievement_key") for a in existing_achievements)
        result = []
        for key, defn in ACHIEVEMENT_DEFS.items():
            result.append({
                "key": key,
                "name": defn["name"],
                "icon": defn["icon"],
                "description": defn["description"],
                "unlocked": key in existing_keys,
            })
        return result


achievement_system = AchievementSystem()
