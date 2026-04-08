"""Thread-safe in-memory cache with TTL for Open-Meteo JSON (per city key)."""

from __future__ import annotations

import threading
import time
from typing import Any

from weatherpal.config import CACHE_TTL_SECONDS


class WeatherCache:
    """Simple dict: city_key -> {data, timestamp}."""

    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            if now - entry["timestamp"] > self._ttl:
                del self._store[key]
                return None
            return entry["data"]

    def set(self, key: str, data: dict[str, Any]) -> None:
        with self._lock:
            self._store[key] = {"data": data, "timestamp": time.time()}

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)


weather_cache = WeatherCache()
