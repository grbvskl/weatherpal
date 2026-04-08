"""SQLite persistence — no external DB required."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

from weatherpal.config import DB_PATH


_lock = threading.Lock()


def _ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    _ensure_parent(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    city TEXT NOT NULL,
                    rain_alert INTEGER NOT NULL DEFAULT 1,
                    temp_alert INTEGER NOT NULL DEFAULT 1,
                    morning_time TEXT NOT NULL DEFAULT '08:00',
                    last_rain_alert_at INTEGER NOT NULL DEFAULT 0,
                    last_temp_alert_at INTEGER NOT NULL DEFAULT 0,
                    last_morning_date TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS geocode_cache (
                    city_norm TEXT PRIMARY KEY,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    display_name TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()


def upsert_user(
    telegram_id: int,
    city: str,
    rain_alert: int | None = None,
    temp_alert: int | None = None,
    morning_time: str | None = None,
) -> None:
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO users (telegram_id, city, rain_alert, temp_alert, morning_time)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        telegram_id,
                        city,
                        1 if rain_alert is None else rain_alert,
                        1 if temp_alert is None else temp_alert,
                        morning_time or "08:00",
                    ),
                )
            else:
                sets = ["city = ?"]
                params: list[Any] = [city]
                if rain_alert is not None:
                    sets.append("rain_alert = ?")
                    params.append(rain_alert)
                if temp_alert is not None:
                    sets.append("temp_alert = ?")
                    params.append(temp_alert)
                if morning_time is not None:
                    sets.append("morning_time = ?")
                    params.append(morning_time)
                params.append(telegram_id)
                conn.execute(
                    f"UPDATE users SET {', '.join(sets)} WHERE telegram_id = ?",
                    params,
                )
            conn.commit()
        finally:
            conn.close()


def get_user(telegram_id: int) -> dict[str, Any] | None:
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def list_all_users() -> list[dict[str, Any]]:
    with _lock:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM users").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def update_alert_times(
    telegram_id: int,
    last_rain_alert_at: int | None = None,
    last_temp_alert_at: int | None = None,
) -> None:
    with _lock:
        conn = get_connection()
        try:
            if last_rain_alert_at is not None:
                conn.execute(
                    "UPDATE users SET last_rain_alert_at = ? WHERE telegram_id = ?",
                    (last_rain_alert_at, telegram_id),
                )
            if last_temp_alert_at is not None:
                conn.execute(
                    "UPDATE users SET last_temp_alert_at = ? WHERE telegram_id = ?",
                    (last_temp_alert_at, telegram_id),
                )
            conn.commit()
        finally:
            conn.close()


def set_last_morning_date(telegram_id: int, date_str: str) -> None:
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE users SET last_morning_date = ? WHERE telegram_id = ?",
                (date_str, telegram_id),
            )
            conn.commit()
        finally:
            conn.close()


def set_user_settings(
    telegram_id: int,
    *,
    rain_alert: int | None = None,
    temp_alert: int | None = None,
    morning_time: str | None = None,
) -> None:
    with _lock:
        conn = get_connection()
        try:
            sets: list[str] = []
            params: list[Any] = []
            if rain_alert is not None:
                sets.append("rain_alert = ?")
                params.append(rain_alert)
            if temp_alert is not None:
                sets.append("temp_alert = ?")
                params.append(temp_alert)
            if morning_time is not None:
                sets.append("morning_time = ?")
                params.append(morning_time)
            if not sets:
                return
            params.append(telegram_id)
            conn.execute(
                f"UPDATE users SET {', '.join(sets)} WHERE telegram_id = ?",
                params,
            )
            conn.commit()
        finally:
            conn.close()


def get_geocode(city_norm: str) -> tuple[float, float, str] | None:
    with _lock:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT lat, lon, display_name FROM geocode_cache WHERE city_norm = ?",
                (city_norm,),
            ).fetchone()
            if not row:
                return None
            return float(row["lat"]), float(row["lon"]), str(row["display_name"])
        finally:
            conn.close()


def save_geocode(city_norm: str, lat: float, lon: float, display_name: str) -> None:
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO geocode_cache (city_norm, lat, lon, display_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(city_norm) DO UPDATE SET
                    lat = excluded.lat,
                    lon = excluded.lon,
                    display_name = excluded.display_name
                """,
                (city_norm, lat, lon, display_name),
            )
            conn.commit()
        finally:
            conn.close()
