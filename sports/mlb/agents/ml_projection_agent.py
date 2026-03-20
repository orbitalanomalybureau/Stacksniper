"""
STACKSNIPER MLB — ML Projection Agent
Uses scikit-learn GradientBoostingRegressor for data-driven DFS projections.
Trained on historical data, used as an optional high-weight agent in the pool.
"""
import pickle
import numpy as np
from pathlib import Path
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion
from sports.mlb.utils.logger import get_logger

log = get_logger("MLAgent")

MODEL_DIR = Path(__file__).parent.parent / "data" / "models"
HITTER_MODEL_PATH = MODEL_DIR / "hitter_xgb.pkl"
PITCHER_MODEL_PATH = MODEL_DIR / "pitcher_xgb.pkl"


class MLProjectionAgent(BaseAgent):
    """ML-based projection agent using gradient boosting."""

    def __init__(self):
        super().__init__(
            name="MLProjection",
            agent_type="ml",
            weight=2.0,
        )
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        self.hitter_model = self._load_model(HITTER_MODEL_PATH)
        self.pitcher_model = self._load_model(PITCHER_MODEL_PATH)
        self._is_trained = self.hitter_model is not None or self.pitcher_model is not None
        if self._is_trained:
            log.info("ML models loaded successfully")
        else:
            log.info("No trained ML models found — agent will be inactive until trained")

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    def _load_model(self, path: Path):
        if path.exists():
            try:
                with open(path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                log.error(f"Failed to load model {path}: {e}")
        return None

    def _save_model(self, model, path: Path):
        try:
            with open(path, "wb") as f:
                pickle.dump(model, f)
            log.info(f"Model saved to {path}")
        except Exception as e:
            log.error(f"Failed to save model {path}: {e}")

    def analyze(self, context: dict) -> AgentOpinion:
        """Produce ML-based projection adjustments."""
        if not self._is_trained:
            return AgentOpinion(
                agent_name=self.name,
                agent_type=self.agent_type,
                confidence=0.0,
                weight=0.0,
                projection={},
                adjustments={},
                reasoning="ML model not yet trained",
            )

        position = context.get("position", "")
        features = self._extract_features(context)

        if position in ("SP", "RP", "P") and self.pitcher_model is not None:
            predicted = self._predict(self.pitcher_model, features)
            multiplier = self._compute_multiplier(predicted, context)
            return AgentOpinion(
                agent_name=self.name,
                agent_type=self.agent_type,
                confidence=0.75,
                weight=self.weight,
                projection={"ml_predicted_dkfp": round(predicted, 2)},
                adjustments={"runs_multiplier": multiplier},
                reasoning=f"ML model predicts {predicted:.1f} DKFP",
            )
        elif self.hitter_model is not None:
            predicted = self._predict(self.hitter_model, features)
            multiplier = self._compute_multiplier(predicted, context)
            return AgentOpinion(
                agent_name=self.name,
                agent_type=self.agent_type,
                confidence=0.75,
                weight=self.weight,
                projection={"ml_predicted_dkfp": round(predicted, 2)},
                adjustments={
                    "runs_multiplier": multiplier,
                    "hr_multiplier": multiplier,
                    "hits_multiplier": multiplier,
                },
                reasoning=f"ML model predicts {predicted:.1f} DKFP",
            )

        return AgentOpinion(
            agent_name=self.name, agent_type=self.agent_type,
            confidence=0.0, weight=0.0, projection={}, adjustments={},
            reasoning="No applicable model",
        )

    def _extract_features(self, context: dict) -> np.ndarray:
        """Extract feature vector from player context."""
        season = context.get("season_stats", {})
        recent = context.get("recent_stats", {})
        matchup = context.get("matchup", {})
        env = context.get("environment", {})

        features = [
            season.get("avg", 0.250),
            season.get("obp", 0.320),
            season.get("slg", 0.400),
            season.get("woba", 0.320),
            season.get("k_rate", 0.22),
            season.get("bb_rate", 0.08),
            season.get("hr_rate", 0.03),
            season.get("sb_rate", 0.02),
            recent.get("rolling_10_woba", season.get("woba", 0.320)),
            recent.get("rolling_30_woba", season.get("woba", 0.320)),
            recent.get("form_factor", 1.0),
            matchup.get("bvp_avg", 0.0),
            1.0 if matchup.get("platoon_advantage", False) else 0.0,
            context.get("lineup_position", 5),
            env.get("park_factor_runs", 1.0),
            env.get("park_factor_hr", 1.0),
            env.get("weather_impact", 1.0),
            env.get("team_implied_total", 4.5),
            env.get("opp_pitcher_era", 4.00),
            season.get("games_played", 80),
            context.get("rest_days", 0),
        ]
        return np.array(features).reshape(1, -1)

    def _predict(self, model, features: np.ndarray) -> float:
        try:
            return float(model.predict(features)[0])
        except Exception as e:
            log.error(f"Prediction failed: {e}")
            return 0.0

    def _compute_multiplier(self, predicted: float, context: dict) -> float:
        """Compute adjustment multiplier based on ML prediction vs baseline."""
        baseline = context.get("baseline_dkfp", 7.0)
        if baseline <= 0:
            return 1.0
        ratio = predicted / baseline
        # Clamp to reasonable range
        return max(0.7, min(1.4, ratio))

    def train_hitter_model(self, X: np.ndarray, y: np.ndarray):
        """Train hitter model on historical data."""
        from sklearn.ensemble import GradientBoostingRegressor
        log.info(f"Training hitter model on {len(X)} samples...")
        model = GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            subsample=0.8, random_state=42,
        )
        model.fit(X, y)
        self.hitter_model = model
        self._is_trained = True
        self._save_model(model, HITTER_MODEL_PATH)
        log.info(f"Hitter model trained (R²={model.score(X, y):.3f})")
        return model.score(X, y)

    def train_pitcher_model(self, X: np.ndarray, y: np.ndarray):
        """Train pitcher model on historical data."""
        from sklearn.ensemble import GradientBoostingRegressor
        log.info(f"Training pitcher model on {len(X)} samples...")
        model = GradientBoostingRegressor(
            n_estimators=150, max_depth=3, learning_rate=0.1,
            subsample=0.8, random_state=42,
        )
        model.fit(X, y)
        self.pitcher_model = model
        self._is_trained = True
        self._save_model(model, PITCHER_MODEL_PATH)
        log.info(f"Pitcher model trained (R²={model.score(X, y):.3f})")
        return model.score(X, y)
