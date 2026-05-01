"""
POLYMARKET WEATHER ANALYZER — Логика погоды v6.0
Улучшения: AviationWeather METAR API, взвешивание моделей,
улучшенный анализ с учётом реальных данных.
"""

import requests
from datetime import datetime, timezone

from config import CITIES
from utils import c2f
from models import fetch_all_models_max, aggregate_forecasts


# ── AviationWeather METAR API ──────────────────────────────────
# Официальный METAR API от FAA/NOAA — точные данные со станций
_AVIATION_API = "https://aviationweather.gov/api/data/metar"
UA = {"User-Agent": "PolymarketWeatherAnalyzer/6.0"}


def _fetch_metar_history(icao: str, hours: int = 12) -> list[dict]:
    """
    Получает температуры из реальных METAR-наблюдений за последние N часов.
    Возвращает список словарей {"temp": float, "time": datetime} (от новых к старым).
    """
    try:
        r = requests.get(
            _AVIATION_API,
            params={"ids": icao, "format": "json", "hours": hours},
            headers=UA,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        results = []
        for obs in data:
            t = obs.get("temp")
            # API может использовать obsTime или reportTime (могут быть строками или интами)
            raw_time = obs.get("obsTime") or obs.get("reportTime")
            if t is not None and raw_time:
                try:
                    # Если raw_time — это timestamp (int/float)
                    if isinstance(raw_time, (int, float)):
                        ts = datetime.fromtimestamp(raw_time, tz=timezone.utc)
                    else:
                        # Если вдруг строка (старое поведение API)
                        ts = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                    
                    results.append({"temp": float(t), "time": ts})
                except (ValueError, TypeError):
                    pass
        return results  # уже отсортированы от новых к старым
    except Exception:
        return []


def _fetch_metar_max_today(icao: str, city_key: str) -> float | None:
    """
    Максимальная темп из METAR за сегодня (до текущего момента).
    Используется AviationWeather API.
    """
    from utils import _city_now
    now = _city_now(city_key)
    # Сегодняшний день в локальном времени
    today = now.date()

    # Берём наблюдения за последние 24 часов
    history = _fetch_metar_history(icao, hours=24)
    if not history:
        return None

    # Фильтруем только за сегодняшний календарный день в локальном времени города
    # API возвращает время в UTC, например '2025-03-13 18:50:00'
    today_temps = []
    # Конвертируем UTC наблюдения в локальное время для сравнения даты
    # Но проще проверить, совпадает ли дата в локальной зоне
    import utils
    if getattr(utils, "_HAS_ZONEINFO", False):
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(CITIES[city_key]["tz_name"])
    else:
        from datetime import timezone as dt_timezone, timedelta
        tz = dt_timezone(timedelta(hours=30)) # Fallback

    for obs in history:
        # Приводим UTC время к локальному времени города
        local_obs_time = obs["time"].astimezone(tz)
        if local_obs_time.date() == today:
            today_temps.append(obs["temp"])

    if today_temps:
        return max(today_temps)
    return None


# ── wttr.in (METAR наблюдения) ─────────────────────────────────

def fetch_wunderground(city_key: str) -> dict | None:
    """
    Получает реальную текущую температуру:
    1. AviationWeather METAR (точнее всего)
    2. wttr.in — METAR наблюдения (fallback)
    3. Open-Meteo current — последний fallback
    """
    result = _fetch_aviation_weather(city_key)
    if result:
        return result
    result = _fetch_wttr(city_key)
    if result:
        return result
    return _fetch_openmeteo_current(city_key)


def _fetch_aviation_weather(city_key: str) -> dict | None:
    """
    AviationWeather.gov METAR API.
    Наиболее точные реальные наблюдения для аэропортных станций.
    """
    c = CITIES[city_key]
    icao = c.get("station_icao")
    if not icao:
        return None

    try:
        from utils import _city_now
        r = requests.get(
            _AVIATION_API,
            params={"ids": icao, "format": "json", "hours": 1},
            headers=UA,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return None

        obs = data[0]  # самое свежее наблюдение
        cur_c = obs.get("temp")
        if cur_c is None:
            return None
        cur_c = float(cur_c)
        cur_f = c2f(cur_c)

        # Санитарная проверка
        if city_key == "miami" and not (10 <= cur_c <= 45):
            return None
        if city_key == "london" and not (-15 <= cur_c <= 40):
            return None

        # High из наблюдений за сегодня
        from utils import _city_now
        now_local = _city_now(city_key)
        today_str = now_local.strftime("%Y-%m-%d")

        history = _fetch_metar_history(icao, hours=24)
        
        import utils
        if getattr(utils, "_HAS_ZONEINFO", False):
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(c["tz_name"])
        else:
            from datetime import timezone as dt_timezone, timedelta
            tz = dt_timezone(timedelta(hours=31)) # Placeholder offset

        today_temps = [
            obs["temp"] for obs in history 
            if obs["time"].astimezone(tz).date() == now_local.date()
        ]
        
        n_obs = len(today_temps)
        high_c = max(today_temps) if today_temps else cur_c
        high_f = c2f(high_c)

        return {
            "current_c": cur_c, "current_f": cur_f,
            "high_c": high_c, "high_f": high_f,
            "n_obs": n_obs,
            "source": f"AviationWeather METAR {icao} ({n_obs} obs сегодня)",
        }
    except Exception:
        return None


def _fetch_wttr(city_key: str) -> dict | None:
    """
    wttr.in JSON API — real METAR data.
    """
    c = CITIES[city_key]
    query = f"{c['lat']},{c['lon']}"
    try:
        r = requests.get(
            f"https://wttr.in/{query}?format=j1",
            headers={"User-Agent": "curl/7.68.0"},
            timeout=10)
        r.raise_for_status()
        data = r.json()
        cc = data["current_condition"][0]
        cur_c = float(cc["temp_C"])
        cur_f = float(cc["temp_F"])

        if city_key == "miami" and not (10 <= cur_c <= 45):
            return None
        if city_key == "london" and not (-15 <= cur_c <= 40):
            return None

        from utils import _city_now
        now_local = _city_now(city_key)
        current_hour = now_local.hour

        observed_temps = []
        weather = data.get("weather", [])
        if weather:
            w0 = weather[0]
            for h in w0.get("hourly", []):
                try:
                    h_hour = int(h.get("time", 0)) // 100
                except Exception:
                    continue
                if h_hour <= current_hour:
                    try:
                        observed_temps.append(float(h["tempC"]))
                    except Exception:
                        pass

        observed_temps.append(cur_c)

        if observed_temps:
            high_c = max(observed_temps)
            high_f = c2f(high_c)
        else:
            high_c, high_f = None, None

        if high_c is not None:
            if city_key == "miami" and not (15 <= high_c <= 45):
                high_c, high_f = None, None
            elif city_key == "london" and not (-5 <= high_c <= 35):
                high_c, high_f = None, None

        n_obs = len(observed_temps)
        return {
            "current_c": cur_c, "current_f": cur_f,
            "high_c": high_c, "high_f": high_f,
            "n_obs": n_obs,
            "source": f"wttr.in METAR ({n_obs} obs)",
        }
    except Exception:
        return None


def _fetch_openmeteo_current(city_key: str) -> dict | None:
    """Open-Meteo current weather."""
    c = CITIES[city_key]
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={c['lat']}&longitude={c['lon']}"
            "&current=temperature_2m"
            "&daily=temperature_2m_max"
            "&forecast_days=1&timezone=auto"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        cur_c = data.get("current", {}).get("temperature_2m")
        if cur_c is None:
            return None
        high_c = None
        maxes = data.get("daily", {}).get("temperature_2m_max", [])
        if maxes:
            high_c = maxes[0]
        return {
            "current_c": cur_c, "current_f": c2f(cur_c),
            "high_c": high_c, "high_f": c2f(high_c) if high_c else None,
            "n_obs": 0,
            "source": "Open-Meteo (модель)",
        }
    except Exception:
        return None


def fetch_forecast(city_key: str) -> dict:
    """Open-Meteo прогноз на 4 дня (fallback)."""
    c = CITIES[city_key]
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={c['lat']}&longitude={c['lon']}"
        "&daily=temperature_2m_max,temperature_2m_min"
        ",precipitation_probability_max,windspeed_10m_max,weathercode"
        "&hourly=relativehumidity_2m,temperature_2m"
        "&forecast_days=4&timezone=auto"
    )
    r = requests.get(url, timeout=12)
    r.raise_for_status()
    return r.json()


def fetch_multimodel_forecast(city_key: str, date_str: str | None = None) -> tuple[dict | None, dict]:
    """
    Собирает прогнозы из нескольких моделей, агрегирует.
    date_str: 'YYYY-MM-DD' для конкретной даты, None = сегодня.
    Возвращает (om_data для analyze, aggregate_info).
    """
    models_list, om_data = fetch_all_models_max(city_key, date_str=date_str)
    agg = aggregate_forecasts(models_list, city_key)
    return om_data, agg


def analyze_forecast(data: dict | None, city_key: str, consensus_max_c: float | None = None) -> dict:
    """Анализ данных прогноза. consensus_max_c — консенсус мульти-моделей (приоритет над Open-Meteo)."""
    if data is None:
        # Возвращаем пустую структуру, чтобы программа не падала
        return {
            "today_max_c": 0, "om_max_c": 0, "today_min_c": 0,
            "precip_prob": 0, "wind_max": 0, "wx_code": 0,
            "day_range_c": 0, "deviation_c": 0, "avg_humidity": 0,
            "maxes_c": [], "trend": "→ НЕТ ДАННЫХ", "hour_temps_c": [],
        }
    
    c = CITIES[city_key]
    d = data.get("daily", {})
    h = data.get("hourly", {})
    
    raw_max = d.get("temperature_2m_max", [])
    raw_min = d.get("temperature_2m_min", [])
    precip_raw = d.get("precipitation_probability_max", [])
    wind_raw = d.get("windspeed_10m_max", [])
    wx_raw = d.get("weathercode", [])

    # Мы ожидаем, что в data уже отфильтрованы данные под нужную дату (offset 0)
    # или список начинается с нужной даты.
    om_max = raw_max[0] if raw_max else 0
    today_max_c = consensus_max_c if consensus_max_c is not None else om_max
    today_min_c = raw_min[0] if raw_min else 0
    precip_prob = precip_raw[0] if precip_raw else 0
    wind_max = wind_raw[0] if wind_raw else 0
    wx_code = wx_raw[0] if wx_raw else 0
    day_range_c = today_max_c - today_min_c
    deviation_c = today_max_c - c["avg_c"]
    hum_vals = (h.get("relativehumidity_2m") or h.get("relativehumidity_2m_best_match") or [])[:24]
    avg_humidity = sum(hum_vals) / len(hum_vals) if hum_vals else 0
    hour_temps_c = (h.get("temperature_2m") or h.get("temperature_2m_best_match") or [])[:24]
    maxes_c = [raw_max[i] for i in range(min(4, len(raw_max)))]
    trend = "→ СТАБИЛЬНО"
    if len(maxes_c) >= 3:
        delta = maxes_c[2] - maxes_c[0]
        if delta >= 3:
            trend = "↑ ТЕПЛЕЕТ"
        elif delta <= -3:
            trend = "↓ ХОЛОДАЕТ"
    return {
        "today_max_c": today_max_c,
        "om_max_c": om_max,
        "today_min_c": today_min_c,
        "precip_prob": precip_prob, "wind_max": wind_max,
        "wx_code": wx_code, "day_range_c": day_range_c,
        "deviation_c": deviation_c, "avg_humidity": avg_humidity,
        "maxes_c": maxes_c, "trend": trend,
        "hour_temps_c": hour_temps_c,
    }


def _weighted_consensus(models: list[tuple[str, float]], city_key: str) -> float | None:
    """
    Взвешенный консенсус моделей.
    ECMWF лучше для Европы (Лондон), GFS/Weather.gov для США (Майами).
    """
    if not models:
        return None

    # Веса по модели и городу
    WEIGHTS = {
        "london": {
            "ECMWF":       4.0,  # лучший для Европы
            "ICON":        3.0,  # немецкая модель, отлично для Европы
            "GEM":         2.0,
            "GFS":         1.5,
            "JMA":         1.0,
            "Open-Meteo":  1.5,  # best_match — микс
            "wttr.in":     1.0,
            "Weather.gov": 0.0,  # не применимо для Лондона
        },
        "miami": {
            "ECMWF":       2.0,
            "GFS":         4.0,  # лучший для США
            "Weather.gov": 4.0,  # официальный NWS
            "ICON":        1.5,
            "GEM":         2.0,
            "JMA":         0.5,
            "Open-Meteo":  1.5,
            "wttr.in":     1.0,
        },
    }
    city_weights = WEIGHTS.get(city_key, {})

    total_w = 0.0
    total_wv = 0.0
    for name, val in models:
        w = city_weights.get(name, 1.0)
        if w <= 0:
            continue
        total_w += w
        total_wv += w * val

    if total_w == 0:
        return sum(v for _, v in models) / len(models)
    return total_wv / total_w


def compute_score(a, wunder, local_time, city_key, market_prob, range_idx, peak_passed_manual, agg_signals=None, models_raw=None):
    """
    Скоринг v6.0: взвешенный консенсус + METAR High + взвешенные модели.
    """
    c = CITIES[city_key]
    pts = 50
    sig = list(agg_signals or [])
    forecast_max_c = a["today_max_c"]
    forecast_max_f = c2f(forecast_max_c)
    best_max_c = forecast_max_c
    best_max_f = forecast_max_f
    wunder_ok = False

    # ── METAR / Wunderground ─────────────────────────────────────
    if wunder:
        wunder_ok = True
        cur_c = wunder["current_c"]
        cur_f = wunder["current_f"]
        n_obs = wunder.get("n_obs", 0)
        wh_c  = wunder.get("high_c")
        wh_f  = wunder.get("high_f")
        src   = wunder.get("source", "Наблюдения")

        if wh_c is not None:
            after_peak = local_time.get("after_peak", False)
            # Если накоплено 6+ наблюдений И High выше текущей — надёжно
            high_reliable = after_peak or (n_obs >= 6 and wh_c >= cur_c)

            if high_reliable:
                best_max_c, best_max_f = wh_c, wh_f
                sig.append(("green",
                    f"METAR High: {wh_f:.0f}°F ({wh_c:.1f}°C)"
                    f" [{src}] {'✓ пик прошёл' if after_peak else f'{n_obs} obs'}"))
                # Если High != прогноз — штраф/бонус
                diff = abs(wh_c - forecast_max_c)
                if diff <= 1.0:
                    pts += 10
                    sig.append(("green", f"METAR совпадает с прогнозом (Δ{diff:.1f}°C)"))
                elif diff <= 2.5:
                    pts += 3
                    sig.append(("yellow", f"METAR расходится с прогнозом (Δ{diff:.1f}°C)"))
                else:
                    pts -= 8
                    sig.append(("red", f"METAR сильно расходится с прогнозом (Δ{diff:.1f}°C)"))
            else:
                best_max_c = max(wh_c, cur_c, forecast_max_c)
                best_max_f = c2f(best_max_c)
                sig.append(("yellow",
                    f"Сейчас {cur_f:.0f}°F, High {wh_f:.0f}°F"
                    f" ({n_obs} obs) — ещё может расти"))
        else:
            best_max_c = max(cur_c, forecast_max_c)
            best_max_f = c2f(best_max_c)
            if city_key == "miami":
                sig.append(("cyan", f"Сейчас {cur_f:.0f}°F ({cur_c:.1f}°C)"))
            else:
                sig.append(("cyan", f"Сейчас {cur_c:.1f}°C ({cur_f:.0f}°F)"))
            if abs(cur_c - forecast_max_c) <= 1.5:
                pts += 8
                sig.append(("green", "Наблюдение и прогноз сходятся"))
            else:
                pts -= 5
                if city_key == "miami":
                    sig.append(("yellow",
                        f"Расхождение: прогноз {forecast_max_f:.0f}°F vs факт {cur_f:.0f}°F"))
                else:
                    sig.append(("yellow",
                        f"Расхождение: прогноз {forecast_max_c:.1f}°C vs факт {cur_c:.1f}°C"))
    else:
        sig.append(("yellow", "Наблюдения недоступны — только прогноз моделей"))

    # ── Время суток / пик ────────────────────────────────────────
    lt = local_time
    auto_peak = lt["after_peak"]
    peak_done = peak_passed_manual or auto_peak
    if peak_done:
        pts += 25
        city_name = "Майами" if city_key == "miami" else "Лондоне"
        if auto_peak and not peak_passed_manual:
            sig.append(("green", f"Время в {city_name} {lt['local_str']} — пик пройден автоматически"))
        else:
            sig.append(("green", "ЧАС ПИКА ПРОШЁЛ — максимум зафиксирован"))
        sig.append(("green", f"Итоговый максимум: {best_max_f:.0f}°F ({best_max_c:.1f}°C)" if city_key == "miami"
                    else f"Итоговый максимум: {best_max_c:.1f}°C ({best_max_f:.0f}°F)"))
    elif lt["during_peak"]:
        pts += 10
        city_name = "Майами" if city_key == "miami" else "Лондоне"
        sig.append(("yellow", f"СЕЙЧАС ЧАС ПИКА в {city_name} ({lt['local_str']}) — t° растёт"))
        sig.append(("yellow", "Максимум ещё не зафиксирован — осторожно"))
    else:
        city_name = "Майами" if city_key == "miami" else "Лондон"
        sig.append(("yellow", f"{city_name} сейчас {lt['local_str']} ({lt['day_phase']}) — до пика {c['peak_label']}"))

    # ── Попадание в диапазон ─────────────────────────────────────
    # --- Кастомная логика Майами vs Лондон ---
    if c["range_type"] == "exact":
        label = c["ranges"][range_idx]
        target = float(label.replace("°C", ""))
        in_range = (target - 0.5) <= best_max_c < (target + 0.5)
        val_str = f"{best_max_c:.1f}°C"
        rng_name = label
    else:
        mf = c2f(best_max_c)
        # Ranges for Miami: 75 or below, 76-77, 78-79, 80-81, 82-83, 84-85, 86-87, 88-89, 90 or higher
        LO = [None, 76, 78, 80, 82, 84, 86, 88, 90]
        HI = [76, 78, 80, 82, 84, 86, 88, 90, None]
        
        # Ensure index is within bounds (safety check)
        ridx = min(max(0, range_idx), len(LO)-1)
        lo, hi = LO[ridx], HI[ridx]
        in_range = (lo is None or mf >= lo) and (hi is None or mf < hi)
        val_str = f"{mf:.0f}°F"
        rng_name = c["ranges"][range_idx]

    if in_range:
        pts += 22
        sig.append(("green", f"Прогноз {val_str} ПОПАДАЕТ в {rng_name} ✓"))
    else:
        pts -= 22
        if city_key == "london":
            target = float(rng_name.replace("°C", ""))
            diff = abs(best_max_c - target)
            sig.append(("red", f"Прогноз {val_str}, выбрано {rng_name} — разница {diff:.1f}°C"))
        else:
            sig.append(("red", f"Прогноз {val_str} НЕ попадает в {rng_name}"))

    # ── Отклонение от нормы ──────────────────────────────────────
    dev = a["deviation_c"]
    if abs(dev) >= 7:
        pts -= 28
        sig.append(("red", f"АНОМАЛИЯ ВЫСОКАЯ: {dev:+.1f}°C от нормы"))
    elif abs(dev) >= 4:
        pts -= 12
        sig.append(("yellow", f"Аномалия умеренная: {dev:+.1f}°C от нормы"))
    else:
        pts += 12
        sig.append(("green", f"t° близка к норме: {dev:+.1f}°C"))

    # ── Суточный диапазон ────────────────────────────────────────
    rng = a["day_range_c"]
    if rng <= 5:
        pts += 12
        sig.append(("green", f"Суточный диапазон мал ({rng:.1f}°C) — стабильно"))
    elif rng > 9:
        pts -= 18
        sig.append(("red", f"Большой диапазон ({rng:.1f}°C) — высокая неопределённость"))

    # ── Осадки ──────────────────────────────────────────────────
    prec = a["precip_prob"]
    if city_key == "london":
        if prec >= 75:
            pts -= 14
            sig.append(("red", f"Высокий риск дождя ({prec}%) — может снизить t°"))
        elif prec <= 20:
            pts += 8
            sig.append(("green", f"Дождь маловероятен ({prec}%)"))
    else:
        if prec >= 65:
            pts -= 18
            sig.append(("red", f"Риск тропических ливней ({prec}%) — охлаждение 3–5°F"))
        elif prec <= 25:
            pts += 8
            sig.append(("green", f"Ливни маловероятны ({prec}%)"))

    # ── Ветер ────────────────────────────────────────────────────
    wind = a["wind_max"]
    if wind >= 55:
        pts -= 10
        sig.append(("red", f"Сильный ветер ({wind:.0f} км/ч)"))
    elif wind <= 20:
        pts += 5
        sig.append(("green", f"Слабый ветер ({wind:.0f} км/ч)"))

    # ── Влажность (только Майами) ────────────────────────────────
    hum = a["avg_humidity"]
    if city_key == "miami" and hum >= 80:
        sig.append(("yellow", f"Влажность {hum:.0f}% — риск ливня повышен"))

    # ── Рыночная вероятность / Edge ──────────────────────────────
    our_prob = min(95, max(5, pts))
    edge, mkt_rec = None, None
    if market_prob is not None:
        edge = our_prob - market_prob
        if edge >= 15:
            pts += 25
            sig.append(("green", f"EDGE +{edge:.0f}%: НЕДООЦЕНЁН → ПОКУПАЙ ДА"))
            mkt_rec = "ДА"
        elif edge <= -15:
            pts += 20
            sig.append(("green", f"EDGE {edge:.0f}%: ПЕРЕОЦЕНЁН → ПОКУПАЙ НЕТ"))
            mkt_rec = "НЕТ"
        else:
            sig.append(("yellow", f"Рынок справедлив (edge {edge:+.0f}%) → пропусти"))
            mkt_rec = "ПРОПУСТИТЬ"

    pts = min(100, max(0, pts))
    our_prob = min(95, max(5, pts))

    # Корректируем вердикт на основе Edge
    if edge is not None and edge < 5 and mkt_rec != "НЕТ":
        verdict, bank = "⚠   ПРОПУСТИТЬ", "0%"
    elif mkt_rec == "НЕТ":
        verdict, bank = "✅  ВХОДИТЬ (НЕТ)", "3–5%"
    elif pts >= 78:
        verdict, bank = "✅  ВХОДИТЬ", "5–7%"
    elif pts >= 62:
        verdict, bank = "⚡  ОСТОРОЖНО", "3–5%"
    elif pts >= 46:
        verdict, bank = "⚠   ПОДОЖДАТЬ", "0–3%"
    else:
        verdict, bank = "❌  НЕ ВХОДИТЬ", "0%"

    return {
        "score": pts, "our_prob": our_prob,
        "verdict": verdict, "bank": bank,
        "signals": sig, "edge": edge, "mkt_rec": mkt_rec,
        "in_range": in_range,
        "best_max_c": best_max_c, "best_max_f": c2f(best_max_c),
        "models_raw": models_raw,
        "wunder_ok": wunder_ok, "auto_peak": auto_peak,
        "peak_done": peak_done,
        "local_str": lt["local_str"], "day_phase": lt["day_phase"],
    }