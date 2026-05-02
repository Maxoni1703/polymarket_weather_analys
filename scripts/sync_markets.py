import requests
import sqlite3
import json
import os
import sys
from datetime import datetime

# Добавляем корень проекта в путь, чтобы работали импорты
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Конфигурация
GAMMA_API = "https://gamma-api.polymarket.com/markets"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "history.db")

# Теги городов на Polymarket
TAGS = {
    "miami": 100937,
    "london": 100166,
}

def sync_polymarket_history():
    """Синхронизирует историю всех рынков по городам из конфига."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Начало синхронизации рынков...")
    
    # 1. Инициализация БД
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS polymarket_outcomes (
            id TEXT PRIMARY KEY,
            city_key TEXT,
            question TEXT,
            market_slug TEXT,
            end_date TEXT,
            outcomes TEXT,      -- JSON [Yes, No]
            outcome_prices TEXT, -- JSON [0.23, 0.77]
            status TEXT,
            last_update DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    total_new = 0
    
    for city_key, tag_id in TAGS.items():
        print(f" -> Обработка {city_key.upper()} (tag {tag_id})...")
        
        # Получаем и закрытые, и открытые рынки
        try:
            # Запрашиваем закрытые (история)
            r_closed = requests.get(GAMMA_API, params={
                "tag_id": tag_id, "limit": 100, "active": "false", "closed": "true"
            }, timeout=15)
            r_closed.raise_for_status()
            closed_markets = r_closed.json()
            
            # Запрашиваем активные (текущие)
            r_active = requests.get(GAMMA_API, params={
                "tag_id": tag_id, "limit": 20, "active": "true", "closed": "false"
            }, timeout=15)
            r_active.raise_for_status()
            active_markets = r_active.json()
            
            all_markets = closed_markets + active_markets
            print(f"    Найдено рынков: {len(all_markets)}")
            
            for m in all_markets:
                m_id = m.get("id")
                # Фильтруем, чтобы брать только погодные рынки (на всякий случай)
                question = m.get("question", "")
                if "temperature" not in question.lower():
                    continue
                    
                cur.execute("""
                    INSERT OR REPLACE INTO polymarket_outcomes 
                    (id, city_key, question, market_slug, end_date, outcomes, outcome_prices, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    m_id, 
                    city_key,
                    question,
                    m.get("slug"),
                    m.get("endDate"),
                    json.dumps(m.get("outcomes")),
                    json.dumps(m.get("outcomePrices")),
                    "closed" if m.get("closed") else "active"
                ))
                total_new += 1
                
        except Exception as e:
            print(f"    [!] Ошибка для {city_key}: {e}")

    conn.commit()
    conn.close()
    print(f"--- Синхронизация завершена. Обработано записей: {total_new} ---")
    
    # 2. Запуск ИИ-самообучения (AI Reflector)
    try:
        from ai.ai_reflector import reflect
        print("[AI] Запуск анализа для самообучения...")
        reflect()
        print("[AI] Анализ завершен, база знаний обновлена.")
    except Exception as e:
        print(f"[AI] [!] Ошибка при самообучении: {e}")

if __name__ == "__main__":
    sync_polymarket_history()
