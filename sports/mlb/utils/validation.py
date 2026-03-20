"""
STACKSNIPER MLB — Input Validation Utilities
"""
from datetime import date, datetime


class ValidationError(Exception):
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


def validate_date(date_str: str) -> date:
    if not date_str or not isinstance(date_str, str):
        raise ValidationError("Date is required.", "date")
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD.", "date")


def validate_sim_count(n) -> int:
    try:
        n = int(n)
    except (TypeError, ValueError):
        raise ValidationError("Sim count must be an integer.", "num_sims")
    if n < 50 or n > 10000:
        raise ValidationError("Sim count must be between 50 and 10000.", "num_sims")
    return n


def validate_num_lineups(n) -> int:
    try:
        n = int(n)
    except (TypeError, ValueError):
        raise ValidationError("Lineup count must be an integer.", "num_lineups")
    if n < 1 or n > 150:
        raise ValidationError("Lineup count must be between 1 and 150.", "num_lineups")
    return n


def validate_max_exposure(v) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValidationError("Max exposure must be a number.", "max_exposure")
    if v < 0.05 or v > 1.0:
        raise ValidationError("Max exposure must be between 0.05 and 1.0.", "max_exposure")
    return v
