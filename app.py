import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="NIFTY MTF OPTIONS PRO", layout="wide")
st_autorefresh(interval=10000, key="nifty_refresh")

st.title("🚀 NIFTY / BANK NIFTY - MULTI TIMEFRAME OPTIONS PRO")

TIMEFRAMES = {
    "5m": {"period": "1d", "weight": 1},
    "15m": {"period": "5d", "weight": 2},
    "1h": {"period": "1mo", "weight": 3},
}

def analyze_timeframe(tf, ticker="^NSEI"):
    try:
        info = TIMEFRAMES[tf]
        df = yf.Ticker(ticker).history(period=info["period"], interval=tf)
        if df.empty or len(df) < 2:
            return None
        # Simple Score Logic: Close > Open = Bullish
        score = 1 if df["Close"].iloc[-1] > df["Open"].iloc[-1] else -1
        return {"TF": tf, "Score": float(score), "Close": float(df["Close"].iloc[-1])}
    except:
        return None

# --- FIXED WEIGHTED SCORE LOGIC - NO ERROR ---
weighted_score = 0.0
total_weight = 0.0
results = []

for tf in TIMEFRAMES:
    result = analyze_timeframe(tf)
    if result is None:
        continue

    score = result.get("Score")
    if score is None or pd.isna(score):
        continue

    weight = float(TIMEFRAMES[tf]["weight"])

    weighted_score += score * weight
    total_weight += weight
    results.append(result)

if total_weight > 0:
    final_score = weighted_score / total_weight
else:
    final_score = 0.0
    st.warning("Data not available for MTF, showing live chart only.")

# --- MAIN CHART ---
nifty = yf.Ticker("^NSEI")
data = nifty.history(period="1d", interval="5m")

if data.empty:
    st.error("Unable to fetch NIFTY data.")
    st.stop()

current_price = data["Close"].iloc[-1]

col1, col2, col3 = st.columns(3)
col1.metric("NIFTY 50", f"{current_price:,.2f}")
col2.metric("Final MTF Score", f"{final_score:.2f}")
col3.metric("Signal", "BUY 🟢" if final_score > 0 else "SELL 🔴" if final_score < 0 else "WAIT")

fig = go.Figure()
fig.add_trace(go.Candlestick(x=data.index, open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"], name="NIFTY"))
fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True)
