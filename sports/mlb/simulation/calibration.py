"""
STACKSNIPER MLB — Agent Calibration System
Compares projections to actuals and adjusts agent weights for improved accuracy.
"""
import json
from pathlib import Path
from datetime import date
from typing import Optional
from sports.mlb.utils.logger import get_logger

log = get_logger("Calibration")

CALIBRATION_PATH = Path(__file__).parent.parent / "data" / "calibration.json"


class AgentCalibrator:
    """Adjusts agent weights based on historical accuracy."""

    def __init__(self):
        self.calibration = self._load_calibration()

    def _load_calibration(self) -> dict:
        if CALIBRATION_PATH.exists():
            try:
                with open(CALIBRATION_PATH) as f:
                    return json.load(f)
            except Exception as e:
                log.error(f"Failed to load calibration: {e}")
        return {"agent_weights": {}, "history": [], "last_calibrated": None}

    def _save_calibration(self):
        try:
            CALIBRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CALIBRATION_PATH, "w") as f:
                json.dump(self.calibration, f, indent=2, default=str)
            log.info("Calibration data saved")
        except Exception as e:
            log.error(f"Failed to save calibration: {e}")

    def get_agent_weight(self, agent_name: str) -> Optional[float]:
        """Get calibrated weight for an agent, or None if no calibration."""
        return self.calibration.get("agent_weights", {}).get(agent_name)

    def run_daily_calibration(self, projections: list, actuals: dict) -> dict:
        """
        Compare projections to actual results and adjust agent weights.

        Args:
            projections: List of player projection dicts with 'agent_opinions'
            actuals: Dict mapping player_id -> actual DK points

        Returns:
            Summary dict with accuracy metrics per agent
        """
        if not projections or not actuals:
            return {"error": "Insufficient data for calibration"}

        agent_errors = {}  # agent_name -> list of (predicted_impact, actual_error)

        for proj in projections:
            player_id = proj.get("player_id")
            actual_pts = actuals.get(player_id)
            if actual_pts is None:
                continue

            projected_pts = proj.get("dk_points", 0)
            base_error = abs(projected_pts - actual_pts)

            for opinion in proj.get("agent_opinions", []):
                agent_name = opinion.get("agent", "")
                confidence = opinion.get("confidence", 0.5)

                if agent_name not in agent_errors:
                    agent_errors[agent_name] = []
                agent_errors[agent_name].append({
                    "error": base_error,
                    "confidence": confidence,
                })

        # Compute accuracy score per agent and adjust weights
        results = {}
        weights = self.calibration.get("agent_weights", {})

        for agent_name, errors in agent_errors.items():
            avg_error = sum(e["error"] for e in errors) / len(errors) if errors else 999
            avg_confidence = sum(e["confidence"] for e in errors) / len(errors) if errors else 0.5

            # Lower error = better accuracy = higher weight
            current_weight = weights.get(agent_name, 1.0)
            if avg_error < 3.0:
                new_weight = min(2.0, current_weight * 1.05)  # +5%
            elif avg_error > 6.0:
                new_weight = max(0.3, current_weight * 0.95)  # -5%
            else:
                new_weight = current_weight

            weights[agent_name] = round(new_weight, 3)
            results[agent_name] = {
                "avg_error": round(avg_error, 2),
                "avg_confidence": round(avg_confidence, 3),
                "sample_size": len(errors),
                "old_weight": round(current_weight, 3),
                "new_weight": round(new_weight, 3),
            }

        self.calibration["agent_weights"] = weights
        self.calibration["last_calibrated"] = str(date.today())
        self.calibration["history"].append({
            "date": str(date.today()),
            "agents": results,
        })
        # Keep only last 30 days of history
        self.calibration["history"] = self.calibration["history"][-30:]
        self._save_calibration()

        log.info(f"Calibration complete: {len(results)} agents evaluated")
        return {"agents": results, "date": str(date.today())}


# Module singleton
calibrator = AgentCalibrator()
