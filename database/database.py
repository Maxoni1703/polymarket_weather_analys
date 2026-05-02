import sqlite3
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "history.db")
KB_PATH = os.path.join(BASE_DIR, "data", "knowledge_base.md")

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
            analysis_data TEXT, -- JSON blob
            actual_max_c REAL,
            is_resolved INTEGER DEFAULT 0
        )
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS model_biases (model_name TEXT, city_key TEXT, bias_sum REAL, count INTEGER, PRIMARY KEY(model_name, city_key))")
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
    
    # Если анализ завершен (пик прошел), сразу помечаем как actual
    if sc.get("peak_done"):
        cur.execute("UPDATE analyses SET actual_max_c = ?, is_resolved = 1 WHERE id = (SELECT LAST_INSERT_ROWID())", (sc.get("best_max_c"),))
        _update_model_biases(ck, sc.get("models_raw"), sc.get("best_max_c"))

    conn.commit()
    conn.close()

def _update_model_biases(city_key, models_raw, actual_c):
    """
    Обновляет статистику смещения (bias) для каждой модели.
    bias = forecast - actual
    """
    if not models_raw or actual_c is None:
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for name, forecast in models_raw:
        bias = forecast - actual_c
        cur.execute("""
            INSERT INTO model_biases (model_name, city_key, bias_sum, count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(model_name, city_key) DO UPDATE SET
                bias_sum = bias_sum + EXCLUDED.bias_sum,
                count = count + 1
        """, (name, city_key, bias))
    conn.commit()
    conn.close()

def get_model_corrections(city_key):
    """
    Возвращает среднее смещение для каждой модели: {model_name: avg_bias}
    Если avg_bias > 0, значит модель завышает. Нужно вычитать.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT model_name, bias_sum, count FROM model_biases WHERE city_key = ?", (city_key,))
    rows = cur.fetchall()
    conn.close()
    return {r[0]: r[1]/r[2] for r in rows if r[2] > 0}
    
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
