"""
POLYMARKET WEATHER ANALYZER — Utilities
Timezones, temperature conversion, local time.
"""

import subprocess
import sys
from datetime import datetime, timezone, timedelta

from config import CITIES

# ── Ensure tzdata on Windows ─────────────────────────────────
def _ensure_tzdata() -> bool:
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("Europe/London")
        return True
    except Exception:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "tzdata", "-q"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False


_HAS_ZONEINFO = _ensure_tzdata()

_UTC_OFFSETS = {"london": 1, "miami": -4}


def _city_now(city_key: str) -> datetime:
    """Returns datetime in the city's local time."""
    if _HAS_ZONEINFO:
        from zoneinfo import ZoneInfo
        tz_name = {"london": "Europe/London", "miami": "America/New_York"}[city_key]
        return datetime.now(ZoneInfo(tz_name))
    offset = _UTC_OFFSETS[city_key]
    return datetime.now(timezone(timedelta(hours=offset)))


def c2f(c: float) -> float:
    """°C → °F"""
    return c * 9 / 5 + 32


def f2c(f: float) -> float:
    """°F → °C"""
    return (f - 32) * 5 / 9


def get_local_time(city_key: str) -> dict:
    """Gets time from system clock, converts to city's timezone."""
    c = CITIES[city_key]
    dt = _city_now(city_key)
    hour, minute = dt.hour, dt.minute
    ps, pe = c["peak_start"], c["peak_end"]
    if hour < 6:
        day_phase = "night"
    elif hour < 12:
        day_phase = "morning"
    elif hour < 18:
        day_phase = "day"
    else:
        day_phase = "evening"
    return {
        "local_hour": hour, "local_minute": minute,
        "local_str": f"{hour:02d}:{minute:02d}",
        "day_phase": day_phase,
        "before_peak": hour < ps,
        "during_peak": ps <= hour < pe,
        "after_peak": hour >= pe,
    }
