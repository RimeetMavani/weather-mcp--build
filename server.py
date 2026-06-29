"""
Weather MCP Server — 5 tools, 5 live public weather APIs, SSE transport.

Tools (no API key needed): Open-Meteo, wttr.in, 7Timer!
Tools (free API key):       OpenWeatherMap, WeatherAPI.com
"""

from __future__ import annotations

import os
from html import escape
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Always load .env from this project folder (not only the current working directory)
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY", "").strip()

mcp = FastMCP(
    "Weather MCP Server",
    instructions=(
        "This server exposes exactly 5 weather tools. Each tool calls a different "
        "live public weather API and returns HTML-formatted results."
    ),
)

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    95: "Thunderstorm",
}


def _html_card(
    title: str,
    source: str,
    city: str,
    rows: list[tuple[str, str]],
    *,
    error: bool = False,
) -> str:
    badge = "error" if error else "ok"
    row_html = "".join(
        f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>"
        for label, value in rows
    )
    return f"""<div class="weather-card {badge}">
  <div class="card-header">
    <h3>{escape(title)}</h3>
    <span class="badge">{escape(source)}</span>
  </div>
  <p class="city">Location: {escape(city)}</p>
  <table>{row_html}</table>
</div>"""


def _html_error(tool: str, source: str, city: str, message: str) -> str:
    return _html_card(
        tool,
        source,
        city,
        [("Status", "Error"), ("Details", message)],
        error=True,
    )


async def _geocode(city: str) -> tuple[float, float, str]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("results") or []
    if not results:
        raise ValueError(f"Could not find location: {city}")

    place = results[0]
    name = place.get("name", city)
    country = place.get("country", "")
    label = f"{name}, {country}" if country else name
    return float(place["latitude"]), float(place["longitude"]), label


@mcp.tool
async def weather_open_meteo(city: str) -> str:
    """Live weather from Open-Meteo (free, no API key). Returns current temperature, humidity, wind, and conditions."""
    try:
        lat, lon, label = await _geocode(city)
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                    "timezone": "auto",
                },
            )
            response.raise_for_status()
            current = response.json()["current"]

        code = int(current.get("weather_code", 0))
        rows = [
            ("Temperature", f"{current['temperature_2m']} °C"),
            ("Humidity", f"{current['relative_humidity_2m']}%"),
            ("Wind Speed", f"{current['wind_speed_10m']} km/h"),
            ("Conditions", WEATHER_CODES.get(code, f"Code {code}")),
            ("Coordinates", f"{lat:.2f}, {lon:.2f}"),
        ]
        return _html_card("Open-Meteo Weather", "api.open-meteo.com", label, rows)
    except Exception as exc:
        return _html_error("Open-Meteo Weather", "api.open-meteo.com", city, str(exc))


@mcp.tool
async def weather_wttr(city: str) -> str:
    """Live weather from wttr.in (free, no API key). Returns temperature, feels-like, humidity, and description."""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"https://wttr.in/{city}?format=j1",
                headers={"User-Agent": "WeatherMCP/1.0"},
            )
            response.raise_for_status()
            data = response.json()

        current = data["current_condition"][0]
        area = data.get("nearest_area", [{}])[0]
        area_name = area.get("areaName", [{}])[0].get("value", city)
        country = area.get("country", [{}])[0].get("value", "")
        label = f"{area_name}, {country}" if country else area_name

        rows = [
            ("Temperature", f"{current['temp_C']} °C ({current['temp_F']} °F)"),
            ("Feels Like", f"{current['FeelsLikeC']} °C"),
            ("Humidity", f"{current['humidity']}%"),
            ("Wind", f"{current['windspeedKmph']} km/h {current['winddir16Point']}"),
            ("Description", current["weatherDesc"][0]["value"]),
            ("Observation Time", current.get("observation_time", "N/A")),
        ]
        return _html_card("wttr.in Weather", "wttr.in", label, rows)
    except Exception as exc:
        return _html_error("wttr.in Weather", "wttr.in", city, str(exc))


