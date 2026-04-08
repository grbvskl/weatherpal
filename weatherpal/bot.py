"""WeatherPal — entrypoint, polling, scheduler (single process, Azure-friendly)."""

from __future__ import annotations

import logging
import sys
import time

import telebot

from weatherpal.config import TELEGRAM_TOKEN
from weatherpal.database.db import init_db
from weatherpal.handlers import menu, settings, start
from weatherpal.services import alerts
from weatherpal.services.scheduler import build_scheduler, run_morning_cycle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("weatherpal")


def start_bot() -> None:
    """
    Initialize DB, scheduler (idempotent job IDs), and Telegram long polling.
    Safe to call once per process; use a single worker on Azure.
    """
    if not TELEGRAM_TOKEN:
        logger.error("Set TELEGRAM_TOKEN in the environment.")
        sys.exit(1)

    init_db()
    bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")

    def send_html(uid: int, text: str) -> None:
        try:
            bot.send_message(uid, text, parse_mode="HTML")
        except Exception as e:
            logger.warning("send_message %s: %s", uid, e)

    def run_alerts() -> None:
        try:
            alerts.run_alert_cycle(send_html)
        except Exception as e:
            logger.exception("Alert job failed: %s", e)

    def run_morning() -> None:
        try:
            run_morning_cycle(send_html)
        except Exception as e:
            logger.exception("Morning job failed: %s", e)

    start.register(bot)
    menu.register(bot)
    settings.register(bot)

    sched = build_scheduler(run_alerts, run_morning)
    sched.start()
    logger.info("Scheduler started (alerts every 15 min, morning tick each minute).")

    logger.info("Bot polling…")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, interval=0, timeout=60)
        except Exception as e:
            logger.exception("Polling error: %s — retrying in 10s", e)
            time.sleep(10)


def main() -> None:
    start_bot()


if __name__ == "__main__":
    main()
