import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="NIFTY SPOT PRO", layout="wide")
st_autorefresh(interval=10000, key="spot_refresh")

st.title("📊 NIFTY SPOT - 1:1 | 1:2 | 1:3 TARGET")
st.caption("Risk:Reward - 1:1, 1:2, 1:3")

tab_5m, tab_15m, tab_1h, tab_1d = st.tabs(["5M", "15M", "1H", "1D"])

TIME_MAP = {
    "5M": {"period": "1d", "interval": "5m"},
    "15M": {"period": "5d", "interval": "15m"},
    "1H": {"period": "1mo", "interval": "1h"},
    "1D": {"period": "6mo", "interval": "1d"},
}

def get_data(period, interval):
    df = yf.Ticker("^NSEI").history(period=period, interval=interval)
    return df

def calculate_levels(df):
    if df.empty or len(df) < 2:
        return None
    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = float(last["Close"])
    high = float(last["High"])
    low = float(last["Low"])
    open_price = float(last["Open"])

    bullish = close > open_price

    if bullish:
        entry = close
        sl = low
        risk = entry - sl
        signal = "BUY 🟢"
    else:
        entry = close
        sl = high
        risk = sl - entry
        signal = "SELL 🔴" if close < open_price else "BUY 🟢"

    # Risk 0 fix
    if risk <= 0:
        risk = close * 0.002 # 0.2% default

    # RISK 1:1, 1:2, 1:3
    if bullish:
        t1 = entry + risk * 1
        t2 = entry + risk * 2
        t3 = entry + risk * 3
    else:
        t1 = entry - risk * 1
        t2 = entry - risk * 2
        t3 = entry - risk * 3

    # Confirmation %
    if abs(close - open_price) > (high - low) * 0.6:
        conf = 85
    elif close > prev["Close"] if bullish else close < prev["Close"]:
        conf = 70
    else:
        conf = 55

    return {
        "entry": entry, "sl": sl, "risk": risk,
        "t1": t1, "t2": t2, "t3": t3,
        "signal": signal, "conf": conf
    }

def show_for_tf(name):
    cfg = TIME_MAP[name]
    df = get_data(cfg["period"], cfg["interval"])
    if df.empty:
        st.error(f"{name} Data not available")
        return

    levels = calculate_levels(df)
    if not levels:
        return

    # METRICS
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("SPOT", f"{df['Close'].iloc[-1]:,.2f}")
    c2.metric(f"{levels['signal']} ENTRY", f"{levels['entry']:,.2f}")
    c3.metric("SL (RISK)", f"{levels['sl']:,.2f}", delta=f"-{levels['risk']:.1f}")
    c4.metric("T1 (1:1)", f"{levels['t1']:,.2f}")
    c5.metric("T2 (1:2)", f"{levels['t2']:,.2f}")
    c6.metric("T3 (1:3)", f"{levels['t3']:,.2f}")

    st.progress(levels['conf'], text=f"Confirmation: {levels['conf']}% | Signal: {levels['signal']}")

    # CHART
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="NIFTY"
    ))
    fig.add_hline(y=levels['entry'], line_color="blue", line_width=2, annotation_text="ENTRY")
    fig.add_hline(y=levels['sl'], line_color="red", line_dash="dash", annotation_text=f"SL")
    fig.add_hline(y=levels['t1'], line_color="#00ff00", line_dash="dot", annotation_text="T1 1:1")
    fig.add_hline(y=levels['t2'], line_color="#00cc00", line_dash="dot", annotation_text="T2 1:2")
    fig.add_hline(y=levels['t3'], line_color="#009900", line_dash="dot", annotation_text="T3 1:3")

    fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(t=30,b=10))
    st.plotly_chart(fig, use_container_width=True)

    # TABLE
    st.table(pd.DataFrame([{
        "ENTRY": f"{levels['entry']:.2f}",
        "SL": f"{levels['sl']:.2f}",
        "RISK": f"{levels['risk']:.2f}",
        "T1 (1:1)": f"{levels['t1']:.2f}",
        "T2 (1:2)": f"{levels['t2']:.2f}",
        "T3 (1:3)": f"{levels['t3']:.2f}",
        "Confirmation": f"{levels['conf']}%"
    }]))

with tab_5m:
    show_for_tf("5M")
with tab_15m:
    show_for_tf("15M")
with tab_1h:
    show_for_tf("1H")
with tab_1d:
    show_for_tf("1D")
