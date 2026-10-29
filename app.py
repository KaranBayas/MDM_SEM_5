import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Stock Trading Dashboard", page_icon="📈", layout="wide")

IST = ZoneInfo("Asia/Kolkata")

# A starter watchlist of NSE-listed shares. Add more symbols as needed.
WATCHLIST = {
    "Reliance Industries": "RELIANCE.NS",
    "Tata Consultancy Services": "TCS.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Tata Motors": "TMPV.NS",
    "ITC": "ITC.NS",
    "State Bank of India": "SBIN.NS",
    "Wipro": "WIPRO.NS",
    "Larsen & Toubro": "LT.NS",
}

st.title("📈 Stock Trading Dashboard")
st.caption("Free educational demo • Real market data when available • Simulated trades only")
st.warning(
    "This project does not place real orders. Prices from yfinance may be delayed, "
    "temporarily unavailable, or subject to provider limitations. Do not use this demo "
    "to make real trading decisions."
)

DB_PATH = Path(__file__).with_name("trading_history.db")

def initialize_database():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                buy_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_price REAL NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_key TEXT NOT NULL UNIQUE,
                holding_id TEXT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                note TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

def migrate_session_data():
    if st.session_state.get("_legacy_data_migrated"):
        return
    with sqlite3.connect(DB_PATH) as connection:
        migrated = connection.execute(
            "SELECT value FROM app_metadata WHERE key = 'legacy_data_migrated'"
        ).fetchone()
        if migrated:
            st.session_state._legacy_data_migrated = True
            return
        for holding in st.session_state.get("holdings", []):
            connection.execute("""
                INSERT OR IGNORE INTO holdings
                (id, symbol, quantity, buy_price, stop_loss, status, created_at, last_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                holding["id"], holding["symbol"], holding["quantity"],
                holding["buy_price"], holding["stop_loss"], holding["status"],
                holding["created_at"], holding.get("last_price", holding["buy_price"]),
            ))
        for index, trade in enumerate(st.session_state.get("trade_history", [])):
            event_key = f"legacy:{index}:" + ":".join(str(trade.get(column, "")) for column in (
                "Time", "Symbol", "Action", "Quantity", "Price (₹)", "Note"
            ))
            connection.execute("""
                INSERT OR IGNORE INTO trades
                (event_key, timestamp, symbol, action, quantity, price, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event_key, str(trade.get("Time", "")), str(trade.get("Symbol", "")),
                str(trade.get("Action", "")), int(trade.get("Quantity", 0)),
                float(trade.get("Price (₹)", 0)), str(trade.get("Note", "")),
            ))
        connection.execute(
            "INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('legacy_data_migrated', '1')"
        )
    st.session_state._legacy_data_migrated = True

def load_persistent_state():
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        holdings = [dict(row) for row in connection.execute(
            "SELECT * FROM holdings ORDER BY created_at, id"
        )]
        history = [dict(row) for row in connection.execute("""
            SELECT timestamp AS 'Time', symbol AS 'Symbol', action AS 'Action',
                   quantity AS 'Quantity', price AS 'Price (₹)', note AS 'Note'
            FROM trades ORDER BY id
        """)]
    st.session_state.holdings = holdings
    st.session_state.trade_history = history

def record_buy(holding):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("""
            INSERT INTO holdings
            (id, symbol, quantity, buy_price, stop_loss, status, created_at, last_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            holding["id"], holding["symbol"], holding["quantity"],
            holding["buy_price"], holding["stop_loss"], holding["status"],
            holding["created_at"], holding["last_price"],
        ))
        connection.execute("""
            INSERT INTO trades
            (event_key, holding_id, timestamp, symbol, action, quantity, price, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{holding['id']}:BUY", holding["id"], holding["created_at"],
            holding["symbol"], "BUY (simulated)", holding["quantity"],
            holding["buy_price"], "Paper trade only",
        ))

def persist_holding(holding):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            UPDATE holdings SET stop_loss = ?, last_price = ? WHERE id = ?
        """, (holding["stop_loss"], holding["last_price"], holding["id"]))

def record_exit(holding, action, status, price, note):
    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute("""
            UPDATE holdings SET status = ?, last_price = ?
            WHERE id = ? AND status = 'Open'
        """, (status, price, holding["id"]))
        if cursor.rowcount != 1:
            return False
        connection.execute("""
            INSERT INTO trades
            (event_key, holding_id, timestamp, symbol, action, quantity, price, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{holding['id']}:EXIT", holding["id"], timestamp,
            holding["symbol"], action, holding["quantity"], price, note,
        ))
    return True

@st.dialog("Choose Your Broker", width="small", position="center")
def choose_broker_dialog():
    with st.container(border=True):
        st.markdown("**Groww**")
        st.caption("Explore stocks and investing with Groww.")
        st.link_button("Open Groww", "https://groww.in/", width="stretch")
    with st.container(border=True):
        st.markdown("**Zerodha**")
        st.caption("Explore trading and investing with Zerodha.")
        st.link_button("Open Zerodha", "https://zerodha.com/", width="stretch")

    simulate_col, close_col = st.columns(2)
    if simulate_col.button("Simulate Buy", type="primary", width="stretch"):
        st.session_state.confirm_paper_buy = True
        st.session_state.show_broker_dialog = False
        st.rerun()
    if close_col.button("Close", width="stretch"):
        st.session_state.show_broker_dialog = False
        st.rerun()

