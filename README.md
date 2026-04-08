# WeatherPal

Lightweight Telegram weather bot using **only free services**: **[Open-Meteo](https://open-meteo.com/)** (weather), **[Nominatim](https://nominatim.org/)** (geocoding), and **SQLite**. No paid API keys.

Efficiency: **10-minute shared weather cache per city**, **permanent coordinate cache**, **15-minute alert batches** (one Open-Meteo request per city when the cache expires), **APScheduler** with stable job IDs (`replace_existing=True`).

## Stack

- Python 3.11+
- pyTelegramBotAPI, requests, APScheduler, python-dotenv
- Open-Meteo (`/v1/forecast`) — no key
- Nominatim (`/search`) — no key; **set `NOMINATIM_USER_AGENT`** in production (see `.env.example`)
- SQLite (`users` + `geocode_cache`)

## Local run

1. Copy env:

   ```bash
   cp .env.example .env
   ```

2. Set **`TELEGRAM_TOKEN`** (from [@BotFather](https://t.me/BotFather)) and optionally **`NOMINATIM_USER_AGENT`** (recommended for polite use of OpenStreetMap’s public Nominatim).

3. Install and run:

   ```bash
   cd "/path/to/Weather bot"
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python -m weatherpal
   ```

The DB file defaults to `./data/weatherpal.db` (`DATABASE_PATH` overrides).

## Features

- **`/start`** — geocode city via Nominatim (cached forever in SQLite); then weather uses **lat/lon**.
- **Today / Forecast** — Open-Meteo **current + hourly + daily**; **10 min cache** per city string.
- **Alerts** (every **15 min**): rain in the **next hour** (hourly precip + WMO codes); temp **below 3°C** or **above 25°C**. Per-user cooldown to limit noise.
- **Morning summary** once per day at **HH:MM** (server clock; set **`TZ`** on the host so it matches your region).

## Free vs “trial” (short answer)

- **Open-Meteo** and **Nominatim** are free to use with fair-use limits (no billing).
- **Telegram Bot API** is free for normal bot usage.
- **Azure for Students** / credits are a **student benefit**, not guaranteed “forever”; this **code** avoids paid weather APIs so you are not tied to vendor billing.

Use **one process** (one worker) so polling and the scheduler stay single-instance.

## Microsoft Azure (App Service / container)

- **Start command:** `python -m weatherpal` (or call `weatherpal.bot:start_bot` from a thin wrapper).
- **Workers:** **one** instance — multiple instances would duplicate schedulers and poll the same bot token.
- **Polling** — no inbound HTTP port required.
- **Persistence:** put **`DATABASE_PATH`** on a **mounted volume** (e.g. Azure Files) if you need the same SQLite file across restarts.
- **Environment:** set `TELEGRAM_TOKEN`, `TZ`, and `NOMINATIM_USER_AGENT`.

## Railway / Render

Same as above: one worker, env vars, `python -m weatherpal`. See `Procfile`.

## Notes

- Respect Nominatim’s **1 request/second** guideline; this bot geocodes a city once per new place (then caches).
- If Open-Meteo or Nominatim fails, users get a short friendly message; the bot keeps running.
