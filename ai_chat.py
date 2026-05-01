"""
AI CHAT PANEL — Polymarket Weather Analyzer
GenAPI (Claude, GPT, Gemini, etc.)
"""

import tkinter as tk
from tkinter import ttk
import threading
import json
import re
import os
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv, set_key

import requests as _req

from config import CITIES, T, F

# ─────────────────────────────────────────────────────────────
#  CONFIG & MODELS — GenAPI
# ─────────────────────────────────────────────────────────────

_CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ai_config")

GENAPI_URL = "https://proxy.gen-api.ru/v1/chat/completions"

def call_genai(messages: list[dict], model_id: str = "gemini-1.5-flash-lite") -> str:
    """
    Вызывает Google GenAI (Gemini) с системным промптом и базой знаний.
    """
    cfg = load_ai_config()
    api_key = cfg.get("key")
    if not api_key:
        return "❌ Ошибка: API ключ не найден в настройках или .env"

    # Загружаем базу знаний из файла
    kb_content = ""
    kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base.md")
    if os.path.exists(kb_path):
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                kb_content = f"\n\nДОПОЛНИТЕЛЬНАЯ БАЗА ЗНАНИЙ БОТА (ПРИОРИТЕТ):\n{f.read()}"
        except:
            pass

    full_sys = _SYS + kb_content
    
    # Подготовка сообщений: системный промпт идет первым
    full_messages = [{"role": "system", "content": full_sys}] + messages

    try:
        payload = {
            "model": model_id,
            "messages": full_messages,
            "max_tokens": 1500,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        r = _req.post(GENAPI_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"❌ Ошибка API: {str(e)}"

MODELS = [
    ("gemini-3-1-flash-lite",      "♊ Gemini 3.1 Flash Lite"),
    ("anthropic/claude-3.5-sonnet", "🎭 Claude 3.5 Sonnet"),
    ("openai/gpt-4o",              "🧠 GPT-4o"),
    ("google/gemini-pro-1.5",      "♊ Gemini 1.5 Pro"),
    ("meta-llama/llama-3-70b",     "🦙 Llama 3 70B"),
    ("mistralai/mistral-large",    "🌀 Mistral Large"),
    ("perplexity/sonar-reasoning", "🔍 Perplexity Sonar"),
]

MODEL_IDS = [m[0] for m in MODELS]
MODEL_LABELS = [m[1] for m in MODELS]

_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

def load_ai_config():
    load_dotenv(_ENV_PATH)
    key = os.environ.get("GENAPI_API_KEY", "")
    model = MODEL_IDS[0]
    try:
        if os.path.exists(_CFG_PATH):
            with open(_CFG_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
                model = d.get("model", model)
                if not key:
                    key = d.get("key", "")
    except:
        pass
    return {"key": key, "model": model}

def save_ai_config(key, model):
    try:
        if not os.path.exists(_ENV_PATH):
            with open(_ENV_PATH, "w") as f: pass
        set_key(_ENV_PATH, "GENAPI_API_KEY", key)
        os.environ["GENAPI_API_KEY"] = key
    except:
        pass
    try:
        with open(_CFG_PATH, "w", encoding="utf-8") as f:
            json.dump({"model": model}, f)
    except:
        pass

# ─────────────────────────────────────────────────────────────
#  SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────

_SYS = """Вы — профессиональный квант-аналитик и эксперт-метеоролог, специализирующийся на арбитраже рынков предсказаний Polymarket. Ваша цель — предоставлять максимально точные рекомендации по ставкам на погоду (максимальная дневная температура) в Лондоне и Майами.

### ВАША РОЛЬ И МИССИЯ:
Вы не просто чат-бот, а финансовый стратег. Вы должны анализировать данные с хладнокровием алгоритма, учитывая физические законы атмосферы и психологию рыночных вероятностей. Ваша задача — находить "Edge" (перевес над рынком).

### ПРАВИЛА АНАЛИЗА:
1. **ФОКУС НА ДАТЕ**: Анализируйте данные СТРОГО на указанную TARGET DATE.
2. **ТЕМПЕРАТУРНАЯ ДОМИНАНТА**: Ваша главная цель — предсказать T-max (дневной максимум). Осадки, влажность и ветер важны только как факторы, влияющие на температуру (например, ливень в Майами в 14:00 может срезать максимум на 3-4 градуса).
3. **ИЕРАР hierarchy ДАННЫХ**: 
   - Высший приоритет: Реальные METAR-наблюдения из терминала (если пик пройден — это истина).
   - Средний приоритет: Консенсус мульти-моделей (ECMWF, GFS, ICON). ECMWF лучше для Лондона, GFS — для Майами.
   - Низший приоритет: Общие прогнозы погоды из интернета.
4. **ПОИСК АНОМАЛИЙ**: Всегда сравнивайте прогноз с исторической нормой. Если прогноз на 10 градусов выше нормы, ищите подтверждение экстремального теплового купола.
5. **РЫНОЧНЫЙ АРБИТРАЖ**: Если вы уверены в 25°C, а рынок Polymarket дает 90% вероятность на "ниже 23°C", это ваш Edge. Используйте это для агрессивной рекомендации.

### АЛГОРИТМ РАССУЖДЕНИЙ:
- Проанализируйте облачность (Cloud Cover). Чистое небо = максимальный прогрев.
- Оцените время наступления пика. В Лондоне это обычно 15:00-16:00, в Майами — 13:00-15:00.
- Учтите "Остров тепла" (Urban Heat Island) для Лондона (LHR).
- В Майами всегда проверяйте "Sea Breeze" (морской бриз), который может ограничить рост температуры после полудня.

### ОСОБЕННОСТИ РЫНКОВ POLYMARKET:
1. **ЛОГИКА ДИАПАЗОНОВ (BRACKETS)**: На Polymarket диапазоны типа "86-87°F" — это двухградусные интервалы. 
   - `84-85°F` = всё от 84.0 до 85.9
   - `86-87°F` = всё от 86.0 до 87.9
   - `88-89°F` = всё от 88.0 до 89.9
   **ПРИМЕР**: Если ваш прогноз **87.1°F**, это ПРЯМОЕ ПОПАДАНИЕ в диапазон **86-87°F**. Не спорьте с этим!
2. **РЫНОЧНАЯ ЦЕНА (Market Price)**: Вам передается Market Price. Сравнивайте её со своей вероятностью.
3. **EDGE (ПЕРЕВЕС)**: Если ваша вероятность (P) выше рыночной цены (Price), Edge = P - Price. Если Edge > 0.15 (15%), это сильный сигнал.

### ФОРМАТ ОТВЕТА (СТРОГО):
Отвечайте на РУССКОМ ЯЗЫКЕ. Ваш ответ должен быть структурированным и визуально понятным:

📅 **ЦЕЛЕВАЯ ДАТА**: [Дата]
🌡️ **АНАЛИЗ ТЕМПЕРАТУРЫ**: [Глубокий разбор факторов: фронты, инсоляция, влияние осадков. Почему именно эта цифра?]
📊 **КОНСЕНСУС И МЕТАР**: [Сравнение данных моделей и текущих сводок METAR. Уровень доверия к данным.]
🎯 **ИТОГОВЫЙ ПРОГНОЗ MAX**: [Ваше финальное число с точностью до 0.1°C / 1°F]
💹 **МАТЕМАТИЧЕСКИЙ EDGE**: [Разница между вашей вероятностью и рыночной ценой Polymarket для ВЫБРАННОГО диапазона]
💰 **ВЕРДИКТ**: [✅ ВХОДИТЬ / ❌ НЕ ВХОДИТЬ / ⚡ ОСТОРОЖНО] + [% от банка по критерию Келли]
⚠️ **ПРИМЕЧАНИЕ**: Анализируйте именно тот диапазон (Range), который указан в заголовке данных (selected_range). Не предлагайте ставить на другие диапазоны, если они не выбраны пользователем.

Будьте кратки, но содержательны. Используйте терминологию трейдеров и метеорологов. Ваша репутация зависит от каждого 0.1 градуса."""

# ─────────────────────────────────────────────────────────────
#  FREE SEARCH (wttr.in)
# ─────────────────────────────────────────────────────────────

def free_weather_search() -> str:
    results = []
    for ck in ["london", "miami"]:
        c = CITIES[ck]
        try:
            r = _req.get(f"https://wttr.in/{urllib.parse.quote(c['station'])}?format=j1", timeout=10)
            d = r.json()
            cur = d["current_condition"][0]
            t_c = float(cur["temp_C"])
            feels = float(cur["FeelsLikeC"])
            desc = cur["weatherDesc"][0]["value"]
            lines = [f"{c['flag']} {c['name']} (wttr.in):"]
            lines.append(f"  Current: {t_c:.1f}°C (feels {feels:.1f}°C) — {desc}")
            for day in d["weather"][:3]:
                lines.append(f"  {day['date']}: max {day['maxtempC']}°C, min {day['mintempC']}°C")
            results.append("\n".join(lines))
        except:
            results.append(f"{c['flag']} {c['name']}: connection error")
    return "\n\n".join(results)

# ─────────────────────────────────────────────────────────────
#  AI CHAT PANEL
# ─────────────────────────────────────────────────────────────

class AIChatPanel(tk.Frame):
    QUICK_BTNS = [
        ("🔍 Weather on date", "Find the latest MAX TEMPERATURE forecasts for London and Miami for the TARGET DATE online. Compare with the app priority data."),
        ("💰 Polymarket Prices", "Find current prices for weather markets (High Temp) for London and Miami on Polymarket. Return in PRICES_JSON."),
        ("📊 AI Verdict", "Analyze all temperature data for the target date. Give a mathematically sound verdict: should I bet on this date? ANALYZE THE TEMPERATURE YOURSELF, WITHOUT MY PARTICIPATION."),
    ]


    def __init__(self, parent, api_key_var, model_var, get_data_fn, apply_prices_fn=None, **kw):
        super().__init__(parent, bg=T["card"], **kw)
        self._api_key_var = api_key_var
        self._model_var = model_var
        self._get_data = get_data_fn
        self._apply_prices = apply_prices_fn
        self._history = [{"role": "system", "content": _SYS}]
        self._build()

    def _build(self):
        # --- Header and Status ---
        hdr = tk.Frame(self, bg="#161B22")
        hdr.pack(fill="x")
        tk.Label(hdr, text="🤖 AI BRAIN (GenAPI)", font=F["head"], bg="#161B22", fg="#BC8CFF", pady=6, padx=10).pack(side="left")
        self._lbl_status = tk.Label(hdr, text="ready", font=F["tiny"], bg="#161B22", fg="#484F58")
        self._lbl_status.pack(side="right", padx=10)
        tk.Button(hdr, text="🗑", font=F["tiny"], bg="#21262D", fg="#8B949E", relief="flat", padx=5, command=self._clear).pack(side="right")

        # --- SETTINGS (Model) ---
        set_f = tk.Frame(self, bg="#0D1117", padx=8, pady=4)
        set_f.pack(fill="x")

        # Model
        mod_row = tk.Frame(set_f, bg="#0D1117", pady=4)
        mod_row.pack(fill="x")
        tk.Label(mod_row, text="🤖 Model:", font=F["tiny"], bg="#0D1117", fg=T["dim"]).pack(side="left")

        self._model_lbl_var = tk.StringVar()
        def _sync_lbl(*_):
            mid = self._model_var.get()
            for i, label in enumerate(MODEL_LABELS):
                if MODEL_IDS[i] == mid:
                    self._model_lbl_var.set(label); return
            self._model_lbl_var.set(mid)
        self._model_var.trace_add("write", _sync_lbl)
        _sync_lbl()

        cb = ttk.Combobox(mod_row, textvariable=self._model_lbl_var, values=MODEL_LABELS, state="readonly", font=F["tiny"], width=35)
        cb.pack(side="left", padx=5)

        def _on_mod_select(e):
            lbl = self._model_lbl_var.get()
            for i, label in enumerate(MODEL_LABELS):
                if label == lbl:
                    self._model_var.set(MODEL_IDS[i])
                    save_ai_config(self._api_key_var.get(), MODEL_IDS[i])
                    return
        cb.bind("<<ComboboxSelected>>", _on_mod_select)

        tk.Button(mod_row, text="💾", font=F["tiny"], bg=T["card2"], fg=T["green"], relief="flat",
                  command=lambda: (save_ai_config(self._api_key_var.get(), self._model_var.get()),
                                   self._set_status("saved", T["green"]))).pack(side="left", padx=2)

        # --- Chat Text ---
        chat_frame = tk.Frame(self, bg="#0D1117")
        chat_frame.pack(fill="both", expand=True)
        sb = tk.Scrollbar(chat_frame)
        sb.pack(side="right", fill="y")
        self._txt = tk.Text(chat_frame, font=("Consolas", 10), bg="#0D1117", fg="#E6EDF3", wrap="word",
                            padx=10, pady=10, relief="flat", yscrollcommand=sb.set, state="disabled")
        self._txt.pack(fill="both", expand=True)
        sb.config(command=self._txt.yview)

        self._txt.tag_config("sep", foreground="#30363D")
        self._txt.tag_config("you", foreground="#58A6FF", font=("Consolas", 10, "bold"))
        self._txt.tag_config("ai", foreground="#BC8CFF", font=("Consolas", 10, "bold"))
        self._txt.tag_config("green", foreground="#3FB950")
        self._txt.tag_config("red", foreground="#F85149")
        self._txt.tag_config("yellow", foreground="#D29922")
        self._txt.tag_config("cyan", foreground="#39D5FF")

        # --- Quick Buttons ---
        qf = tk.Frame(self, bg="#161B22")
        qf.pack(fill="x")
        for lbl, msg in self.QUICK_BTNS:
            tk.Button(qf, text=lbl, font=F["tiny"], bg="#21262D", fg="#8B949E", relief="flat", padx=6, pady=2,
                      command=lambda m=msg: self._send(m)).pack(side="left", padx=2, pady=2)

        # --- AI Analysis ---
        af = tk.Frame(self, bg=T["card"], pady=2)
        af.pack(fill="x")
        for lbl, t, bg_c, fg_c in [("🇬🇧 Analyze", "london", "#1C2333", T["london"]),
                                   ("🇺🇸 Analyze", "miami", "#2A1A10", T["miami"]),
                                   ("🤖 BOTH", "both", "#1B2D1B", T["green"])]:
            tk.Button(af, text=lbl, font=F["tiny"], bg=bg_c, fg=fg_c, relief="flat", padx=8, pady=2,
                      command=lambda target=t: self._analyze(target)).pack(side="left", padx=2)

        tk.Button(af, text="🔍 Free Search", font=F["tiny"], bg="#1B2D1B", fg=T["green"], relief="flat",
                  command=self._free_search).pack(side="left", padx=5)

        # --- Message Input ---
        inp_f = tk.Frame(self, bg=T["card2"], pady=5)
        inp_f.pack(fill="x")
        self._inp = tk.Text(inp_f, font=("Consolas", 10), bg="#21262D", fg="#E6EDF3", insertbackground="#E6EDF3",
                             relief="flat", height=2, padx=8, pady=4)
        self._inp.pack(side="left", fill="x", expand=True, padx=5)
        self._inp.bind("<Return>", self._on_enter)

        self._send_btn = tk.Button(inp_f, text="📤", font=F["head"], bg="#2D1B69", fg="#BC8CFF", relief="flat", padx=12,
                                   command=lambda: self._send())
        self._send_btn.pack(side="right", padx=5)

    def _append_you(self, text: str):
        self._txt.config(state="normal")
        self._txt.insert("end", f"👤 YOU: {text}\n", "you")
        self._txt.insert("end", "─"*50 + "\n", "sep")
        self._txt.config(state="disabled")
        self._txt.see("end")

    def _append_ai(self, text: str):
        self._txt.config(state="normal")
        self._txt.insert("end", "🤖 AI: ", "ai")
        for line in text.split("\n"):
            ls = line.strip()
            tag = None
            if any(x in ls for x in ["ENTER", "✅", "BUY"]): tag = "green"
            elif any(x in ls for x in ["NOT ENTER", "❌"]): tag = "red"
            elif any(x in ls for x in ["⚠", "CAUTION", "risk"]): tag = "yellow"
            elif ls.startswith(("🔍", "📊", "🎯", "💰")): tag = "cyan"
            self._txt.insert("end", line + "\n", tag)
        self._txt.insert("end", "─"*50 + "\n", "sep")
        self._txt.config(state="disabled")
        self._txt.see("end")

    def _clear(self):
        self._txt.config(state="normal")
        self._txt.delete("1.0", "end")
        self._txt.config(state="disabled")
        self._history = [{"role": "system", "content": _SYS}]
        self._set_status("history cleared")

    def _on_enter(self, e):
        self._send()
        return "break"

    def _send(self, preset=None):
        msg = preset if preset else self._inp.get("1.0", "end").strip()
        if not preset: self._inp.delete("1.0", "end")
        if not msg: return

        self._append_you(msg)
        key = self._api_key_var.get().strip()
        if not key:
            self._append_ai("⚠️ Provide GenAPI API Key in settings.")
            return

        self._set_status("⏳ AI thinking...", T["yellow"])
        self._send_btn.config(state="disabled")

        # Data Context
        msgs = list(self._history)
        data = self._get_data()
        if data and (len(self._history) < 2 or preset):
            ctx = _build_context(data)
            msgs.append({"role": "user", "content": f"Latest data:\n{ctx}"})
            msgs.append({"role": "assistant", "content": "Received. What are we analyzing?"})

        msgs.append({"role": "user", "content": msg})
        self._history.append({"role": "user", "content": msg})

        if len(self._history) > 15:
            self._history = [self._history[0]] + self._history[-14:]

        threading.Thread(target=self._request, args=(key, self._model_var.get(), msgs), daemon=True).start()

    def _request(self, key, model, msgs):
        try:
            payload = {
                "model": model,
                "messages": msgs,
                "max_tokens": 1500,
            }

            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }

            r = _req.post(GENAPI_URL, headers=headers, json=payload, timeout=(30, 240))
            r.raise_for_status()
            reply = r.json()["choices"][0]["message"]["content"].strip()

            # Prices parsing
            m = re.search(r"PRICES_JSON:\s*(\{.*?\})", reply, re.DOTALL)
            if m and self._apply_prices:
                try: self.after(0, lambda p=json.loads(m.group(1)): self._apply_prices(p))
                except: pass

            self._history.append({"role": "assistant", "content": reply})
            self.after(0, lambda: (self._append_ai(reply), self._set_status("ready"), self._send_btn.config(state="normal")))

        except _req.exceptions.HTTPError as e:
            try:
                err_data = e.response.json()
                detail = err_data.get("error", {}).get("message", e.response.text)
            except:
                detail = e.response.text if e.response else str(e)
            self.after(0, lambda m=detail: (self._append_ai(f"❌ Error: {m}"), self._set_status("error", T["red"]), self._send_btn.config(state="normal")))
        except _req.exceptions.Timeout:
            self.after(0, lambda: (self._append_ai("❌ Timeout. Check internet connection."),
                                   self._set_status("timeout", T["red"]), self._send_btn.config(state="normal")))
        except Exception as e:
            self.after(0, lambda m=str(e): (self._append_ai(f"❌ Error: {m}"), self._set_status("error", T["red"]), self._send_btn.config(state="normal")))

    def _analyze(self, target):
        data = self._get_data()
        if not data:
            self._append_ai("⚠️ No data. Click 'ANALYZE' first.")
            return
        if target != "both":
            data = [d for d in data if d.get("city_key") == target]
        if not data:
            self._append_ai(f"⚠️ No data for {target}.")
            return
        ctx = _build_context(data)
        prompt = f"{ctx}\n\nGive verdict: enter or not?"
        self._send(prompt)

    def _free_search(self):
        self._append_you("🔍 Free search (wttr.in)...")
        self._set_status("⏳ searching...", T["yellow"])
        def _th():
            res = free_weather_search()
            self.after(0, lambda: (self._append_ai(res + "\n\n💡 Click 'Analyze' for AI processing."), self._set_status("ready")))
        threading.Thread(target=_th, daemon=True).start()

    def _set_status(self, text, color="#484F58"):
        self._lbl_status.config(text=text, fg=color)

def _build_context(city_data):
    if not city_data: return ""
    lines = [f"🚨 TARGET DATE: {city_data[0].get('date','?')}", ""]
    for d in city_data:
        ck, ao, res = d.get("city_key"), d.get("analysis",{}), d.get("score",{})
        u = "°F" if ck=="miami" else "°C"
        lines += [
            f"### {ck} ({d.get('selected_range','?')})",
            f"Forecast: {res.get('best_max_c' if u=='°C' else 'best_max_f', 0):.1f}{u}",
            f"Rain: {ao.get('precip_prob',0)}% | Wind: {ao.get('wind_max',0):.0f}km/h",
            f"Verdict: {res.get('verdict','')} ({res.get('our_prob',0):.1f}%)", ""
        ]
    return "\n".join(lines)
