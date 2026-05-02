import sqlite3
import json
import os
import re
from datetime import datetime

# Пути к данным
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "history.db")
KB_PATH = os.path.join(BASE_DIR, "data", "knowledge_base.md")

def get_winning_outcomes():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Берем все закрытые рынки
    cur.execute("SELECT city_key, question, end_date, outcome_prices FROM polymarket_outcomes WHERE status = 'closed'")
    rows = cur.fetchall()
    conn.close()
    
    winners = []
    for r in rows:
        try:
            # Парсим дважды, так как в базе лежит строка с JSON-строкой
            prices_str = json.loads(r['outcome_prices'])
            prices = json.loads(prices_str)
            if prices[0] == "1": # Yes выиграл
                winners.append(r)
        except:
            continue
    return winners

def parse_temperature(question):
    # Пытаемся вытащить диапазон из вопроса
    # 1. Диапазоны типа 81-82, 8182, between 76-77
    # Добавляем \D* перед F, так как там может быть мусор (F)
    match = re.search(r"(\d+)\D+(\d+)\D*F", question)
    if match:
        return f"{match.group(1)}-{match.group(2)}°F"
    
    # 2. Одиночные пороги: 82F or higher, 58F or below
    match = re.search(r"(\d+)\D*F or (below|lower)", question)
    if match:
        return f"<= {match.group(1)}°F"
    
    match = re.search(r"(\d+)\D*F or (higher|above)", question)
    if match:
        return f">= {match.group(1)}°F"
    
    return "Unknown"

def reflect():
    winners = get_winning_outcomes()
    if not winners:
        print("No winning outcomes found to analyze.")
        return

    city_stats = {} # {city: {range: count}}
    for w in winners:
        q = w['question']
        city = (w['city_key'] or 'unknown').upper()
        if city not in city_stats: city_stats[city] = {}
        
        temp_range = parse_temperature(q)
        if temp_range == "Unknown":
            print(f"[DEBUG] Не удалось распознать вопрос: {q}")
            
        city_stats[city][temp_range] = city_stats[city].get(temp_range, 0) + 1

    thoughts = []
    thoughts.append(f"### [Self-Learning] Анализ исходов по городам ({len(winners)} записей)")
    
    for city, stats in city_stats.items():
        # Сортируем исходы, убирая Unknown из топа для красоты
        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        valid_stats = [s for s in sorted_stats if s[0] != "Unknown"]
        
        thoughts.append(f"*   **{city}**:")
        if valid_stats:
            for res, count in valid_stats[:3]:
                thoughts.append(f"    *   {res}: {count} раз")
        
        if stats.get("Unknown"):
             thoughts.append(f"    *   *Заметки*: {stats['Unknown']} исходов не распознано.*")

    thoughts.append(f"*   **Обновлено**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    append_to_kb(thoughts)

def append_to_kb(thoughts):
    if not os.path.exists(KB_PATH):
        return
        
    with open(KB_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    section_header = "## 6. МЫСЛИ ИИ (САМООБУЧЕНИЕ)"
    new_block = "\n" + section_header + "\n" + "\n".join(thoughts) + "\n"

    if section_header in content:
        # Заменяем старую секцию на новую (или добавляем к ней)
        # Для простоты сейчас будем заменять, чтобы не раздувать файл бесконечно
        parts = content.split(section_header)
        # Сохраняем все до секции 6
        new_content = parts[0] + new_block
    else:
        new_content = content + "\n" + new_block

    with open(KB_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Knowledge base updated with AI thoughts.")

if __name__ == "__main__":
    reflect()
