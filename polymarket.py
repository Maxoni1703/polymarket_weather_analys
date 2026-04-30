"""
POLYMARKET API — автозагрузка цен на погодные маркеты.

Реальная структура (из дебага):
  Каждый диапазон = отдельный маркет Yes/No
  Slug: highest-temperature-in-miami-on-march-11-2026-84-85f
  Поиск: /markets?tag_id=... (теги по городам)
  Цены: outcomePrices["0.23","0.77"] — Yes=0.23, No=0.77
"""

import requests
import re
from datetime import datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
GAMMA = "https://gamma-api.polymarket.com"
H = {"User-Agent": UA}
TIMEOUT = 14


# ═══════════════════════════════════════════════════════════════════
#  ПОИСК ТЕГА ГОРОДА  (Miami=100937, London=100166)
# ═══════════════════════════════════════════════════════════════════

_TAG_CACHE = {
    "miami":  100937,
    "london": 100166,
}

def _find_city_tag(city_key: str) -> int | None:
    """Ищет tag_id для города. Возвращает закэшированный ID или ищет через API."""
    if city_key in _TAG_CACHE:
        return _TAG_CACHE[city_key]
    
    city_words = {
        "miami":  ["miami"],
        "london": ["london"],
    }
    keywords = city_words.get(city_key, [])
    
    try:
        r = requests.get(f"{GAMMA}/tags", headers=H, timeout=TIMEOUT)
        r.raise_for_status()
        for t in r.json():
            label = str(t.get("label", "")).lower()
            slug  = str(t.get("slug", "")).lower()
            if any(w in label or w in slug for w in keywords):
                tag_id = t.get("id")
                _TAG_CACHE[city_key] = tag_id
                return tag_id
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════
#  ЗАГРУЗКА МАРКЕТОВ ПО TAG_ID
# ═══════════════════════════════════════════════════════════════════

