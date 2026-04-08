"""Open-Meteo forecast API with 10-minute per-city cache; one bundle per city."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests

from weatherpal.cache import weather_cache
from weatherpal.config import (
    OPEN_METEO_BASE,
    RAIN_LOOKAHEAD_HOURS,
    RAIN_PRECIP_MM_THRESHOLD,
)
from weatherpal.services import geocoding
from weatherpal.utils.weather_codes import describe

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "WeatherPal/1.0"})


def _city_key(city: str) -> str:
    return city.strip().lower()


def get_weather(lat: float, lon: float) -> dict[str, Any] | None:
    """
    Single Open-Meteo request: current + hourly + daily for coordinates.
    """
    url = f"{OPEN_METEO_BASE}/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,weathercode",
        "daily": "temperature_2m_max,temperature_2m_min,weathercode",
        "current_weather": "true",
        "timezone": "auto",
    }
    try:
        r = SESSION.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            return None
        return data
    except (requests.RequestException, ValueError) as e:
        logger.warning("Open-Meteo error: %s", e)
        return None


def get_weather_bundle_for_city(city: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    Geocode (permanently cached) + Open-Meteo bundle (10-minute cache per city).
    Returns (open_meteo_json, display_name) or (None, None) if city not found.
    """
    coords = geocoding.get_coordinates(city)
    if not coords:
        return None, None
    lat, lon, display_name = coords

    key = "om:" + _city_key(city)
    cached = weather_cache.get(key)
    if cached is not None:
        return cached, display_name

    om = get_weather(lat, lon)
    if not om:
        return None, display_name

    weather_cache.set(key, om)
    return om, display_name


def _timezone(om: dict[str, Any]) -> ZoneInfo:
    name = (om.get("timezone") or "UTC").strip()
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def current_snapshot(om: dict[str, Any]) -> dict[str, Any]:
    """Normalized “current” block for formatters."""
    cw = om.get("current_weather") or {}
    wc = cw.get("weathercode")
    emoji, desc = describe(wc)
    return {
        "temp": cw.get("temperature"),
        "windspeed": cw.get("windspeed"),
        "weathercode": wc,
        "description": desc,
        "emoji": emoji,
    }


def current_temp_c(om: dict[str, Any]) -> float | None:
    cw = om.get("current_weather") or {}
    t = cw.get("temperature")
    return float(t) if t is not None else None


def aggregate_daily(om: dict[str, Any]) -> list[dict[str, Any]]:
    """Build daily rows from Open-Meteo daily arrays."""
    daily = om.get("daily") or {}
    times: list[str] = list(daily.get("time") or [])
    tmax = list(daily.get("temperature_2m_max") or [])
    tmin = list(daily.get("temperature_2m_min") or [])
    wcodes = list(daily.get("weathercode") or [])
    tz = _timezone(om)
    out: list[dict[str, Any]] = []
    for i, date_s in enumerate(times):
        try:
            d0 = datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=tz)
        except ValueError:
            continue
        dt = int(d0.timestamp())
        mx = tmax[i] if i < len(tmax) else None
        mn = tmin[i] if i < len(tmin) else None
        wc = wcodes[i] if i < len(wcodes) else None
        em, dsc = describe(wc)
        out.append(
            {
                "dt": dt,
                "date": date_s,
                "temp_max": float(mx) if mx is not None else None,
                "temp_min": float(mn) if mn is not None else None,
                "weathercode": wc,
                "description": dsc,
                "emoji": em,
            }
        )
    return out


def pick_today_daily(om: dict[str, Any], daily: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not daily:
        return None
    tz = _timezone(om)
    today = datetime.now(tz).strftime("%Y-%m-%d")
    for d in daily:
        if d.get("date") == today:
            return d
    return daily[0]


def _parse_hourly_time(s: str) -> datetime | None:
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def rain_expected_next_hour(om: dict[str, Any]) -> bool:
    """True if hourly model shows meaningful rain within the next ~1 hour."""
    h = om.get("hourly") or {}
    times: list[str] = list(h.get("time") or [])
    precip = list(h.get("precipitation") or [])
    codes = list(h.get("weathercode") or [])
    tz = _timezone(om)
    now = datetime.now(tz)
    end = now + timedelta(hours=RAIN_LOOKAHEAD_HOURS)

    rain_codes = {
        *range(51, 68),
        *range(80, 83),
        95,
        96,
        99,
    }

    for i, ts in enumerate(times):
        t = _parse_hourly_time(ts)
        if t is None:
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=tz)
        if t <= now:
            continue
        if t > end:
            break
        p = precip[i] if i < len(precip) else 0.0
        c = codes[i] if i < len(codes) else None
        try:
            pf = float(p)
        except (TypeError, ValueError):
            pf = 0.0
        ci = int(c) if c is not None else -1
        if pf >= RAIN_PRECIP_MM_THRESHOLD or ci in rain_codes:
            return True
    return False