initialize_database()
migrate_session_data()
load_persistent_state()

def fetch_intraday(symbol: str):
    """Fetch today's 1-minute candles from Yahoo Finance via yfinance."""
    try:
        df = yf.Ticker(symbol).history(period="1d", interval="1m", auto_adjust=False, prepost=False)
        if df is None or df.empty:
            return pd.DataFrame(), "No intraday data returned. The market may be closed, or data may be unavailable."
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        if df.empty:
            return pd.DataFrame(), "No valid candles were returned."
        # Convert index to India time for NSE symbols when possible.
        try:
            if df.index.tz is not None:
                df.index = df.index.tz_convert("Asia/Kolkata")
        except Exception:
            pass
        return df, None
    except Exception as exc:
        return pd.DataFrame(), f"Could not fetch data: {exc}"

def get_quote(symbol: str):
    try:
        info = yf.Ticker(symbol).fast_info
        price = info.get("lastPrice", None)
        previous = info.get("previousClose", None)
        if price is None:
            hist = yf.Ticker(symbol).history(period="5d", interval="1d")
            if not hist.empty:
                price = float(hist["Close"].dropna().iloc[-1])
        if previous is None:
            hist = yf.Ticker(symbol).history(period="5d", interval="1d")
            if len(hist) >= 2:
                previous = float(hist["Close"].dropna().iloc[-2])
        return (float(price) if price is not None else None,
                float(previous) if previous is not None else None)
    except Exception:
        return None, None

# Sidebar: symbol search and refresh controls
st.sidebar.header("Find a share")
company_names = list(WATCHLIST.keys())
selected_company = st.sidebar.selectbox("Choose a company", company_names)
custom_symbol = st.sidebar.text_input("Or enter an NSE symbol", placeholder="e.g. TCS")
symbol = custom_symbol.strip().upper() if custom_symbol.strip() else WATCHLIST[selected_company]
if "." not in symbol and not custom_symbol.strip():
    symbol += ".NS"

interval_label = st.sidebar.radio("Chart interval", ["1 minute", "5 minutes"], index=0)
refresh_seconds = st.sidebar.selectbox("Auto-refresh", [0, 15, 30, 60, 120], index=4,
                                      format_func=lambda x: "Off" if x == 0 else f"Every {x} seconds")
if st.sidebar.button("Refresh now", use_container_width=True):
    st.rerun()

# Main navigation
dashboard_tab, details_tab, holdings_tab = st.tabs(["Market dashboard", "Selected share", "My shares"])

with dashboard_tab:
    st.subheader("Watchlist")
    rows = []
    for company, ticker in WATCHLIST.items():
        price, previous = get_quote(ticker)
        change = price - previous if price is not None and previous is not None else None
        change_pct = (change / previous * 100) if change is not None and previous else None
        rows.append({
            "Company": company,
            "Symbol": ticker,
            "Latest available price (₹)": round(price, 2) if price is not None else "Unavailable",
            "Change (₹)": round(change, 2) if change is not None else "—",
            "Change (%)": f"{change_pct:+.2f}%" if change_pct is not None else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Prices are retrieved from Yahoo Finance through yfinance; they are not guaranteed to be real-time.")

with details_tab:
    st.subheader(f"{symbol} — intraday candlestick chart")
    interval = "1m" if interval_label == "1 minute" else "5m"
    data, error = fetch_intraday(symbol)

    price, previous = get_quote(symbol)
    if price is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("Latest available price", f"₹{price:,.2f}",
                  delta=f"{(price-previous):+.2f}" if previous is not None else None)
        c2.metric("Symbol", symbol)
        c3.metric("Chart interval", interval_label)

    if not data.empty:
        if interval == "5m":
            # Resample 1-minute data into 5-minute OHLC candles.
            data = data.resample("5min").agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            }).dropna(subset=["Open", "High", "Low", "Close"])

        fig = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            increasing_line_color="#75c943",
            decreasing_line_color="#ff453a",
            increasing_fillcolor="#75c943",
            decreasing_fillcolor="#ff453a",
            name=symbol
        )])
        fig.update_layout(
            height=520,
            template="plotly_dark",
            paper_bgcolor="#08283c",
            plot_bgcolor="#08283c",
            xaxis_title="Time (IST)",
            yaxis_title="Price (₹)",
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(160,190,210,0.15)")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(160,190,210,0.15)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Showing {len(data)} available candles. The feed may not update outside market hours.")
    else:
        st.info(error or "Intraday data is currently unavailable.")
        st.write("Check your internet connection, try another symbol, or refresh during NSE market hours.")

    st.divider()
    st.subheader("Simulate a buy")
    buy_col1, buy_col2, buy_col3 = st.columns(3)
    with buy_col1:
        quantity = st.number_input("Quantity", min_value=1, max_value=100000, value=1, step=1, key="buy_qty")
    with buy_col2:
        fallback_price = float(price) if price is not None else 0.0
        buy_price = st.number_input("Buy price (₹)", min_value=0.0, value=fallback_price, step=0.05, format="%.2f")
    with buy_col3:
        stop_loss = st.number_input("Stop-loss price (₹)", min_value=0.0,
                                    value=round(max(0.0, buy_price * 0.98), 2), step=0.05, format="%.2f")
    if st.button("Buy (simulate)", type="primary", use_container_width=True):
        st.session_state.show_broker_dialog = True

    if st.session_state.get("show_broker_dialog", False):
        choose_broker_dialog()

    if st.session_state.pop("confirm_paper_buy", False):
        if buy_price <= 0:
            st.error("A valid price is needed. Wait for a price or enter one manually for a demo.")
        elif stop_loss <= 0 or stop_loss >= buy_price:
            st.error("For this long-position demo, stop-loss must be greater than ₹0 and below the buy price.")
        else:
            holding = {
                "id": f"{symbol}-{datetime.now(IST).strftime('%Y%m%d%H%M%S%f')}",
                "symbol": symbol,
                "quantity": int(quantity),
                "buy_price": float(buy_price),
                "stop_loss": float(stop_loss),
                "status": "Open",
                "created_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                "last_price": float(price) if price is not None else float(buy_price),
            }
            record_buy(holding)
            load_persistent_state()
            st.success(f"Simulated purchase recorded: {quantity} share(s) of {symbol}. See My shares.")
            st.info("Stop-loss is checked when you refresh this app. Keep it open and refresh regularly for this demo.")