def _fetch_markets_by_tag(tag_id: int, limit: int = 50) -> list[dict]:
    """Все активные маркеты по тегу."""
    try:
        r = requests.get(
            f"{GAMMA}/markets",
            params={"tag_id": tag_id, "active": "true",
                    "closed": "false", "limit": limit},
            headers=H, timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════
#  ПОИСК ПО SLUG  (основной метод — надёжный)
# ═══════════════════════════════════════════════════════════════════

def _slug_for_range(city_key: str, range_label: str, date_str: str) -> str:
    """
    Строит slug по паттерну Polymarket:
    highest-temperature-in-miami-on-march-11-2026-84-85f
    """
    city = "miami" if city_key == "miami" else "london"
    
    # Форматируем дату: "2026-03-11" → "march-11-2026"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        month = dt.strftime("%B").lower()      # "march"
        day   = str(dt.day)                    # "11" (без нуля)
        year  = dt.strftime("%Y")              # "2026"
        date_part = f"{month}-{day}-{year}"
    except Exception:
        date_part = date_str

    # Нормализуем диапазон в slug-формат
    rng = (range_label
           .lower()
           .replace("°f", "f").replace("°c", "c")
           .replace("≥", "").replace(">=", "")
           .replace("≤", "").replace("<=", "")
           .replace(" ", "-").replace("–", "-")
           .replace("or-above", "orабove").replace("or-below", "orbelow"))
    
    # Специальные случаи Polymarket
    if city_key == "miami":
        if "or higher" in range_label:
            val = re.findall(r'\d+', range_label)[0]
            rng = f"{val}forавove" # "90forавove"
        elif "or below" in range_label:
            val = re.findall(r'\d+', range_label)[0]
            rng = f"{val}forbelow" # "75forbelow"
        else:
            # "84-85°F" → "84-85f"
            rng = re.sub(r'[°\s]', '', range_label.lower()).replace("f", "f")
            rng = rng.replace("–", "-")
    else:
        # Лондон: "14°C" → "14c"
        rng = range_label.lower().replace("°c", "c").replace("°", "c").replace(" ", "")

    return f"highest-temperature-in-{city}-on-{date_part}-{rng}"


def _fetch_by_slug(slug: str) -> dict | None:
    """Загружает маркет по точному slug."""
    try:
        r = requests.get(f"{GAMMA}/markets/{slug}", headers=H, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _extract_yes_price(market: dict) -> float | None:
    """Извлекает цену Yes из маркета (0.0–1.0 → вернём %)."""
    import json as _json
    
    outcomes_raw = market.get("outcomes", "[]")
    prices_raw   = market.get("outcomePrices", "[]")
    
    if isinstance(outcomes_raw, str):
        try: outcomes_raw = _json.loads(outcomes_raw)
        except: outcomes_raw = []
    if isinstance(prices_raw, str):
        try: prices_raw = _json.loads(prices_raw)
        except: prices_raw = []
    
    for i, outcome in enumerate(outcomes_raw):
        if str(outcome).lower() == "yes" and i < len(prices_raw):
            try:
                return round(float(prices_raw[i]) * 100, 1)
            except Exception:
                pass
    
    # Fallback: lastTradePrice
    ltp = market.get("lastTradePrice")
    if ltp is not None:
        try: return round(float(ltp) * 100, 1)
        except: pass
    
    return None


# ═══════════════════════════════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ — загрузка цен для всех диапазонов
# ═══════════════════════════════════════════════════════════════════

def fetch_city_markets(city_key: str) -> list[dict]:
    """
    Возвращает список маркетов: [{"title", "outcomes", "url", "slug"}]
    Совместимо с match_prices_to_ranges.
    """
    return []  # не используется напрямую — используй fetch_prices_for_ranges


def fetch_prices_for_ranges(city_key: str, ranges: list[str],
                             date_str: str | None = None) -> dict[int, float]:
    """
    Загружает цены Yes для каждого диапазона.
    Возвращает {range_idx: price_pct}.

    Стратегия:
    1. Найти tag_id города
    2. Загрузить все маркеты тега
    3. Сопоставить по question/slug
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    matched = {}

    # ── Метод 1: по тегу города ───────────────────────────────────
    tag_id = _find_city_tag(city_key)
    if tag_id:
        markets = _fetch_markets_by_tag(tag_id, limit=60)
        matched = _match_markets_to_ranges(markets, ranges, city_key, date_str)
        if matched:
            return matched

    # ── Метод 2: по slug (перебираем каждый диапазон) ─────────────
    for idx, rng in enumerate(ranges):
        slug = _slug_for_range(city_key, rng, date_str)
        m = _fetch_by_slug(slug)
        if m:
            price = _extract_yes_price(m)
            if price is not None:
                matched[idx] = price

    return matched


def _match_markets_to_ranges(markets: list[dict], ranges: list[str],
                               city_key: str, date_str: str) -> dict[int, float]:
    """Сопоставляет список маркетов с диапазонами GUI."""
    matched = {}
    
    # Форматируем дату для поиска в question
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        date_variants = [
            dt.strftime("%B %-d"),          # "March 11"  (Linux)
            dt.strftime("%B %d").lstrip("0").replace(" 0", " "),  # "March 11"
            dt.strftime("%b %d"),            # "Mar 11"
            date_str,                        # "2026-03-11"
        ]
    except Exception:
        date_variants = [date_str]

    city_word = "miami" if city_key == "miami" else "london"

    for m in markets:
        question = m.get("question", "").lower()
        
        # Проверяем что маркет про нужный город
        if city_word not in question:
            continue
        
        price = _extract_yes_price(m)
        if price is None:
            continue

        # Сопоставляем с диапазоном
        for idx, rng in enumerate(ranges):
            if idx in matched:
                continue
            if _question_matches_range(question, rng, city_key):
                matched[idx] = price
                break

    return matched


def _question_matches_range(question: str, gui_range: str, city_key: str) -> bool:
    """
    Проверяет совпадение вопроса маркета и диапазона GUI.
    """
    q = question.lower()
    r = gui_range.lower().strip()

    if city_key == "miami":
        # Нормализуем диапазон
        r_norm = r.replace("°f", "").replace("°", "").replace(" ", "").replace("–", "-")
        
        # Граничные случаи
        if "or higher" in r:
            val = re.findall(r'\d+', r)[0]
            return val in q and ("above" in q or "over" in q or "higher" in q or "≥" in q or ">=" in q)
        if "or below" in r:
            val = re.findall(r'\d+', r)[0]
            return val in q and ("below" in q or "under" in q or "lower" in q or "≤" in q or "<=" in q)
        
        # Обычный диапазон "84-85" → ищем "84-85" или "84–85" в вопросе
        nums = re.sub(r'[^0-9\-]', '', r_norm)  # "84-85" или "86"
        if nums and nums in q.replace("–", "-"):
            return True
            
    else:  # london °C
        r_norm = r.replace("°c", "").replace("°", "").replace(" ", "")
        # "14" → ищем "14°c" или "be 14" в вопросе
        if r_norm.isdigit() and f" {r_norm}°" in question.replace("°c", "°"):
            return True
        if r_norm.isdigit() and f"be {r_norm}" in q:
            return True

    return False


# Обратная совместимость с gui.py
def match_prices_to_ranges(markets: list[dict], city_key: str,
                            ranges: list[str]) -> dict[int, float]:
    """Обёртка для совместимости — использует fetch_prices_for_ranges."""
    return fetch_prices_for_ranges(city_key, ranges)