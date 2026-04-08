"""Main menu: today, forecast, help."""

from __future__ import annotations

import logging

from telebot import TeleBot, types

from weatherpal.config import FORECAST_DAYS_LABEL
from weatherpal.database import db
from weatherpal.services import weather
from weatherpal.state import pending
from weatherpal.utils import formatters

logger = logging.getLogger(__name__)

BTN_TODAY = "🌤 Today"
BTN_FORECAST = "📅 Forecast"
BTN_SETTINGS = "⚙️ Settings"
BTN_HELP = "❓ Help"


def main_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(BTN_TODAY, BTN_FORECAST)
    kb.row(BTN_SETTINGS, BTN_HELP)
    return kb


def register(bot: TeleBot) -> None:
    @bot.message_handler(commands=["help"])
    def on_help(message: types.Message) -> None:
        bot.reply_to(
            message,
            "🌤 <b>WeatherPal</b>\n\n"
            "• <b>Today</b> — Open-Meteo (10 min cache per city)\n"
            f"• <b>Forecast</b> — {FORECAST_DAYS_LABEL} daily outlook\n"
            "• <b>Settings</b> — rain & temp alerts, morning summary\n\n"
            "Alerts every 15 min · one weather request per city.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    @bot.message_handler(commands=["today"])
    def cmd_today(message: types.Message) -> None:
        send_today(bot, message)

    @bot.message_handler(commands=["forecast"])
    def cmd_forecast(message: types.Message) -> None:
        send_forecast(bot, message)

    @bot.message_handler(func=lambda m: m.text == BTN_TODAY)
    def btn_today(message: types.Message) -> None:
        send_today(bot, message)

    @bot.message_handler(func=lambda m: m.text == BTN_FORECAST)
    def btn_forecast(message: types.Message) -> None:
        send_forecast(bot, message)

    @bot.message_handler(func=lambda m: m.text == BTN_HELP)
    def btn_help(message: types.Message) -> None:
        on_help(message)

    def send_today(bot_: TeleBot, message: types.Message) -> None:
        uid = message.from_user.id
        if pending.get(uid) in ("city", "morning"):
            return
        row = db.get_user(uid)
        if not row or not (row.get("city") or "").strip():
            bot_.reply_to(
                message,
                "Use /start and send your city first.",
                reply_markup=main_keyboard(),
            )
            return
        city = row["city"].strip()
        try:
            om, resolved = weather.get_weather_bundle_for_city(city)
            if not resolved:
                bot_.reply_to(
                    message,
                    formatters.invalid_city_message(),
                    parse_mode="HTML",
                    reply_markup=main_keyboard(),
                )
                return
            if not om:
                bot_.reply_to(
                    message,
                    formatters.friendly_api_error(),
                    parse_mode="HTML",
                    reply_markup=main_keyboard(),
                )
                return
            snap = weather.current_snapshot(om)
            text = formatters.format_current_weather(resolved, snap)
            bot_.reply_to(
                message,
                text,
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )
        except Exception as e:
            logger.exception("today: %s", e)
            bot_.reply_to(
                message,
                formatters.friendly_api_error(),
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )

    def send_forecast(bot_: TeleBot, message: types.Message) -> None:
        uid = message.from_user.id
        if pending.get(uid) in ("city", "morning"):
            return
        row = db.get_user(uid)
        if not row or not (row.get("city") or "").strip():
            bot_.reply_to(
                message,
                "Use /start and send your city first.",
                reply_markup=main_keyboard(),
            )
            return
        city = row["city"].strip()
        try:
            om, resolved = weather.get_weather_bundle_for_city(city)
            if not resolved:
                bot_.reply_to(
                    message,
                    formatters.invalid_city_message(),
                    parse_mode="HTML",
                    reply_markup=main_keyboard(),
                )
                return
            if not om:
                bot_.reply_to(
                    message,
                    formatters.friendly_api_error(),
                    parse_mode="HTML",
                    reply_markup=main_keyboard(),
                )
                return
            daily = weather.aggregate_daily(om)
            text = formatters.format_forecast(resolved, daily)
            bot_.reply_to(
                message,
                text,
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )
        except Exception as e:
            logger.exception("forecast: %s", e)
            bot_.reply_to(
                message,
                formatters.friendly_api_error(),
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )
