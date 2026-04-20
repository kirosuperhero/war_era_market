# War Era Market Analyzer

A Streamlit-based dashboard for analyzing the in-game marketplace for the game "War Era". Tracks Jets, Tanks, and Legendary/Mythic equipment with real-time data, quality scoring, price trend prediction, and Telegram alerts.

## Tech Stack

- **Language:** Python 3.12
- **Framework:** Streamlit
- **Data:** Pandas, NumPy
- **Visualization:** Plotly Express
- **ML:** Scikit-learn (LinearRegression for price prediction)
- **HTTP:** Requests (connects to `api4.warera.io`)

## Project Structure

- `app.py` — Main dashboard entry point
- `pages/1_Sales_Analyzer.py` — Sales history analyzer
- `data/` — Local JSON storage (price history, sales cache, alerts)
- `.streamlit/config.toml` — Streamlit server config (port 5000, all hosts)
- `.streamlit/secrets.toml` — JWT token and Telegram credentials

## Running the App

```bash
streamlit run app.py
```

Runs on port 5000 at `0.0.0.0`.

## Configuration

Secrets are stored in `.streamlit/secrets.toml`:
- `YOUR_JWT` — JWT auth token for the War Era API
- `TELEGRAM_BOT_TOKEN` — Telegram bot token for alerts
- `TELEGRAM_CHAT_ID` — Telegram chat ID for alerts
