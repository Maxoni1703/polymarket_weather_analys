
# 🌤️ Polymarket Weather Analyzer

A professional, high-performance tool for analyzing and gaining an edge in weather-based prediction markets on **Polymarket** (specifically targeting Max Temperature markets for London and Miami).

By blending multi-model weather forecasts (Open-Meteo), live METAR station observations, and AI-driven insights, this application calculates mathematical probabilities and provides actionable betting advice to help you beat the public consensus.

---

## 🚀 Key Features

*   **Deep Data Aggregation**: Seamlessly combines historical, current, and forecasted data from Open-Meteo, METAR aviation weather stations, and `wttr.in`.
*   **AI-Powered Analysis**: Integrated with GenAPI to leverage cutting-edge AI models (Gemini, Claude, GPT). The AI analyzes temperature trends, frontal movements, and historical station biases to provide an edge.
*   **One-Click Verdicts**: Special "AI Verdict" buttons generate instantaneous mathematical probabilities, suggested stake sizes, and final YES/NO betting advice based on current Polymarket odds.
*   **Live Odds Tracking**: Automatically pulls the latest order book prices from Polymarket to calculate your expected value (EV) and Kelly criterion stake sizing.
*   **Modern Web Dashboard**: A sleek, locally-hosted web interface featuring a dark mode, glass-morphism aesthetic, and responsive design—built entirely with Vanilla JS, HTML5, and CSS3 (no bulky frameworks).

---

## 🛠️ Technology Stack

*   **Backend**: Python 3, FastAPI, Uvicorn (High-performance async server)
*   **Frontend**: HTML5, CSS3, Vanilla JavaScript
*   **AI Integration**: GenAPI
*   **Weather APIs**: Open-Meteo, METAR, wttr.in

---

## ⚙️ Getting Started

Follow these instructions to get the application running on your local machine.

### Prerequisites
* Python 3.8+ installed
* An API key from [GenAPI](https://gen-api.ru/) (for AI analysis)

### Installation

1. **Clone the repository** (or navigate to the project directory):
   ```bash
   cd "polymarket app"
   ```

2. **Create a virtual environment (Optional but recommended)**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   # source venv/bin/activate
   ```

3. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the application**:
   ```bash
   python main.py
   ```
   *The server will start on `http://127.0.0.1:8000` and should automatically open in your default web browser.*

---

## 🔧 Configuration & AI Setup

To get the most out of the AI predictions, you need to configure your GenAPI API key:

1. Open the web dashboard at `http://localhost:8000`.
2. Click on the **AI Settings** gear icon in the top navigation panel.
3. Paste your **GenAPI API Key**.
4. Select your preferred AI model (e.g. Gemini 3.1 Flash Lite). 
5. Save the settings.

---

## 📊 How It Works

1. **City Selection**: Choose either **London (Heathrow - EGLL)** or **Miami (KMIA)**.
2. **Data Fetching**: The backend fetches real-time METAR observations, Open-Meteo forecasts, and live Polymarket odds.
3. **Probability Calculation**: The app checks the current max temperature against the Polymarket target brackets.
4. **AI Verdict**: Click the AI Verdict button to send the compiled weather data to the LLM. The AI evaluates the time of day (e.g., peak heating hours 14:00-16:00), cloud cover, historical biases of the specific weather stations, and current market odds to give a final percentage chance.

---

## 📁 Project Structure

*   `main.py`: Entry point that launches the local Uvicorn server and opens the browser.
*   `server.py`: FastAPI server containing the REST endpoints.
*   `config.py`: Configuration file for UI colors, fonts, and city-specific weather logic (coordinates, METAR stations, peak hours).
*   `polymarket.py`: Logic for interacting with the Polymarket API/data.
*   `weather.py`: Functions for fetching and parsing METAR, wttr.in, and Open-Meteo data.
*   `ai_chat.py`: Handles communication with the GenAPI.
*   `models.py`: Data classes and Pydantic models.
*   `static/`: Contains all the frontend assets (HTML, CSS, JS).

---

