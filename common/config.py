"""
POLYMARKET WEATHER ANALYZER — Configuration
Colors, fonts, cities, constants.
"""

# ═══════════════════════════════════════════════════════════════════
#  COLORS
# ═══════════════════════════════════════════════════════════════════
T = {
    "bg":     "#0D1117", "card":   "#161B22", "card2":  "#1C2128",
    "blue":   "#58A6FF", "green":  "#3FB950", "red":    "#F85149",
    "yellow": "#D29922", "cyan":   "#39D5FF", "orange": "#FF6E40",
    "fg":     "#E6EDF3", "dim":    "#8B949E", "muted":  "#484F58",
    "border": "#30363D", "london": "#4493F8", "miami":  "#FF7043",
    "purple": "#BC8CFF",
}

# ═══════════════════════════════════════════════════════════════════
#  FONTS
# ═══════════════════════════════════════════════════════════════════
F = {
    "title":   ("Consolas", 17, "bold"),
    "head":    ("Consolas", 12, "bold"),
    "body":    ("Consolas", 11),
    "small":   ("Consolas", 9),
    "tiny":    ("Consolas", 8),
    "big":     ("Consolas", 28, "bold"),
    "verdict": ("Consolas", 13, "bold"),
    "label":   ("Consolas", 10),
}

# ═══════════════════════════════════════════════════════════════════
#  CITIES CONFIG
# ═══════════════════════════════════════════════════════════════════
CITIES = {
    "london": {
        "name":       "LONDON",
        "flag":       "🇬🇧",
        "lat":        51.4775,
        "lon":        -0.4614,
        "station":    "Heathrow (EGLL)",
        "station_icao": "EGLL",
        "avg_c":      9.0,
        "unit":       "C",
        "peak_start": 14,
        "peak_end":   16,
        "peak_label": "14:00–16:00 London",
        "color":      T["london"],
        "tz_name":    "Europe/London",
        "wunder_url": "https://www.wunderground.com/dashboard/pws/IEGLL",
        "wunder_station": "EGLL / Heathrow",
        "wunder_url2": "https://www.wunderground.com/weather/gb/london",
        "ranges":     ["14°C", "15°C", "16°C", "17°C", "18°C", "19°C", "20°C",
                      "21°C", "22°C", "23°C", "24°C", "25°C or higher"],
        "range_type": "exact",
        "tips": [
            "Heathrow is 1–2°C warmer than the center",
            "Atlantic front = warmth + rain",
            "Market overestimates snow in March",
        ],
    },
    "miami": {
        "name":       "MIAMI",
        "flag":       "🇺🇸",
        "lat":        25.7959,
        "lon":        -80.2870,
        "station":    "KMIA (Miami Intl Airport)",
        "station_icao": "KMIA",
        "avg_c":      26.1,
        "unit":       "F",
        "peak_start": 14,
        "peak_end":   16,
        "peak_label": "14:30–16:00 ET",
        "color":      T["miami"],
        "tz_name":    "America/New_York",
        "wunder_url": "https://www.wunderground.com/history/daily/us/fl/miami/KMIA",
        "wunder_station": "KMIA",
        "wunder_url2": "https://www.wunderground.com/weather/us/fl/miami",
        "ranges":     ["75°F or below", "76–77°F", "78–79°F", "80–81°F", "82–83°F", "84–85°F", "86–87°F", "88–89°F", "90°F or higher"],
        "range_type": "band",
        "tips": [
            "KMIA High = max METAR for the ENTIRE day",
            "Peak: 14:30–16:00 Eastern Time",
            "Showers cool by 3–5°F in 15 minutes",
        ],
    },
}

# ═══════════════════════════════════════════════════════════════════
#  WMO WEATHER CODES → EMOJI
# ═══════════════════════════════════════════════════════════════════
WX_ICONS = {
    0: "☀", 1: "🌤", 2: "⛅", 3: "☁", 45: "🌫", 48: "🌫",
    51: "🌦", 53: "🌦", 55: "🌧", 61: "🌧", 63: "🌧", 65: "🌧",
    71: "🌨", 73: "❄", 75: "❄", 80: "🌦", 81: "🌧", 82: "⛈",
    95: "⛈", 96: "⛈", 99: "⛈",
}
