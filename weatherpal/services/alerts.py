"""Alert evaluation: one API pass per city, many users grouped."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from weatherpal.config import ALERT_COOLDOWN_SECONDS, TEMP_ALERT_HIGH, TEMP_ALERT_LOW
from weatherpal.database import db
from weatherpal.services import weather
from weatherpal.utils.formatters import esc

logger = logging.getLogger(__name__)


def run_alert_cycle(
    send_message: Callable[[int, str], None],
) -> None:
    """
    Group users by city; for each city one Open-Meteo bundle (10-minute cache).
    """
    users = db.list_all_users()
    by_city: dict[str, list[dict[str, Any]]] = {}
    for u in users:
        c = (u.get("city") or "").strip()
        if not c:
            continue
        by_city.setdefault(c, []).append(u)

    now = time.time()

    for city, group in by_city.items():
        om, resolved = weather.get_weather_bundle_for_city(city)
        if not om or not resolved:
            logger.debug("Skip alerts for %s (no data)", city)
            continue

        rain_soon = weather.rain_expected_next_hour(om)
        temp = weather.current_temp_c(om)
        temp_extreme = (
            temp is not None
            and (temp < TEMP_ALERT_LOW or temp > TEMP_ALERT_HIGH)
        )

        place = esc(str(resolved))
        for u in group:
            tid = int(u["telegram_id"])
            try:
                if u.get("rain_alert") and rain_soon:
                    last = int(u.get("last_rain_alert_at") or 0)
                    if now - last >= ALERT_COOLDOWN_SECONDS:
                        send_message(
                            tid,
                            "🌧 <b>Rain heads-up</b>\n"
                            f"📍 {place}\n"
                            "Rain is likely in the next hour. Take an umbrella! ☂️",
                        )
                        db.update_alert_times(tid, last_rain_alert_at=int(now))

                if u.get("temp_alert") and temp_extreme and temp is not None:
                    last = int(u.get("last_temp_alert_at") or 0)
                    if now - last >= ALERT_COOLDOWN_SECONDS:
                        if temp < TEMP_ALERT_LOW:
                            msg = (
                                "🥶 <b>Cold alert</b>\n"
                                f"📍 {place}\n"
                                f"It’s about <b>{temp:.1f}°C</b> — dress warmly!"
                            )
                        else:
                            msg = (
                                "🌡 <b>Heat alert</b>\n"
                                f"📍 {place}\n"
                                f"It’s about <b>{temp:.1f}°C</b> — stay hydrated!"
                            )
                        send_message(tid, msg)
                        db.update_alert_times(tid, last_temp_alert_at=int(now))
            except Exception as e:
                logger.exception("Alert send failed for %s: %s", tid, e)
