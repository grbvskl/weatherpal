"""Onboarding: city selection."""

from __future__ import annotations

import logging

from telebot import TeleBot, types

from weatherpal.database import db
from weatherpal.handlers.menu import main_keyboard
from weatherpal.services import geocoding
from weatherpal.state import pending
from weatherpal.utils import formatters

logger = logging.getLogger(__name__)


def register(bot: TeleBot) -> None:
    @bot.message_handler(commands=["start"])
    def on_start(message: types.Message) -> None:
        uid = message.from_user.id
        row = db.get_user(uid)
        if row and (row.get("city") or "").strip():
            pending.pop(uid, None)
            bot.reply_to(
                message,
                "👋 Welcome back to <b>WeatherPal</b>!\n"
                "Your city is saved — use the menu below.",
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )
            return
        pending[uid] = "city"
        bot.reply_to(
            message,
            "👋 Hi! I’m <b>WeatherPal</b> — your calm weather companion.\n\n"
            "📍 Please send your <b>city name</b> (e.g. <code>London</code> or "
            "<code>New York</code>).",
            parse_mode="HTML",
        )

    @bot.message_handler(
        func=lambda m: m.from_user and pending.get(m.from_user.id) == "city",
        content_types=["text"],
    )
    def on_city(message: types.Message) -> None:
        uid = message.from_user.id
        city = (message.text or "").strip()
        if not city or city.startswith("/"):
            bot.reply_to(message, "Please send a city name without a slash command.")
            return
        try:
            coords = geocoding.get_coordinates(city)
            if not coords:
                bot.reply_to(
                    message,
                    formatters.invalid_city_message(),
                    parse_mode="HTML",
                )
                return
            _, _, resolved = coords
            db.upsert_user(uid, city)
            pending.pop(uid, None)
            bot.reply_to(
                message,
                f"✅ Saved: <b>{formatters.esc(resolved)}</b>\n\n"
                "Use the buttons below for weather, forecast, and settings.",
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )
        except Exception as e:
            logger.exception("save city: %s", e)
            bot.reply_to(message, "Something went wrong saving your city. Try again.")