@mcp.tool
async def weather_7timer(city: str) -> str:
    """Live astronomical weather from 7Timer! (free, no API key). Returns cloud cover and seeing conditions."""
    try:
        lat, lon, label = await _geocode(city)
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://www.7timer.info/bin/api.pl",
                params={
                    "lon": lon,
                    "lat": lat,
                    "product": "astro",
                    "output": "json",
                },
            )
            response.raise_for_status()
            data = response.json()

        init = data.get("init", "N/A")
        series = data.get("dataseries") or []
        if not series:
            raise ValueError("7Timer returned no forecast data")

        point = series[0]
        cloud = point.get("cloudcover", "N/A")
        seeing = point.get("seeing", "N/A")
        transparency = point.get("transparency", "N/A")
        lifted_index = point.get("lifted_index", "N/A")

        rows = [
            ("Forecast Init", str(init)),
            ("Cloud Cover", f"Level {cloud}/9"),
            ("Seeing", f"Level {seeing}/9 (lower is better)"),
            ("Transparency", f"Level {transparency}/9"),
            ("Lifted Index", str(lifted_index)),
            ("Coordinates", f"{lat:.2f}, {lon:.2f}"),
        ]
        return _html_card("7Timer! Astro Weather", "7timer.info", label, rows)
    except Exception as exc:
        return _html_error("7Timer! Astro Weather", "7timer.info", city, str(exc))


@mcp.tool
async def weather_openweather(city: str) -> str:
    """Live weather from OpenWeatherMap (free tier — requires OPENWEATHER_API_KEY in .env)."""
    if not OPENWEATHER_API_KEY:
        return _html_error(
            "OpenWeatherMap",
            "openweathermap.org",
            city,
            "Missing OPENWEATHER_API_KEY. Copy .env.example to .env and add your free key from https://openweathermap.org/api",
        )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            )
            response.raise_for_status()
            data = response.json()

        label = f"{data['name']}, {data['sys'].get('country', '')}"
        rows = [
            ("Temperature", f"{data['main']['temp']} °C (feels {data['main']['feels_like']} °C)"),
            ("Humidity", f"{data['main']['humidity']}%"),
            ("Pressure", f"{data['main']['pressure']} hPa"),
            ("Wind", f"{data['wind']['speed']} m/s"),
            ("Conditions", data["weather"][0]["description"].title()),
            ("Cloudiness", f"{data['clouds']['all']}%"),
        ]
        return _html_card("OpenWeatherMap", "openweathermap.org", label.strip(", "), rows)
    except Exception as exc:
        return _html_error("OpenWeatherMap", "openweathermap.org", city, str(exc))


@mcp.tool
async def weather_weatherapi(city: str) -> str:
    """Live weather from WeatherAPI.com (free tier — requires WEATHERAPI_KEY in .env)."""
    if not WEATHERAPI_KEY:
        return _html_error(
            "WeatherAPI.com",
            "weatherapi.com",
            city,
            "Missing WEATHERAPI_KEY. Copy .env.example to .env and add your free key from https://www.weatherapi.com/signup.aspx",
        )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.weatherapi.com/v1/current.json",
                params={"key": WEATHERAPI_KEY, "q": city},
            )
            response.raise_for_status()
            data = response.json()

        loc = data["location"]
        current = data["current"]
        label = f"{loc['name']}, {loc['country']}"
        rows = [
            ("Temperature", f"{current['temp_c']} °C ({current['temp_f']} °F)"),
            ("Feels Like", f"{current['feelslike_c']} °C"),
            ("Humidity", f"{current['humidity']}%"),
            ("Wind", f"{current['wind_kph']} km/h {current['wind_dir']}"),
            ("Conditions", current["condition"]["text"]),
            ("Local Time", loc["localtime"]),
        ]
        return _html_card("WeatherAPI.com", "weatherapi.com", label, rows)
    except Exception as exc:
        return _html_error("WeatherAPI.com", "weatherapi.com", city, str(exc))


CORS_MIDDLEWARE = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "mcp-protocol-version",
            "mcp-session-id",
            "last-event-id",
        ],
        expose_headers=["mcp-session-id"],
    )
]

if __name__ == "__main__":
    mcp.run(
        transport="sse",
        host="127.0.0.1",
        port=8000,
        middleware=CORS_MIDDLEWARE,
    )
