"""Weather tool — Open-Meteo API integration (free, no API key)."""

from typing import Annotated

import httpx
from langchain_core.tools import tool

from config import settings


async def _geocode(location: str) -> dict | None:
    """Resolve a location name to lat/lon via Open-Meteo Geocoding API."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.OPEN_METEO_GEOCODING_URL}/search",
            params={"name": location, "count": 1, "language": "en"},
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results")
        if not results:
            return None
        r = results[0]
        return {
            "name": r.get("name", location),
            "country": r.get("country", ""),
            "lat": r["latitude"],
            "lon": r["longitude"],
        }


async def _get_forecast(lat: float, lon: float) -> dict:
    """Fetch current weather + 3-day forecast from Open-Meteo."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.OPEN_METEO_BASE_URL}/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min,weather_code",
                "timezone": "auto",
                "forecast_days": 3,
            },
        )
        resp.raise_for_status()
        return resp.json()


# WMO weather codes → human descriptions
_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


@tool
async def weather(
    location: Annotated[str, "City or place name, e.g. 'London' or 'New York'"],
) -> str:
    """Get current weather and a 3-day forecast for a location.

    Uses the free Open-Meteo API. Returns temperature, humidity, wind speed,
    and conditions.
    """
    geo = await _geocode(location)
    if not geo:
        return f"Could not find location: '{location}'. Try a different city name."

    forecast = await _get_forecast(geo["lat"], geo["lon"])
    current = forecast.get("current", {})
    daily = forecast.get("daily", {})

    wmo_code = current.get("weather_code", 0)
    condition = _WMO_CODES.get(wmo_code, "Unknown")

    lines = [
        f"Weather for {geo['name']}, {geo['country']}:",
        f"  Temperature: {current.get('temperature_2m', 'N/A')}°C",
        f"  Condition:   {condition}",
        f"  Humidity:    {current.get('relative_humidity_2m', 'N/A')}%",
        f"  Wind:        {current.get('wind_speed_10m', 'N/A')} km/h",
        "",
        "3-Day Forecast:",
    ]
    dates = daily.get("time", [])
    maxs = daily.get("temperature_2m_max", [])
    mins = daily.get("temperature_2m_min", [])
    codes = daily.get("weather_code", [])

    for i, date in enumerate(dates):
        cond = _WMO_CODES.get(codes[i], "Unknown") if i < len(codes) else "?"
        hi = maxs[i] if i < len(maxs) else "?"
        lo = mins[i] if i < len(mins) else "?"
        lines.append(f"  {date}: {lo}°C – {hi}°C, {cond}")

    return "\n".join(lines)
