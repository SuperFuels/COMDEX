"""Small provider-neutral public-data tools owned by AION.

Connected models never call these endpoints directly. AION resolves the request,
performs the bounded read, records the named tool, and returns a deterministic
answer with the data source attached.
"""
from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


GEOCODING_ENDPOINT = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_ENDPOINT = "https://api.open-meteo.com/v1/forecast"


class LivePublicToolError(RuntimeError):
    pass


def _fetch_json(url: str, timeout: float = 15.0) -> Mapping[str, Any]:
    request = Request(url, headers={"User-Agent": "Tessaris-AION/1.0"}, method="GET")
    with urlopen(request, timeout=timeout) as response:  # nosec B310: fixed HTTPS authorities
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise LivePublicToolError("public_tool_invalid_response")
    return payload


def _location_from_prompt(prompt: str, *, kind: str) -> str:
    text = " ".join(str(prompt or "").strip().split())
    if kind == "weather":
        match = re.search(
            r"\bweather\s+(?:in|for|at)\s+(.+?)(?:\s+(?:today|tomorrow|tonight|this\s+(?:morning|afternoon|evening|week)))?[?.!]*$",
            text,
            flags=re.IGNORECASE,
        )
    else:
        match = re.search(
            r"\btime\s+(?:is\s+it\s+)?(?:in|at)\s+(.+?)[?.!]*$",
            text,
            flags=re.IGNORECASE,
        )
    return str(match.group(1) if match else "").strip(" ,?.!")


def _geocode(location: str, fetch_json: Callable[[str], Mapping[str, Any]]) -> Mapping[str, Any]:
    if not location:
        raise LivePublicToolError("location_missing")
    words = location.split()
    candidates = [location]
    # Open-Meteo often resolves "Arboleas" but not the natural-language form
    # "Arboleas Spain". Retry without a trailing country/region token while
    # preserving multi-word city names on the first attempt.
    for drop_count in range(1, min(3, len(words))):
        candidate = " ".join(words[:-drop_count]).strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        url = f"{GEOCODING_ENDPOINT}?{urlencode({'name': candidate, 'count': 1, 'language': 'en', 'format': 'json'})}"
        payload = fetch_json(url)
        results = payload.get("results")
        if isinstance(results, list) and results and isinstance(results[0], dict):
            return results[0]
    raise LivePublicToolError("location_not_found")


def _place_label(place: Mapping[str, Any]) -> str:
    parts = [str(place.get("name") or "").strip(), str(place.get("country") or "").strip()]
    return ", ".join(part for part in parts if part)


def current_time_answer(
    prompt: str,
    *,
    fetch_json: Callable[[str], Mapping[str, Any]] = _fetch_json,
    now: Callable[[ZoneInfo], datetime] = lambda timezone: datetime.now(timezone),
) -> dict[str, Any] | None:
    if not re.search(r"\b(?:current\s+)?time\b", str(prompt or ""), flags=re.IGNORECASE):
        return None
    location = _location_from_prompt(prompt, kind="time")
    if not location:
        return None
    place = _geocode(location, fetch_json)
    timezone_name = str(place.get("timezone") or "").strip()
    if not timezone_name:
        raise LivePublicToolError("timezone_not_found")
    local_now = now(ZoneInfo(timezone_name))
    label = _place_label(place) or location
    return {
        "text": f"The current time in {label} is {local_now.strftime('%H:%M')} on {local_now.strftime('%A, %d %B %Y')} ({timezone_name}).",
        "tool_name": "public.time.lookup",
        "source_url": GEOCODING_ENDPOINT,
        "location": label,
        "timezone": timezone_name,
    }


_WEATHER_CODES = {
    0: "clear skies",
    1: "mainly clear conditions",
    2: "partly cloudy conditions",
    3: "overcast conditions",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "light rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    95: "thunderstorms",
    96: "thunderstorms with hail",
    99: "severe thunderstorms with hail",
}


def weather_answer(
    prompt: str,
    *,
    fetch_json: Callable[[str], Mapping[str, Any]] = _fetch_json,
) -> dict[str, Any] | None:
    if not re.search(r"\bweather\b", str(prompt or ""), flags=re.IGNORECASE):
        return None
    location = _location_from_prompt(prompt, kind="weather")
    if not location:
        return None
    place = _geocode(location, fetch_json)
    params = {
        "latitude": place.get("latitude"),
        "longitude": place.get("longitude"),
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": 3,
    }
    forecast_url = f"{FORECAST_ENDPOINT}?{urlencode(params)}"
    payload = fetch_json(forecast_url)
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise LivePublicToolError("weather_forecast_missing")
    wants_tomorrow = bool(re.search(r"\btomorrow\b", prompt, flags=re.IGNORECASE))
    index = 1 if wants_tomorrow else 0

    def value(key: str, default: Any = None) -> Any:
        values = daily.get(key)
        return values[index] if isinstance(values, list) and len(values) > index else default

    code = int(value("weather_code", -1))
    condition = _WEATHER_CODES.get(code, "mixed conditions")
    label = _place_label(place) or location
    day_label = "Tomorrow" if wants_tomorrow else "Today"
    date_value = str(value("time", "")).strip()
    maximum = value("temperature_2m_max")
    minimum = value("temperature_2m_min")
    rain = value("precipitation_probability_max")
    wind = value("wind_speed_10m_max")
    return {
        "text": (
            f"{day_label} in {label} ({date_value}), expect {condition}. "
            f"The forecast range is {minimum}°C to {maximum}°C, with up to {rain}% chance of precipitation "
            f"and maximum winds around {wind} km/h.\n\n"
            f"Source: [Open-Meteo forecast]({forecast_url})"
        ),
        "tool_name": "public.weather.forecast",
        "source_url": forecast_url,
        "location": label,
        "forecast_date": date_value,
    }


def answer_live_public_question(prompt: str) -> dict[str, Any] | None:
    for resolver in (weather_answer, current_time_answer):
        answer = resolver(prompt)
        if answer is not None:
            return answer
    return None
