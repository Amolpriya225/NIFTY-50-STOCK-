import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import pyotp
from SmartApi import SmartConnect

st.set_page_config(page_title="NIFTY SPOT PRO - Angel LIVE", page_icon="📊", layout="wide")
st_autorefresh(interval=30000, key="refresh")

def get_angel_live():
    try:
        api_key = st.secrets["ANGEL_API_KEY"]
        client_code = st.secrets["ANGEL_CLIENT_CODE"]
        pin = st.secrets["ANGEL_PIN"]
        totp_secret = st.secrets["ANGEL_TOTP_SECRET"]
        obj = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_secret).now()
        session = obj.generateSession(client_code, pin, totp)
        if session.get('status') == True:
            ltp_data = obj.ltpData("NSE", "NIFTY", "26000")
            return True, ltp_data['data']['ltp'], obj
        else:
            return False, session.get('message', 'Login failed'), None
    except Exception as e:
        return False, str(e), None

with st.sidebar:
    st.header("Angel One LIVE")
    live_ok, live_price, _ = get_angel_live()
    if live_ok:
        st.success(f"LIVE NIFTY: {live_price}")
    else:
        st.warning("Angel Login pending")

st.title("📊 NIFTY SPOT PRO - Angel LIVE")
st.caption("EMA 9/21 | RSI 14 | Entry | Stop Loss | Targets - LIVE")

TIME_MAP = {
    "5M": {"period": "5d", "interval": "5m"},
    "15M": {"period": "1mo", "interval": "15m"},
    "1H": {"period": "3mo", "interval": "1h"},
    "1D": {"period": "1y", "interval": "1d"},
}

@st.cache_data(ttl=30)
def get_data(period, interval):
    ticker = yf.Ticker("^NSEI")
    df = ticker.history(period=period, interval=interval, auto_adjust=False, timeout=15)
    if df.empty:
        return df
    df = df.dropna(subset=["Open", "High", "Low", "Close"]).copy()
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.where(avg_loss!= 0)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["RSI"] = df["RSI"].fillna(50)
    prev_close = df["Close"].shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev_close).abs(), (df["Low"] - prev_close).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    return df

def calculate_signal(df):
    last = df.iloc[-1]
    close = float(last["Close"])
    ema9 = float(last["EMA9"])
    ema21 = float(last["EMA21"])
    rsi = float(last["RSI"])
    atr = last["ATR"]
    if pd.isna(atr) or float(atr) <= 0:
        return None
    atr = float(atr)
    if ema9 > ema21 and close > ema9 and 50 < rsi < 70:
        signal = "BUY"
        entry = close
        sl = entry - 1.5 * atr
        risk = entry - sl
    elif ema9 < ema21 and close < ema9 and 30 < rsi < 50:
        signal = "SELL"
        entry = close
        sl = entry + 1.5 * atr
        risk = sl - entry
    else:
        signal = "WAIT"
        entry = close
        sl = None
        risk = None
    if signal == "BUY":
        targets = [entry + risk, entry + 2 * risk, entry + 3 * risk]
    elif signal == "SELL":
        targets = [entry - risk, entry - 2 * risk, entry - 3 * risk]
    else:
        targets = [None, None, None]
    return {"signal": signal, "entry": entry, "sl": sl, "risk": risk, "targets": targets, "rsi": rsi, "ema9": ema9, "ema21": ema21, "atr": atr}

def show_timeframe(name):
    cfg = TIME_MAP[name]
    try:
        df = get_data(cfg["period"], cfg["interval"])
    except Exception as e:
        st.error(f"डेटा मिळवताना समस्या: {e}")
        return
    if df.empty or len(df) < 30:
        st.error(f"{name}: पुरेसा डेटा नाही")
        return
    levels = calculate_signal(df)
    if levels is None:
        st.warning("ATR नाही")
        return
    close = float(df["Close"].iloc[-1])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NIFTY SPOT", f"{close:,.2f}")
    c2.metric("SIGNAL", levels["signal"])
    c3.metric("RSI", f"{levels['rsi']:.1f}")
    c4.metric("EMA", "Bullish" if levels["ema9"] > levels["ema21"] else "Bearish")
    if levels["signal"] == "WAIT":
        st.info("WAIT - अटी पूर्ण नाहीत")
    else:
        st.write(f"**Entry:** {levels['entry']:,.2f} | **SL:** {levels['sl']:,.2f} | **Risk:** {levels['risk']:,.2f}")
        t1, t2, t3 = levels["targets"]
        a, b, c = st.columns(3)
        a.metric("Target 1 (1:1)", f"{t1:,.2f}")
        b.metric("Target 2 (1:2)", f"{t2:,.2f}")
        c.metric("Target 3 (1:3)", f"{t3:,.2f}")
    fig = go.F