with holdings_tab:
    st.subheader("My shares (paper trading)")
    if not st.session_state.holdings:
        st.info("You haven't simulated buying any shares yet. Select a share and use Buy (simulate).")
    else:
        for holding in st.session_state.holdings:
            if holding["status"] != "Open":
                continue
            current, _ = get_quote(holding["symbol"])
            if current is not None:
                holding["last_price"] = current
            current = float(holding.get("last_price", holding["buy_price"]))
            # Simulated stop-loss: this runs when the page is rerun/refreshed.
            if current <= holding["stop_loss"]:
                if record_exit(
                    holding, "STOP-LOSS SELL (simulated)",
                    "Stop-loss triggered (simulated)", current,
                    "Triggered by latest available price on refresh",
                ):
                    holding["status"] = "Stop-loss triggered (simulated)"
                    load_persistent_state()
            else:
                persist_holding(holding)
            pnl = (current - holding["buy_price"]) * holding["quantity"]
            with st.container(border=True):
                a, b, c, d = st.columns(4)
                a.markdown(f"**{holding['symbol']}**")
                a.caption(f"Quantity: {holding['quantity']}")
                b.metric("Buy price", f"₹{holding['buy_price']:,.2f}")
                c.metric("Latest available price", f"₹{current:,.2f}", delta=f"{pnl:+,.2f} ₹ P/L")
                d.metric("Stop-loss", f"₹{holding['stop_loss']:,.2f}")
                st.write(f"Status: **{holding['status']}**")
                if holding["status"] == "Open":
                    new_sl = st.number_input(
                        f"Change stop-loss for {holding['symbol']}",
                        min_value=0.01, max_value=max(0.02, holding["buy_price"] - 0.01),
                        value=float(holding["stop_loss"]), step=0.05,
                        key=f"sl_{holding['id']}"
                    )
                    x, y = st.columns(2)
                    if x.button("Update stop-loss", key=f"upd_{holding['id']}"):
                        if new_sl >= holding["buy_price"]:
                            st.error("Stop-loss must be below the buy price in this demo.")
                        else:
                            holding["stop_loss"] = float(new_sl)
                            persist_holding(holding)
                            st.success("Stop-loss updated.")
                            st.rerun()
                    if y.button("Sell now (simulate)", key=f"sell_{holding['id']}"):
                        if record_exit(
                            holding, "SELL (simulated)",
                            "Sold manually (simulated)", current,
                            "Manual paper-trade exit",
                        ):
                            st.success("Simulated sale recorded.")
                        else:
                            st.warning("This holding has already been closed.")
                        load_persistent_state()
                        st.rerun()
                elif holding["status"].startswith("Stop-loss triggered"):
                    st.warning("The stop-loss condition was detected. This was a simulated sale, not a real broker order.")

    st.divider()
    st.subheader("Trade history")
    if st.session_state.trade_history:
        st.dataframe(pd.DataFrame(st.session_state.trade_history), use_container_width=True, hide_index=True)
    else:
        st.caption("Your simulated buy/sell activity will appear here.")

if refresh_seconds > 0:
    st.sidebar.caption(f"Page refreshes every {refresh_seconds} seconds.")
    st.markdown(
        f'<meta http-equiv="refresh" content="{refresh_seconds}">',
        unsafe_allow_html=True
    )
