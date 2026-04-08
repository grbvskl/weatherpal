"""
WMO weather interpretation codes (Open-Meteo).
https://open-meteo.com/en/docs (Weather variable documentation)
"""

from __future__ import annotations


def describe(code: int | None) -> tuple[str, str]:
    """
    Return (emoji, short description) for a WMO weathercode.
    Unknown codes fall back to a neutral cloud.
    """
    c = int(code) if code is not None else -1

    if c == 0:
        return "☀️", "Clear"
    if c in (1, 2, 3):
        return "⛅", "Cloudy"
    if c in (45, 48):
        return "🌫", "Fog"
    if 51 <= c <= 55:
        return "🌦", "Drizzle"
    if c in (56, 57):
        return "🌧", "Freezing drizzle"
    if 61 <= c <= 65:
        return "🌧", "Rain"
    if c in (66, 67):
        return "🌨", "Freezing rain"
    if 71 <= c <= 77:
        return "❄️", "Snow"
    if 80 <= c <= 82:
        return "🌧", "Rain showers"
    if c in (85, 86):
        return "🌨", "Snow showers"
    if c == 95:
        return "⛈️", "Thunderstorm"
    if c in (96, 99):
        return "⛈️", "Thunderstorm with hail"
    return "☁️", "Unknown"
