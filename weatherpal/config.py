"""Configuration loaded from environment. Tuned for free-tier limits."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

# Open-Meteo (no API key)
OPEN_METEO_BASE = "https://api.open-meteo.com/v1"

# Nominatim — identify your app (usage policy: https://operations.osmfoundation.org/policies/nominatim/)
NOMINATIM_BASE = os.getenv("NOMINATIM_BASE", "https://nominatim.openstreetmap.org").rstrip("/")
NOMINATIM_USER_AGENT = os.getenv(
    "NOMINATIM_USER_AGENT",
    "WeatherPal/1.0 (Telegram bot; no commercial use)",
).strip()

# Cache: reuse same city weather for all users (10 minutes)
CACHE_TTL_SECONDS = 600

# Scheduler: alert sweep every 15 minutes (not per-user API spam)
ALERT_INTERVAL_MINUTES = 15

# Morning job checks every minute which users need a greeting (cheap DB-only)
MORNING_CHECK_INTERVAL_SECONDS = 60

# Anti-spam: minimum gap between same-type alerts (seconds)
ALERT_COOLDOWN_SECONDS = 6 * 3600

# Temp thresholds (°C) for alerts
TEMP_ALERT_LOW = 3.0
TEMP_ALERT_HIGH = 25.0

# Rain: notify when model shows meaningful rain in ~1 hour window
RAIN_LOOKAHEAD_HOURS = 1.0
# Hourly precipitation (mm) above this counts as “wet”
RAIN_PRECIP_MM_THRESHOLD = 0.15

# SQLite path (local file; Azure/Railway/Render with optional volume)
DB_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "weatherpal.db"))

# Open-Meteo daily array length (typically 7)
FORECAST_DAYS_LABEL = "7-day"
