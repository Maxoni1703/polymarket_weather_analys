#!/usr/bin/env python3
"""
POLYMARKET WEATHER ANALYZER v6.0 (WEB APP)
- Open-Meteo: прогноз 
- METAR/wttr.in: реальные наблюдения
- AI: интеллектуальный анализ температуры
"""

import threading
import webbrowser
import time
import os
import sys
import subprocess

def open_browser():
    # Wait a few seconds for the Django server to start
    time.sleep(3)
    webbrowser.open("http://127.0.0.1:8005")

if __name__ == "__main__":
    # Start browser in background
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("Starting Django local web server... (Press Ctrl+C to quit)")
    subprocess.run([sys.executable, "manage.py", "runserver", "127.0.0.1:8005"])
