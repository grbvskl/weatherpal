"""Alerts and morning time."""

from __future__ import annotations

import logging
import re

from telebot import TeleBot, types

from weatherpal.database import db
from weatherpal.state import pending
from weatherpal.utils.formatters import esc

logger = logging.getLogger(__name__)

BTN_SETTINGS = "⚙️ Settings"
TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def register(bot: TeleBot) -> None:
    @bot.message_handler(commands=["settings"])
    def cmd_settings(message: types.Message) -> None:
        show_settings(bot, message)

    @bot.message_handler(func=lambda m: m.text == BTN_SETTINGS)
    def btn_settings(message: types.Message) -> None:
        show_settings(bot, message)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("wp:"))
    def on_cb(call: types.CallbackQuery) -> None:
        uid = call.from_user.id
        data = call.data or ""
        parts = data.split(":")
        if len(parts) < 2:
            bot.answer_callback_query(call.id)
            return
        action = parts[1]
        row = db.get_user(uid)
        if not row:
            bot.answer_callback_query(call.id, "Use /start first.", show_alert=True)
            return
        try:
            if action == "rain":
                v = 0 if row.get("rain_alert") else 1
                db.set_user_settings(uid, rain_alert=v)
                bot.answer_callback_query(call.id, "Updated")
                _edit_settings_msg(bot, call, uid)
            elif action == "temp":
                v = 0 if row.get("temp_alert") else 1
                db.set_user_settings(uid, temp_alert=v)
                bot.answer_callback_query(call.id, "Updated")
                _edit_settings_msg(bot, call, uid)
            elif action == "morning":
                bot.answer_callback_query(call.id)
                pending[uid] = "morning"
                bot.send_message(
                    uid,
                    "⏰ Send morning time as <b>HH:MM</b> in <b>24h</b> format "
                    "(server clock — set <code>TZ</code> on your host for local time).\n"
                    "Example: <code>07:30</code>",
                    parse_mode="HTML",
                )
            elif action == "city":
                bot.answer_callback_query(call.id)
                pending[uid] = "city"
                bot.send_message(
                    uid,
                    "📍 Send your new city name.",
                )
            else:
                bot.answer_callback_query(call.id)
        except Exception as e:
            logger.exception("settings cb: %s", e)
            bot.answer_callback_query(call.id, "Error", show_alert=True)

    @bot.message_handler(
        func=lambda m: m.from_user and pending.get(m.from_user.id) == "morning",
        content_types=["text"],
    )
    def on_morning_time(message: types.Message) -> None:
        uid = message.from_user.id
        raw = (message.text or "").strip()
        if not TIME_RE.match(raw):
            bot.reply_to(
                message,
                "Please use HH:MM, e.g. <code>08:15</code>.",
                parse_mode="HTML",
            )
            return
        h, m_ = raw.split(":")
        if int(h) > 23 or int(m_) > 59:
            bot.reply_to(message, "Invalid time.")
            return
        try:
            db.set_user_settings(uid, morning_time=raw)
            pending.pop(uid, None)
            bot.reply_to(message, f"✅ Morning summary set to <b>{raw}</b>.", parse_mode="HTML")
        except Exception as e:
            logger.exception("morning time: %s", e)
            bot.reply_to(message, "Could not save. Try again.")


def show_settings(bot: TeleBot, message: types.Message) -> None:
    uid = message.from_user.id
    row = db.get_user(uid)
    if not row:
        bot.reply_to(message, "Use /start first.")
        return
    kb = _settings_kb(row)
    city = esc(str(row.get("city") or "—"))
    mt = row.get("morning_time") or "08:00"
    ra = "ON" if row.get("rain_alert") else "OFF"
    ta = "ON" if row.get("temp_alert") else "OFF"
    bot.reply_to(
        message,
        "⚙️ <b>Settings</b>\n\n"
        f"📍 City: <b>{city}</b>\n"
        f"🌧 Rain alerts: <b>{ra}</b>\n"
        f"🌡 Temp alerts: <b>{ta}</b>\n"
        f"☀️ Morning: <b>{mt}</b> (server time)\n",
        parse_mode="HTML",
        reply_markup=kb,
    )


def _settings_kb(row: dict) -> types.InlineKeyboardMarkup:
    ra = row.get("rain_alert")
    ta = row.get("temp_alert")
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(
            text=f"🌧 Rain: {'ON' if ra else 'OFF'}",
            callback_data="wp:rain",
        ),
        types.InlineKeyboardButton(
            text=f"🌡 Temp: {'ON' if ta else 'OFF'}",
            callback_data="wp:temp",
        ),
    )
    kb.row(
        types.InlineKeyboardButton(
            text="⏰ Set morning time",
            callback_data="wp:morning",
        ),
    )
    kb.row(
        types.InlineKeyboardButton(
            text="📍 Change city",
            callback_data="wp:city",
        ),
    )
    return kb


def _edit_settings_msg(bot: TeleBot, call: types.CallbackQuery, uid: int) -> None:
    row = db.get_user(uid)
    if not row or not call.message:
        return
    kb = _settings_kb(row)
    city = esc(str(row.get("city") or "—"))
    mt = row.get("morning_time") or "08:00"
    ra = "ON" if row.get("rain_alert") else "OFF"
    ta = "ON" if row.get("temp_alert") else "OFF"
    text = (
        "⚙️ <b>Settings</b>\n\n"
        f"📍 City: <b>{city}</b>\n"
        f"🌧 Rain alerts: <b>{ra}</b>\n"
        f"🌡 Temp alerts: <b>{ta}</b>\n"
        f"☀️ Morning: <b>{mt}</b> (server time)\n"
    )
    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception as e:
        logger.debug("edit settings: %s", e)
