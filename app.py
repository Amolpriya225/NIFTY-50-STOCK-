import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="NIFTY 50 PRO", layout="wide")
st.title("📈 NIFTY 50 PRO DASHBOARD - TradingView Style")

# Auto Refresh har 15 sec me
st_autorefresh = st.empty()
if 'count' not in st.session_state:
    st.session_state.count = 0

# 1. Sare Index aur Stocks
indices = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "FIN NIFTY": "^CNXFIN",
    "MIDCAP NIFTY": "^NSEMDCP50"
}

stocks = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS",
    "HDFC BANK": "HDFCBANK.NS", "ICICI BANK": "ICICIBANK.NS", "SBIN": "SBIN.NS"
}

col1, col2, col3 = st.columns(3)
with col1:
    selected_index = st.selectbox("Index Chuno", list(indices.keys()))
    ticker = indices[selected_index]
with col2:
    selected_stock = st.selectbox("Ya Stock Chuno (Optional)", ["-- Index Dekho --"] + list(stocks.keys()))
    if selected_stock!= "-- Index Dekho --":
        ticker = stocks[selected_stock]
with col3:
    timeframe = st.selectbox("Time Frame", ["5m", "15m", "1h", "1d"], index=1)

period_map = {"5m": "1d", "15m": "5d", "1h": "1mo", "1d": "6mo"}

@st.cache_data(ttl=15)
def get_data(tick, period, interval):
    df = yf.download(tick, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

data = get_data(ticker, period_map[timeframe], timeframe)

if data.empty:
    st.error("Market band hai ya data nahi mil raha. 9:15 ke baad try karo.")
    st.stop()

# Latest OHLC
close = float(data['Close'].iloc[-1])
open_p = float(data['Open'].iloc[-1])
high = float(data['High'].iloc[-1])
low = float(data['Low'].iloc[-1])

# 2. Live Price Movement wala header
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"{ticker} LIVE", f"₹ {close:.2f}", f"{close-open_p:.2f}")
c2.metric("OPEN", f"₹ {open_p:.2f}")
c3.metric("HIGH", f"₹ {high:.2f}")
c4.metric("LOW", f"₹ {low:.2f}")

# 3. & 4. TradingView jaisa Candle Chart with OHLC
fig = go.Figure(data=[go.Candlestick(
    x=data.index, open=data['Open'], high=data['High'],
    low=data['Low'], close=data['Close'], name="Candle"
)])
fig.update_layout(
    height=500, xaxis_rangeslider_visible=False,
    title=f"{ticker} - {timeframe} Chart",
    yaxis_title="Price",
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

# 5. Buy/Sell Recommendation Logic
st.divider()
st.subheader("🤖 Auto Recommendation (Entry / Stoploss / Target)")

data['SMA20'] = data['Close'].rolling(20).mean()
data['SMA50'] = data['Close'].rolling(50).mean()

# RSI simple
delta = data['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
data['RSI'] = 100 - (100 / (1 + rs))

last_rsi = float(data['RSI'].iloc[-1])
sma20 = float(data['SMA20'].iloc[-1])
sma50 = float(data['SMA50'].iloc[-1])

entry = close
if sma20 > sma50 and last_rsi < 70:
    signal = "🟢 BUY"
    stoploss = close * 0.99 # 1% SL
    target = close * 1.02 # 2% Target
elif sma20 < sma50 and last_rsi > 30:
    signal = "🔴 SELL"
    stoploss = close * 1.01
    target = close * 0.98
else:
    signal = "🟡 HOLD / WAIT"
    stoploss = close * 0.995
    target = close * 1.005

rc1, rc2, rc3, rc4 = st.columns(4)
rc1.metric("Signal", signal)
rc2.metric("Entry Price", f"₹ {entry:.2f}")
rc3.metric("Stoploss", f"₹ {stoploss:.2f}")
rc4.metric("Target", f"₹ {target:.2f}")

st.info(f"Time: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} | RSI: {last_rsi:.2f} | Logic: SMA20 vs SMA50 crossover. Ye educational purpose ke liye hai.")

st.caption("Page har 15 sec me khud refresh hoga.")
st.rerun if st.button("🔄 Abhi Refresh Karo") else None
