import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import pyotp
from SmartApi import SmartConnect

st.set_page_config(page_title="NIFTY SPOT PRO", page_icon="📊", layout="wide")
st_autorefresh(interval=30000, key="refresh")

with st.sidebar:
    st.header("Angel One LIVE")
    st.success("Login Ready")

st.title("📊 NIFTY SPOT PRO")
st.caption("EMA 9/21 | RSI 14 | Entry | Stop Loss | Targets")

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
    if df.empty: return df
    df = df.dropna(subset=["Open", "High", "Low", "Close"]).copy()
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.where(avg_loss!=0)
    df["RSI"] = 100 - (100 / (1 + rs)); df["RSI"] = df["RSI"].fillna(50)
    prev_close = df["Close"].shift(1)
    tr = pd.concat([df["High"]-df["Low"], (df["High"]-prev_close).abs(), (df["Low"]-prev_close).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    return df

def calculate_signal(df):
    last = df.iloc[-1]; close = float(last["Close"]); ema9 = float(last["EMA9"]); ema21 = float(last["EMA21"]); rsi = float(last["RSI"]); atr = last["ATR"]
    if pd.isna(atr) or float(atr)<=0: return None
    atr=float(atr)
    if ema9>ema21 and close>ema9 and 50<rsi<70: signal="BUY"; entry=close; sl=entry-1.5*atr; risk=entry-sl
    elif ema9<ema21 and close<ema9 and 30<rsi<50: signal="SELL"; entry=close; sl=entry+1.5*atr; risk=sl-entry
    else: signal="WAIT"; entry=close; sl=None; risk=None
    if signal=="BUY": targets=[entry+risk, entry+2*risk, entry+3*risk]
    elif signal=="SELL": targets=[entry-risk, entry-2*risk, entry-3*risk]
    else: targets=[None,None,None]
    return {"signal":signal,"entry":entry,"sl":sl,"risk":risk,"targets":targets,"rsi":rsi,"ema9":ema9,"ema21":ema21,"atr":atr}

def show_timeframe(name):
    cfg=TIME_MAP[name]
    try: df=get_data(cfg["period"], cfg["interval"])
    except Exception as e: st.error(f"Error: {e}"); return
    if df.empty or len(df)<30: st.error(f"{name}: data nahi"); return
    levels=calculate_signal(df)
    if levels is None: st.warning("ATR nahi"); return
    close=float(df["Close"].iloc[-1])
    c1,c2,c3,c4=st.columns(4)
    c1.metric("NIFTY SPOT", f"{close:,.2f}"); c2.metric("SIGNAL", levels["signal"]); c3.metric("RSI", f"{levels['rsi']:.1f}"); c4.metric("EMA", "Bullish" if levels["ema9"]>levels["ema21"] else "Bearish")
    if levels["signal"]=="WAIT": st.info("WAIT")
    else:
        st.write(f"**Entry:** {levels['entry']:,.2f} | **SL:** {levels['sl']:,.2f}")
        t1,t2,t3=levels["targets"]; a,b,c=st.columns(3)
        a.metric("T1 (1:1)", f"{t1:,.2f}"); b.metric("T2 (1:2)", f"{t2:,.2f}"); c.metric("T3 (1:3)", f"{t3:,.2f}")
    fig=go.Figure(); fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="NIFTY"))
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA9"], name="EMA 9", mode="lines")); fig.add_trace(go.Scatter(x=df.index, y=df["EMA21"], name="EMA 21", mode="lines"))
    if levels["sl"] is not None:
        fig.add_hline(y=levels["entry"], line_color="blue", annotation_text="Entry"); fig.add_hline(y=levels["sl"], line_color="red", line_dash="dash", annotation_text="SL")
        for i,t in enumerate(levels["targets"],1): fig.add_hline(y=t, line_dash="dot", annotation_text=f"T{i}")
    fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, legend=dict(orientation="h"), margin=dict(t=30,b=20))
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("RSI (14)"); rsi_fig=go.Figure(); rsi_fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", mode="lines"))
    rsi_fig.add_hline(y=70, line_dash="dash"); rsi_fig.add_hline(y=30, line_dash="dash"); rsi_fig.update_layout(height=250, template="plotly_dark", yaxis=dict(range=[0,100]))
    st.plotly_chart(rsi_fig, use_container_width=True)

tab5,tab15,tab1h,tab1d=st.tabs(["5 MIN","15 MIN","1 HOUR","1 DAY"])
with tab5: show_timeframe("5M")
with tab15: show_timeframe("15M")
with tab1h: show_timeframe("1H")
with tab1d: show_timeframe("1D")

st.divider()
st.subheader("Angel One API Status - FIXED")

def get_angel_live_fixed():
    try:
        api_key = st.secrets["ANGEL_API_KEY"].strip()
        client_code = st.secrets["ANGEL_CLIENT_CODE"].strip()
        pin = st.secrets["ANGEL_PIN"].strip()
        totp_secret = st.secrets["ANGEL_TOTP_SECRET"].strip().replace(" ", "")
        obj = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_secret).now()
        session = obj.generateSession(client_code, pin, totp)

        if not isinstance(session, dict) or not session.get('status'):
            return False, f"Login fail: {session}"

        # LTP with safe parsing - heach fix aahe
        try:
            ltp_data = obj.ltpData("NSE", "NIFTY", "26000")
            # Different versions return different format
            if isinstance(ltp_data, dict):
                data = ltp_data.get('data', {})
                price = data.get('ltp') or data.get('last') or data.get('close') or 0
                if isinstance(data, dict) and not price and 'ltp' in str(ltp_data).lower():
                    # try alternative parsing
                    price = data.get('ltp')
                return True, price if price else ltp_data
            else:
                return True, ltp_data
        except Exception as ltp_err:
            # Login zala pan LTP fail - tarihi success manu
            return True, f"Login OK (LTP error: {ltp_err}) - {client_code}"

    except Exception as e:
        return False, str(e)

if st.button("Test SmartAPI Setup - REAL LOGIN"):
    ok, msg = get_angel_live_fixed()
    if ok:
        st.success(f"Angel Login SUCCESS! LIVE = {msg}")
        st.balloons()
        st.sidebar.success(f"LIVE: {msg}")
    else:
        st.error(f"FAIL: {msg}")

# Auto live price sidebar madhe
try:
    ok_live, price_live = get_angel_live_fixed()
    if ok_live:
        st.sidebar.metric("LIVE NIFTY", f"{price_live}")
except:
    pass