"""
POLYMARKET WEATHER ANALYZER — Multi-model Forecast
Collecting max temperatures from multiple sources, aggregation.
"""

import requests
from datetime import datetime

from common.config import CITIES
from common.utils import c2f, f2c

# User-Agent for all requests
UA = {"User-Agent": "PolymarketWeather/1.0"}
TIMEOUT = 10


def _date_offset(date_str: str | None) -> int:
    """Returns day offset from today (0 = today, 1 = tomorrow, ...)."""
    if not date_str:
        return 0
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        today  = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return max(0, (target - today).days)
    except Exception:
        return 0


def _fetch_openmeteo_max(city_key: str,
                          date_str: str | None = None) -> tuple[float | None, dict | None]:
    """Open-Meteo: daily max + full daily data for analysis."""
    c = CITIES[city_key]
    offset = _date_offset(date_str)
    forecast_days = max(offset + 2, 4)
    date_param = f"&start_date={date_str}&end_date={date_str}" if date_str else ""
    try:
        models_param = "&models=best_match,ecmwf_ifs04,gfs_seamless,jma_seamless,icon_seamless,gem_seamless"
        days_param = f"&forecast_days={min(forecast_days, 16)}" if not date_str else ""
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={c['lat']}&longitude={c['lon']}"
            "&daily=temperature_2m_max,temperature_2m_min"
            ",precipitation_probability_max,windspeed_10m_max,weathercode"
            "&hourly=relativehumidity_2m,temperature_2m"
            f"{models_param}"
            f"&timezone=auto{days_param}"
            + date_param
        )
        r = requests.get(url, headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        
        daily = data.get("daily", {})
        hourly = data.get("hourly", {})
        
        for base_key in ["temperature_2m_max", "temperature_2m_min", 
                         "precipitation_probability_max", "windspeed_10m_max", "weathercode"]:
            if base_key not in daily:
                for k in daily.keys():
                    if k.startswith(base_key):
                        daily[base_key] = daily[k]
                        break
        
        for h_key in ["relativehumidity_2m", "temperature_2m"]:
            if h_key not in hourly:
                for k in hourly.keys():
                    if k.startswith(h_key):
                        hourly[h_key] = hourly[k]
                        break

        idx = 0 if date_str else offset
        maxes = daily.get("temperature_2m_max", [])
        max_c = float(maxes[idx]) if len(maxes) > idx else None
        
        return max_c, data
    except Exception as e:
        print(f"Open-Meteo Error: {e}")
        return None, None


def _fetch_wttr_forecast_max(city_key: str,
                               date_str: str | None = None) -> float | None:
    """wttr.in: max from forecast."""
    c = CITIES[city_key]
    offset = _date_offset(date_str)
    query = f"{c['lat']},{c['lon']}"
    try:
        r = requests.get(
            f"https://wttr.in/{query}?format=j1",
            headers={"User-Agent": "curl/7.68.0"},
            timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        weather = data.get("weather", [])
        if offset < len(weather):
            hc = float(weather[offset].get("maxtempC", 0))
        elif weather:
            hc = float(weather[-1].get("maxtempC", 0))
        else:
            return None
        return hc if -20 <= hc <= 50 else None
    except Exception:
        return None


def _fetch_weather_gov_max(city_key: str,
                            date_str: str | None = None) -> float | None:
    """api.weather.gov: only for US (Miami)."""
    if city_key != "miami":
        return None
    c = CITIES[city_key]
    offset = _date_offset(date_str)
    try:
        r = requests.get(
            f"https://api.weather.gov/points/{c['lat']:.4f},{c['lon']:.4f}",
            headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        forecast_url = r.json().get("properties", {}).get("forecast")
        if not forecast_url:
            return None
        r2 = requests.get(forecast_url, headers=UA, timeout=TIMEOUT)
        r2.raise_for_status()
        periods = r2.json().get("properties", {}).get("periods", [])
        day_periods = [p for p in periods if p.get("isDaytime")]
        if offset < len(day_periods):
            temp = day_periods[offset].get("temperature")
            return f2c(temp) if temp is not None else None
        return None
    except Exception:
        return None


def fetch_all_models_max(city_key: str,
                          date_str: str | None = None) -> tuple[list[tuple[str, float]], dict | None]:
    """Fetches max temperature from all models for the specified date."""
    models = []
    om_max, om_data = _fetch_openmeteo_max(city_key, date_str)
    if om_max is not None:
        models.append(("Open-Meteo", om_max))
        if om_data and "daily" in om_data:
            daily = om_data["daily"]
            for m_key, m_name in [("ecmwf_ifs04", "ECMWF"), ("gfs_seamless", "GFS"), 
                                  ("jma_seamless", "JMA"), ("icon_seamless", "ICON"), 
                                  ("gem_seamless", "GEM")]:
                key = f"temperature_2m_max_{m_key}"
                vals = daily.get(key, [])
                if vals and vals[0] is not None:
                    models.append((m_name, float(vals[0])))

    wttr_max = _fetch_wttr_forecast_max(city_key, date_str)
    if wttr_max is not None:
        models.append(("wttr.in", wttr_max))

    wgov_max = _fetch_weather_gov_max(city_key, date_str)
    if wgov_max is not None:
        models.append(("Weather.gov", wgov_max))

    return models, om_data


def aggregate_forecasts(models: list[tuple[str, float]], city_key: str) -> dict:
    """Aggregates model forecasts with historical bias correction."""
    from database.database import get_model_corrections
    corrections = get_model_corrections(city_key)
    
    adjusted_models = []
    applied_corr_signals = []
    
    for name, val in models:
        corr = corrections.get(name, 0)
        if corr != 0:
            adj_val = val - corr
            adjusted_models.append((name, adj_val))
            applied_corr_signals.append(f"{name}: {corr:+.1f}°C correction")
        else:
            adjusted_models.append((name, val))

    if not adjusted_models:
        return {
            "consensus_max_c": None,
            "spread": None,
            "sources": [],
            "signals": [],
            "confidence": "low",
        }
    
    values = [m[1] for m in adjusted_models]
    names = [m[0] for m in adjusted_models]
    # ... (rest of the logic remains similar but uses values)
    avg = sum(values) / len(values)
    min_v, max_v = min(values), max(values)
    spread = max_v - min_v

    # Consensus: median is more robust
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2:
        median = sorted_vals[n // 2]
    else:
        median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2

    # Outliers: more than 2°C from median
    outliers = []
    for name, v in zip(names, values):
        if abs(v - median) > 2.0:
            outliers.append((name, v))

    signals = []
    if spread <= 1.0:
        signals.append(("green", f"Model consensus: spread {spread:.1f}°C — high confidence"))
        confidence = "high"
    elif spread <= 2.5:
        signals.append(("yellow", f"Consensus: spread {spread:.1f}°C — medium confidence"))
        confidence = "medium"
    else:
        signals.append(("yellow", f"Model spread {spread:.1f}°C — uncertainty"))
        confidence = "low"

    if applied_corr_signals:
        signals.append(("cyan", "ML Corrections applied: " + ", ".join(applied_corr_signals)))

    detail = ", ".join(f"{n}={v:.1f}°C" for n, v in zip(names, values))
    signals.append(("cyan", f"Models ({len(models)}): {detail}"))

    if outliers:
        out_str = ", ".join(f"{n}={v:.1f}°C" for n, v in outliers)
        signals.append(("yellow", f"Outliers: {out_str}"))

    return {
        "consensus_max_c": median,
        "consensus_mean_c": avg,
        "spread": spread,
        "sources": names,
        "models_raw": list(zip(names, values)),
        "signals": signals,
        "confidence": confidence,
        "min_model": min_v,
        "max_model": max_v,
    }