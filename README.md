# Stock Trading Dashboard (₹0 college demo)

A Streamlit educational demo with:
- NSE watchlist and search-by-symbol
- Available quote information from Yahoo Finance via `yfinance`
- Intraday candlestick chart (1-minute data, optionally resampled to 5-minute candles)
- Simulated buy and sell orders
- Simulated stop-loss and holdings view

## Important limitations
- This app does **not** place real orders.
- Yahoo Finance data is not guaranteed to be real-time, complete, or continuously available.
- Stop-loss checks run when the Streamlit app reruns/refreshes. This is not a reliable live trading system.
- Use only for an educational demonstration, not investment decisions.

## Run on macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL shown in the terminal, usually `http://localhost:8501`.

## Use
1. Pick a company from the sidebar or enter an NSE Yahoo Finance symbol such as `TCS.NS`.
2. Open **Selected share** to view the available intraday candlestick data.
3. Enter quantity, buy price, and a stop-loss below the buy price.
4. Click **Buy (simulate)**.
5. Open **My shares** to see holdings, change stop-loss, or simulate a manual sale.

## Free-data note
Yahoo Finance/yfinance is an unofficial data route and may throttle requests, return delayed data, or omit intraday candles. When the market is closed, today's intraday chart may show the latest available candles or no data.
