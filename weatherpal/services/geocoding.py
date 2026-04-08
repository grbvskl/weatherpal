"""Nominatim geocoding — city to coordinates. Coordinates cached permanently."""

from __future__ import annotations

import logging
import threading
from typing import Any
from urllib.parse import quote_plus

import requests

from weatherpal.config import NOMINATIM_BASE, NOMINATIM_USER_AGENT
from weatherpal.database import db

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": NOMINATIM_USER_AGENT,
        "Accept-Language": "en",
    }
)

_mem: dict[str, tuple[float, float, str]] = {}
_lock = threading.Lock()


def _norm_key(city: str) -> str:
    return city.strip().lower()


def get_coordinates(city_name: str) -> tuple[float, float, str] | None:
    """
    Resolve city name to (lat, lon, display_name).
    Cached forever (SQLite + in-memory). Returns None if not found or on HTTP error.
    """
    raw = city_name.strip()
    if not raw:
        return None
    key = _norm_key(raw)

    with _lock:
        hit = _mem.get(key)
    if hit:
        return hit

    row = db.get_geocode(key)
    if row:
        lat, lon, disp = row
        with _lock:
            _mem[key] = (lat, lon, disp)
        return lat, lon, disp

    url = (
        f"{NOMINATIM_BASE}/search?q={quote_plus(raw)}&format=json&limit=1"
    )
    try:
        r = _SESSION.get(url, timeout=15)
        r.raise_for_status()
        data: list[Any] = r.json()
    except (requests.RequestException, ValueError) as e:
        logger.warning("Nominatim error for %r: %s", raw, e)
        return None

    if not data:
        return None

    item = data[0]
    try:
        lat = float(item["lat"])
        lon = float(item["lon"])
    except (KeyError, TypeError, ValueError):
        return None

    disp = str(item.get("display_name") or raw).strip() or raw

    db.save_geocode(key, lat, lon, disp)
    with _lock:
        _mem[key] = (lat, lon, disp)
    return lat, lon, disp
