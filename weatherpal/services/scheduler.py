"""APScheduler jobs — 15-minute alerts, light morning tick."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from weatherpal.config import ALERT_INTERVAL_MINUTES, MORNING_CHECK_INTERVAL_SECONDS
from weatherpal.database import db
from weatherpal.services import weather
from weatherpal.utils import formatters

logger = logging.getLogger(__name__)


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def run_morning_cycle(send_message: Callable[[int, str], None]) -> None:
    """Once per local day per user, at their morning_time (server clock)."""
    now = datetime.now()
    hm = now.strftime("%H:%M")
    today = _today_str()
    users = db.list_all_users()
    for u in users:
        if (u.get("last_morning_date") or "") == today:
            continue
        mt = (u.get("morning_time") or "08:00").strip()
        if mt != hm:
            continue
        tid = int(u["telegram_id"])
        city = (u.get("city") or "").strip()
        if not city:
            continue
        try:
            om, resolved = weather.get_weather_bundle_for_city(city)
            if not resolved:
                send_message(tid, formatters.invalid_city_message())
                db.set_last_morning_date(tid, today)
                continue
            if not om:
                send_message(
                    tid,
                    "☀️ <b>Good morning!</b>\n" + formatters.friendly_api_error(),
                )
                db.set_last_morning_date(tid, today)
                continue
            daily = weather.aggregate_daily(om)
            today_d = weather.pick_today_daily(om, daily)
            snap = weather.current_snapshot(om)
            text = formatters.format_morning_summary(resolved, snap, today_d)
            send_message(tid, text)
            db.set_last_morning_date(tid, today)
        except Exception as e:
            logger.exception("Morning message failed for %s: %s", tid, e)


def build_scheduler(
    alert_runner: Callable[[], None],
    morning_runner: Callable[[], None],
) -> BackgroundScheduler:
    sched = BackgroundScheduler(
        job_defaults={"coalesce": True, "max_instances": 1},
    )
    sched.add_job(
        alert_runner,
        trigger=IntervalTrigger(minutes=ALERT_INTERVAL_MINUTES),
        id="weatherpal_alerts",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sched.add_job(
        morning_runner,
        trigger=IntervalTrigger(seconds=MORNING_CHECK_INTERVAL_SECONDS),
        id="weatherpal_morning",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return sched
