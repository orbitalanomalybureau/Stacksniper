"""
STACKSNIPER MLB — Weather Impact Agent
Adjusts projections based on weather conditions.
"""
import re
from sports.mlb.agents.base_agent import BaseAgent, AgentOpinion

class WeatherAgent(BaseAgent):
    """Adjusts projections for weather impact on gameplay."""
    def __init__(self):
        super().__init__("WeatherAnalyst", "environment", weight=0.8)

    def analyze(self, context: dict) -> AgentOpinion:
        weather = context.get("weather", {})
        temp = self._parse_temp(weather.get("temp", "72"))
        wind = weather.get("wind", "")
        condition = weather.get("condition", "").lower()
        is_dome = context.get("is_dome", False)

        if is_dome:
            return AgentOpinion(
                agent_name=self.name,
                agent_type=self.agent_type,
                confidence=0.95,
                weight=self.weight,
                projection={"weather_impact": 1.0},
                reasoning="Dome/retractable roof — no weather impact",
                adjustments={"runs_multiplier": 1.0, "hr_multiplier": 1.0},
            )

        temp_factor = 1.0
        if temp >= 85:
            temp_factor = 1.08
        elif temp >= 75:
            temp_factor = 1.03
        elif temp <= 50:
            temp_factor = 0.90
        elif temp <= 60:
            temp_factor = 0.95

        wind_factor = 1.0
        wind_speed = self._parse_wind_speed(wind)
        if "out" in wind.lower() and wind_speed >= 10:
            wind_factor = 1.05 + (wind_speed - 10) * 0.01
        elif "in" in wind.lower() and wind_speed >= 10:
            wind_factor = 0.92 - (wind_speed - 10) * 0.01

        condition_factor = 1.0
        if any(w in condition for w in ["rain", "drizzle", "shower"]):
            condition_factor = 0.92
        elif "cloudy" in condition:
            condition_factor = 0.98

        total_impact = round(temp_factor * wind_factor * condition_factor, 3)

        return AgentOpinion(
            agent_name=self.name,
            agent_type=self.agent_type,
            confidence=0.7,
            weight=self.weight,
            projection={"weather_impact": total_impact, "temp": temp,
                         "wind_speed": wind_speed},
            reasoning=f"Temp {temp}°F, wind: {wind}, condition: {condition}",
            adjustments={
                "runs_multiplier": total_impact,
                "hr_multiplier": round(temp_factor * wind_factor, 3),
            },
        )

    def _parse_temp(self, temp_str) -> int:
        try:
            return int(re.sub(r'[^\d]', '', str(temp_str))[:3])
        except (ValueError, IndexError):
            return 72

    def _parse_wind_speed(self, wind_str: str) -> int:
        try:
            match = re.search(r'(\d+)', wind_str)
            return int(match.group(1)) if match else 0
        except (ValueError, AttributeError):
            return 0
