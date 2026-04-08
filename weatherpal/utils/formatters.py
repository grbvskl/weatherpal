"""Telegram message formatting — plain strings, no heavy deps."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def esc(text: str) -> str:
    """Minimal escaping for Telegram HTML mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_current_weather(city_name: str, snap: dict[str, Any]) -> str:
    desc = esc(str(snap.get("description", "—")))
    em = snap.get("emoji") or "🌤"
    temp = snap.get("temp")
    wind = snap.get("windspeed")

    parts = [
        f"📍 <b>{esc(city_name)}</b>",
        "",
        f"{em} <b>Now:</b> {desc}",
    ]
    if temp is not None:
        parts.append(f"🌡 <b>Temp:</b> {float(temp):.1f}°C")
    if wind is not None:
        parts.append(f"💨 <b>Wind:</b> {float(wind):.1f} km/h")
    parts.append("")
    parts.append("<i>Open-Meteo · 10 min cache per city</i>")
    return "\n".join(parts)


def _day_label(ts: int) -> str:
    return datetime.utcfromtimestamp(ts).strftime("%a %d %b")


def format_forecast(city_name: str, daily: list[dict[str, Any]]) -> str:
    if not daily:
        return f"📍 <b>{esc(city_name)}</b>\n\nNo forecast data."
    lines = [f"📍 <b>{esc(city_name)}</b>", "", "📅 <b>Daily outlook</b>", ""]
    for d in daily:
        day = _day_label(d["dt"])
        tmin = d.get("temp_min")
        tmax = d.get("temp_max")
        em = d.get("emoji") or "☁️"
        dsc = esc(str(d.get("description", "—")))
        if tmin is not None and tmax is not None:
            lines.append(
                f"• {em} <b>{day}</b>: {float(tmin):.0f}–{float(tmax):.0f}°C — {dsc}"
            )
        else:
            lines.append(f"• {em} <b>{day}</b>: {dsc}")
    lines.append("")
    lines.append("<i>Open-Meteo (free) · daily model</i>")
    return "\n".join(lines)


def format_morning_summary(
    city_name: str,
    snap: dict[str, Any],
    daily_today: dict[str, Any] | None,
) -> str:
    desc = esc(str(snap.get("description", "—")))
    em = snap.get("emoji") or "☀️"
    temp = snap.get("temp")
    header = f"☀️ <b>Good morning!</b> {esc(city_name)}"
    body = f"\n\n{em} Today: <b>{desc}</b>"
    if temp is not None:
        body += f"\n🌡 Around <b>{float(temp):.0f}°C</b> now."
    if daily_today:
        tmin = daily_today.get("temp_min")
        tmax = daily_today.get("temp_max")
        if tmin is not None and tmax is not None:
            body += (
                f"\n📊 High / low: <b>{float(tmax):.0f}°C</b> / "
                f"<b>{float(tmin):.0f}°C</b>."
            )
    body += "\n\nHave a great day! 🌈"
    return header + body


def friendly_api_error() -> str:
    return (
        "😕 Couldn’t reach the weather service right now.\n"
        "Please try again in a few minutes."
    )


def invalid_city_message() -> str:
    return (
        "🔍 I couldn’t find that place.\n"
        "Try a larger nearby city or a different spelling."
    )
