from datetime import datetime
from zoneinfo import ZoneInfo

from backend.modules.aion_fabric.live_public_tools import (
    current_time_answer,
    weather_answer,
)


def test_current_time_uses_resolved_timezone() -> None:
    def fetch_json(_url: str):
        return {
            "results": [{
                "name": "Los Angeles",
                "country": "United States",
                "timezone": "America/Los_Angeles",
            }]
        }

    result = current_time_answer(
        "what is the time in los angeles",
        fetch_json=fetch_json,
        now=lambda timezone: datetime(2026, 10, 7, 15, 42, tzinfo=timezone),
    )
    assert result is not None
    assert "15:42" in result["text"]
    assert "Los Angeles, United States" in result["text"]
    assert result["tool_name"] == "public.time.lookup"


def test_weather_tomorrow_uses_next_forecast_day() -> None:
    def fetch_json(url: str):
        if "geocoding-api" in url:
            return {
                "results": [{
                    "name": "Arboleas",
                    "country": "Spain",
                    "latitude": 37.35,
                    "longitude": -2.07,
                    "timezone": "Europe/Madrid",
                }]
            }
        return {
            "daily": {
                "time": ["2026-10-08", "2026-10-09"],
                "weather_code": [0, 61],
                "temperature_2m_max": [25, 22],
                "temperature_2m_min": [14, 12],
                "precipitation_probability_max": [5, 70],
                "wind_speed_10m_max": [12, 20],
            }
        }

    result = weather_answer(
        "what is the weather in arboleas spain tomorrow",
        fetch_json=fetch_json,
    )
    assert result is not None
    assert "Tomorrow in Arboleas, Spain (2026-10-09)" in result["text"]
    assert "12°C to 22°C" in result["text"]
    assert "70% chance" in result["text"]
    assert result["tool_name"] == "public.weather.forecast"
