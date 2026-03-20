"""
STACKSNIPER MLB — MLB Sport Configuration (v6 Sprint 5.4)
Concrete implementation of SportConfig for Major League Baseball.
Wraps existing config modules without changing their import paths.
"""
from sports.mlb.config.sports.base import SportConfig
from sports.mlb.config.dk_scoring import HITTER_SCORING, PITCHER_SCORING, POSITION_MAP
from sports.mlb.config.settings import DK_ROSTER_SLOTS
from sports.mlb.config.team_mappings import MLB_TEAMS, PARK_FACTORS


class MLBConfig(SportConfig):
    SALARY_CAP = 50000

    def get_scoring_rules(self):
        return {"hitter": HITTER_SCORING, "pitcher": PITCHER_SCORING}

    def get_roster_slots(self):
        return DK_ROSTER_SLOTS

    def get_position_map(self):
        return POSITION_MAP

    def get_salary_cap(self):
        return self.SALARY_CAP

    def get_park_factors(self):
        return PARK_FACTORS

    def get_team_mappings(self):
        return MLB_TEAMS
