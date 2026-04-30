import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "history.db")
KB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.md")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            city_key TEXT,
            target_date TEXT,
            market_price REAL,
            range_name TEXT,
            forecast_c REAL,
            forecast_f REAL,
            in_range INTEGER,
            verdict TEXT,
            score_data TEXT,  -- JSON blob
            analysis_data TEXT -- JSON blob
        )
    """)
    conn.commit()
    conn.close()

def save_analysis(ck, date_str, market_price, range_name, sc, ao):
    """
    Сохраняет полный результат анализа в БД.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO analyses (city_key, target_date, market_price, range_name, forecast_c, forecast_f, in_range, verdict, score_data, analysis_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ck, date_str, market_price, range_name,
        sc.get("best_max_c"), sc.get("best_max_f"),
        1 if sc.get("in_range") else 0,
        sc.get("verdict"),
        json.dumps(sc),
        json.dumps(ao)
    ))
    conn.commit()
    conn.close()
    
    # После сохранения обновляем подсказки в .md
    update_knowledge_from_history()

def update_knowledge_from_history():
    """
    Анализирует последние записи в БД и обновляет секцию в knowledge_base.md
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Берем последние 5 анализов
    cur.execute("SELECT city_key, target_date, forecast_c, verdict FROM analyses ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return

    history_text = "\n## 5. ИСТОРИЯ ПОСЛЕДНИХ АНАЛИЗОВ (ДЛЯ ОБУЧЕНИЯ)\n"
    for r in rows:
        history_text += f"* [{r[1]}] {r[0].upper()}: Прогноз {r[2]}°C. Вердикт: {r[3]}\n"
    
    # Читаем текущий файл
    if os.path.exists(KB_PATH):
        with open(KB_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Если секция уже есть, заменяем её, если нет — добавляем в конец
        if "## 5. ИСТОРИЯ" in content:
            parts = content.split("## 5. ИСТОРИЯ")
            new_content = parts[0] + history_text
        else:
            new_content = content + "\n" + history_text
            
        with open(KB_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)

# Инициализируем БД при импорте
init_db()
