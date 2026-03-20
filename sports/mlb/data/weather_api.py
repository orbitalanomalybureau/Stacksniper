"""
STACKSNIPER MLB — OpenWeatherMap Integration
"""
import requests
from sports.mlb.utils.cache import get_cached, set_cached
from sports.mlb.utils.logger import get_logger

log = get_logger("Weather")

WEATHER_API_BASE = "https://api.openweathermap.org/data/2.5/weather"

def fetch_weather(api_key: str, lat: float, lon: float) -> dict:
    """Fetch current weather for a location."""
    if not api_key:
        return {}

    cache_key = f"weather_{lat}_{lon}"
    cached = get_cached(cache_key, "weather")
    if cached:
        return cached

    try:
        resp = requests.get(WEATHER_API_BASE, params={
            "lat": lat, "lon": lon,
            "appid": api_key,
            "units": "imperial",
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        result = {
            "temp": str(round(data.get("main", {}).get("temp", 72))),
            "condition": data.get("weather", [{}])[0].get("main", ""),
            "wind": f"{round(data.get('wind', {}).get('speed', 0))} mph",
            "wind_speed": data.get("wind", {}).get("speed", 0),
            "wind_deg": data.get("wind", {}).get("deg", 0),
            "humidity": data.get("main", {}).get("humidity", 50),
            "clouds": data.get("clouds", {}).get("all", 0),
        }

        set_cached(cache_key, result, "weather")
        return result
    except Exception as e:
        log.warning(f"Weather API error: {e}")
        return {}
