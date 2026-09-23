import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="NIFTY 50 PRO", layout="wide")
st.title("NIFTY 50 PRO DASHBOARD")

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

c1, c2, c3 = st.columns(3)
with c1:
    sel_idx = st.selectbox("Index Chuno", list(indices.keys()))
    ticker = indices[sel_idx]
with c2:
    sel_stock = st.selectbox("Stock (Optional)", ["-- Index --"] + list(stocks.keys()))
    if sel_stock!= "-- Index --":
        ticker = stocks[sel_stock]
with c3:
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
    st.error("Market band hai ya data nahi aa raha.")
    st.stop()

close = float(data['Close'].iloc[-1])
open_p = float(data['Open'].iloc[-1])
high = float(data['High'].iloc[-1])
low = float(data['Low'].iloc[-1])

m1, m2, m3, m4 = st.columns(4)
m1.metric(f"{ticker} LIVE", f"Rs {close:.2f}", f"{close-open_p:.2f}")
m2.metric("OPEN", f"Rs {open_p:.2f}")
m3.metric("HIGH", f"Rs {high:.2f}")
m4.metric("LOW", f"Rs {low:.2f}")

fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Recommendation % me")

data['SMA20'] = data['Close'].rolling(20).mean()
data['SMA50'] = data['Close'].rolling(50).mean()
delta = data['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
data['RSI'] = 100 - (100 / (1 + rs))

last_rsi = float(data['RSI'].iloc[-1])
sma20 = float(data['SMA20'].iloc[-1])
sma50 = float(data['SMA50'].iloc[-1])

if sma20 > sma50 and last_rsi < 70:
    signal, sl_pct, tgt_pct = "BUY", -1.0, 2.0
elif sma20 < sma50 and last_rsi > 30:
    signal, sl_pct, tgt_pct = "SELL", 1.0, -2.0
else:
    signal, sl_pct, tgt_pct = "HOLD", -0.5, 0.5

sl_price = close * (1 + sl_pct/100)
tgt_price = close * (1 + tgt_pct/100)

r1, r2, r3, r4 = st.columns(4)
r1.metric("Signal", signal)
r2.metric("Entry", f"Rs {close:.2f}")
r3.metric("Stoploss", f"{sl_pct}%", f"Rs {sl_price:.2f}")
r4.metric("Target", f"{tgt_pct}%", f"Rs {tgt_price:.2f}")

st.info(f"Time: {datetime.now().strftime('%H:%M:%S')} | RSI: {last_rsi:.2f}")

if st.button("Refresh Karo"):
    st.rerun()
