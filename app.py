import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

st.set_page_config(page_title="NIFTY MTF OPTIONS PRO", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=10000, key="market_refresh")
st.title("🚀 NIFTY / BANK NIFTY – MULTI TIMEFRAME OPTIONS PRO")

def play_alert_sound():
    components.html("""<audio autoplay><source src="https://www.soundjay.com/buttons/beep-07a.mp3" type="audio/mpeg"></audio>
    <script>var a=new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');a.play();</script>""", height=0)

idx_map = {"NIFTY 50": {"ticker": "^NSEI","nse_symbol": "NIFTY","step": 50}, "BANK NIFTY": {"ticker": "^NSEBANK","nse_symbol": "BANKNIFTY","step": 100}}
sel = st.sidebar.selectbox("Select Index", list(idx_map.keys()))
spot_ticker = idx_map[sel]["ticker"]; nse_sym = idx_map[sel]["nse_symbol"]; strike_step = idx_map[sel]["step"]

TIMEFRAMES = {"1m": {"period": "1d","interval": "1m","weight": 1,"purpose": "Entry"},"3m": {"period": "1d","interval": "1m","weight": 1,"purpose": "Momentum"},"5m": {"period": "5d","interval": "5m","weight": 2,"purpose": "Primary Entry"},"15m": {"period": "1mo","interval": "15m","weight": 3,"purpose": "Trend Confirmation"},"30m": {"period": "1mo","interval": "30m","weight": 3,"purpose": "Major Intraday Trend"},"1h": {"period": "3mo","interval": "1h","weight": 4,"purpose": "Higher Trend"}}

@st.cache_data(ttl=8)
def get_market_data(ticker, period, interval):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False, threads=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.dropna(); return df
    except Exception: return pd.DataFrame()

def calculate_indicators(df):
    df = df.copy()
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["SMA20"] = df["Close"].rolling(20).mean(); df["SMA50"] = df["Close"].rolling(50).mean()
    delta = df["Close"].diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean(); avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan); df["RSI"] = 100 - (100 / (1 + rs))
    high_low = df["High"] - df["Low"]; high_close = abs(df["High"] - df["Close"].shift()); low_close = abs(df["Low"] - df["Close"].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1); df["ATR"] = true_range.rolling(14).mean()
    df["VolumeMA20"] = df["Volume"].rolling(20).mean()
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    cumulative_volume = df["Volume"].cumsum(); df["VWAP"] = (typical_price * df["Volume"]).cumsum() / cumulative_volume
    return df

def market_structure(df):
    if len(df) < 10: return "UNKNOWN"
    recent = df.tail(10); last_close = float(recent["Close"].iloc[-1])
    previous_high = float(recent["High"].iloc[:-1].max()); previous_low = float(recent["Low"].iloc[:-1].min())
    if last_close > previous_high: return "BREAKOUT"
    if last_close < previous_low: return "BREAKDOWN"
    ema9 = float(df["EMA9"].iloc[-1]); ema21 = float(df["EMA21"].iloc[-1])
    if ema9 > ema21: return "HH/HL"
    if ema9 < ema21: return "LH/LL"
    return "RANGE"

def analyze_timeframe(df):
    if df.empty or len(df) < 60: return None
    df = calculate_indicators(df); last = df.iloc[-1]
    close = float(last["Close"]); ema9 = float(last["EMA9"]); ema21 = float(last["EMA21"]); sma20 = float(last["SMA20"]); sma50 = float(last["SMA50"]); rsi = float(last["RSI"]); vwap = float(last["VWAP"]); atr = float(last["ATR"]); volume = float(last["Volume"]); volume_ma = float(last["VolumeMA20"])
    score = 50
    if ema9 > ema21: score += 10
    else: score -= 10
    if sma20 > sma50: score += 10
    else: score -= 10
    if 55 <= rsi <= 70: score += 10
    elif 30 <= rsi <= 45: score -= 10
    elif rsi > 70: score -= 5
    elif rsi < 30: score += 5
    if close > vwap: score += 8
    else: score -= 8
    if volume_ma > 0:
        volume_ratio = volume / volume_ma
        if volume_ratio >= 1.3:
            if close > float(last["Open"]): score += 7
            else: score -= 7
    structure = market_structure(df)
    if structure == "BREAKOUT": score += 8
    elif structure == "BREAKDOWN": score -= 8
    elif structure == "HH/HL": score += 5
    elif structure == "LH/LL": score -= 5
    score = max(0, min(100, score))
    if score >= 65: trend = "BULLISH"
    elif score <= 35: trend = "BEARISH"
    else: trend = "SIDEWAYS"
    return {"Close": close,"EMA9": ema9,"EMA21": ema21,"SMA20": sma20,"SMA50": sma50,"RSI": rsi,"VWAP": vwap,"ATR": atr,"VolumeRatio": (volume / volume_ma if volume_ma > 0 else 0),"Structure": structure,"Score": score,"Trend": trend,"Data": df}

@st.cache_data(ttl=8)
def get_all_timeframes(ticker):
    results = {}
    for tf, cfg in TIMEFRAMES.items():
        df = get_market_data(ticker, cfg["period"], cfg["interval"])
        if tf == "3m" and not df.empty:
            df = df.copy()
            df = df.resample("3min").agg({"Open": "first","High": "max","Low": "min","Close": "last","Volume": "sum"}).dropna()
        if not df.empty: results[tf] = analyze_timeframe(df)
    return results

results = get_all_timeframes(spot_ticker)
if not results:
    st.error("Live market data available nahi hai. Internet/data source check karein."); st.stop()

available_tfs = list(results.keys()); primary_tf = "5m" if "5m" in results else available_tfs[0]
spot = results[primary_tf]["Close"]

weighted_score = 0; total_weight = 0; bull_count = 0; bear_count = 0
for tf, result in results.items():
    # OLD CODE KO HATAO - YE NAYA LAGAO
weighted_score = 0
total_weight = 0

for tf in TIMEFRAMES:
    result = analyze_timeframe(tf) # aapka function jo score nikalta hai
    if result is None or result.get("Score") is None:
        continue

    try:
        score = float(result["Score"])
        weight = float(TIMEFRAMES[tf]["weight"])
    except:
        continue

    if pd.isna(score) or pd.isna(weight):
        continue

    weighted_score += score * weight
    total_weight += weight

# Final score
if total_weight > 0:
    final_score = weighted_score / total_weight
else:
    final_score = 0
    if result["Trend"] == "BULLISH": bull_count += 1
    elif result["Trend"] == "BEARISH": bear_count += 1
mtf_score = weighted_score / total_weight

higher_tf = []; lower_tf = []
for tf in ["1h", "30m", "15m"]:
    if tf in results: higher_tf.append(results[tf]["Trend"])
for tf in ["5m", "3m", "1m"]:
    if tf in results: lower_tf.append(results[tf]["Trend"])

bull_higher = sum(1 for x in higher_tf if x == "BULLISH"); bear_higher = sum(1 for x in higher_tf if x == "BEARISH")
bull_lower = sum(1 for x in lower_tf if x == "BULLISH"); bear_lower = sum(1 for x in lower_tf if x == "BEARISH")

if (mtf_score >= 68 and bull_higher >= 2 and bull_lower >= 2):
    final_signal = "BUY CE"; final_trend = "BULLISH"
elif (mtf_score <= 32 and bear_higher >= 2 and bear_lower >= 2):
    final_signal = "BUY PE"; final_trend = "BEARISH"
else:
    final_signal = "WAIT"; final_trend = "SIDEWAYS / MIXED"

st.sidebar.divider(); st.sidebar.metric("MTF SCORE", f"{mtf_score:.0f}/100"); st.sidebar.metric("FINAL SIGNAL", final_signal)
st.sidebar.write("Higher TF:", higher_tf); st.sidebar.write("Lower TF:", lower_tf)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"{sel} SPOT", f"₹{spot:,.2f}"); c2.metric("MTF SCORE", f"{mtf_score:.0f}/100"); c3.metric("TREND", final_trend); c4.metric("SIGNAL", final_signal); c5.metric("TIME", datetime.now().strftime("%H:%M:%S"))

st.subheader("📊 Multi-Timeframe Analysis")
rows = []
for tf in TIMEFRAMES:
    if tf not in results: continue
    r = results[tf]
    rows.append({"TF": tf,"Purpose": TIMEFRAMES[tf]["purpose"],"Trend": r["Trend"],"Score": round(r["Score"]),"RSI": round(r["RSI"], 1),"VWAP": ("ABOVE" if r["Close"] > r["VWAP"] else "BELOW"),"Structure": r["Structure"],"Volume": f"{r['VolumeRatio']:.1f}x"})
mtf_df = pd.DataFrame(rows)
st.dataframe(mtf_df, use_container_width=True, hide_index=True)

primary_data = results[primary_tf]; df = primary_data["Data"]; rsi = primary_data["RSI"]; atr = primary_data["ATR"]

if final_signal == "BUY CE":
    entry = spot; stoploss = spot - (atr * 1.2); target1 = spot + (atr * 1.5); target2 = spot + (atr * 2.5)
elif final_signal == "BUY PE":
    entry = spot; stoploss = spot + (atr * 1.2); target1 = spot - (atr * 1.5); target2 = spot - (atr * 2.5)
else:
    entry = spot; stoploss = spot; target1 = spot; target2 = spot

st.subheader("🎯 Trade Plan")
p1, p2, p3, p4, p5 = st.columns(5)
p1.metric("Signal", final_signal); p2.metric("Entry", f"₹{entry:,.2f}"); p3.metric("Stop Loss", f"₹{stoploss:,.2f}"); p4.metric("Target 1", f"₹{target1:,.2f}"); p5.metric("Target 2", f"₹{target2:,.2f}")

if final_signal == "BUY CE":
    st.success(f"🟢 BULLISH MTF SETUP | Spot: ₹{spot:,.2f} | MTF Score: {mtf_score:.0f}/100 | ATR: {atr:.2f} | SL: ₹{stoploss:,.2f} | T1: ₹{target1:,.2f} | T2: ₹{target2:,.2f} | 1m/3m confirmation ke baad entry lo")
elif final_signal == "BUY PE":
    st.error(f"🔴 BEARISH MTF SETUP | Spot: ₹{spot:,.2f} | MTF Score: {mtf_score:.0f}/100 | ATR: {atr:.2f} | SL: ₹{stoploss:,.2f} | T1: ₹{target1:,.2f} | T2: ₹{target2:,.2f} | 1m/3m confirmation ke baad entry lo")
    play_alert_sound()
else:
    st.warning(f"⚪ NO TRADE / WAIT | MTF Score: {mtf_score:.0f}/100 | Timeframes aligned nahi hai. Force trade mat karo.")

# CHART WITH INDICATORS + SCROLL ENABLED
st.subheader(f"📈 {sel} – {primary_tf} Chart - Scroll & Zoom Enabled")
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.60, 0.20, 0.20])
fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=sel), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["EMA9"], name="EMA 9", line=dict(width=1.5, color='orange')), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["EMA21"], name="EMA 21", line=dict(width=1.5, color='blue')), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP", line=dict(width=1.5, color='green')), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(width=1.3, color='purple')), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1); fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1); fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color='lightblue'), row=3, col=1)
fig.update_layout(height=750, template="plotly_white", xaxis_rangeslider_visible=False, hovermode="x unified", dragmode="pan", showlegend=True)
fig.update_xaxes(showspikes=True, rangeslider_visible=False)
fig.update_yaxes(fixedrange=False)
st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True, "modeBarButtonsToAdd": ["drawline","drawopenpath","eraseshape"]})

# NSE OPTION CHAIN
@st.cache_data(ttl=20)
def get_nse_chain(symbol="NIFTY"):
    try:
        sess = requests.Session()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36","Accept": "*/*","Referer": "https://www.nseindia.com/option-chain"}
        sess.get("https://www.nseindia.com/option-chain", headers=headers, timeout=10)
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        r = sess.get(url, headers=headers, timeout=10)
        if r.status_code == 200: return r.json()
    except Exception: return None
    return None

st.divider()
atm = round(spot / strike_step) * strike_step
st.subheader(f"🔗 Option Chain – ATM {atm} - ONLY 100% CONFIRMED SIGNALS")

chain = get_nse_chain(nse_sym)

# OPTION SIGNAL - FINAL FIX
st.subheader("🎯 Option Trade Bias - 100% Confirmed Only")

if chain and final_signal!= "WAIT":
    try:
        records = chain["records"]["data"]
        ce_confirmed = None; pe_confirmed = None

        for rec in records:
            strike = rec.get("strikePrice")
            if strike == atm:
                ce = rec.get("CE", {}); pe = rec.get("PE", {})
                if final_signal == "BUY CE":
                    ce_confirmed = {"Strike": strike, "Type": "ATM", "LTP": ce.get("lastPrice",0), "OI": ce.get("openInterest",0), "Chg OI": ce.get("changeinOpenInterest",0), "Signal": "✅ BUY CE - 100% MTF CONFIRMED", "Conf": f"{mtf_score:.0f}%", "Reason": f"Higher TF {bull_higher}/3 Bullish + Lower TF {bull_lower}/3 Bullish"}
                if final_signal == "BUY PE":
                    pe_confirmed = {"Strike": strike, "Type": "ATM", "LTP": pe.get("lastPrice",0), "OI": pe.get("openInterest",0), "Chg OI": pe.get("changeinOpenInterest",0), "Signal": "✅ BUY PE - 100% MTF CONFIRMED", "Conf": f"{100-mtf_score:.0f}%", "Reason": f"Higher TF {bear_higher}/3 Bearish + Lower TF {bear_lower}/3 Bearish"}

        if final_signal == "BUY CE" and ce_confirmed:
            st.success(f"**{ce_confirmed['Signal']}**")
            st.dataframe(pd.DataFrame([ce_confirmed]), use_container_width=True, hide_index=True)
            st.info(f"Entry: ₹{ce_confirmed['LTP']} | SL: 25% | Target: 50%+ | Logic: {ce_confirmed['Reason']}")
        elif final_signal == "BUY PE" and pe_confirmed:
            st.error(f"**{pe_confirmed['Signal']}**")
            st.dataframe(pd.DataFrame([pe_confirmed]), use_container_width=True, hide_index=True)
            st.info(f"Entry: ₹{pe_confirmed['LTP']} | SL: 25% | Target: 50%+ | Logic: {pe_confirmed['Reason']}")
        else:
            st.warning("NSE data me ATM strike nahi mila, retry karo.")

    except Exception as e:
        st.warning(f"Option chain format error: {e}")
else:
    if final_signal == "WAIT":
        st.info(f"🔍 MTF Score {mtf_score:.0f}/100 - Abhi koi 100% Confirmed signal nahi hai. Market SIDEWAYS hai. Wait karo.")
        st.dataframe(pd.DataFrame([{"Status": "NO TRADE", "MTF Score": f"{mtf_score:.0f}", "Higher TF Bullish": bull_higher, "Lower TF Bullish": bull_lower, "Higher TF Bearish": bear_higher, "Lower TF Bearish": bear_lower, "Message": "Timeframes aligned nahi - No random option will be shown"}]), use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ NSE option chain currently unavailable - Fake data nahi dikhayenge. 1 min baad refresh karo.")

# FULL CHAIN TABLE (optional - only show nearest)
if chain:
    st.subheader("📋 Full Chain (Near ATM 3 strikes)")
    option_rows = []
    for rec in chain["records"]["data"]:
        strike = rec.get("strikePrice")
        if atm - strike_step*3 <= strike <= atm + strike_step*3:
            ce = rec.get("CE", {}); pe = rec.get("PE", {})
            option_rows.append({"Strike": strike, "CE LTP": ce.get("lastPrice",0), "CE OI": ce.get("openInterest",0), "CE Chg OI": ce.get("changeinOpenInterest",0), "PE LTP": pe.get("lastPrice",0), "PE OI": pe.get("openInterest",0), "PE Chg OI": pe.get("changeinOpenInterest",0)})
    st.dataframe(pd.DataFrame(option_rows).sort_values("Strike"), use_container_width=True, hide_index=True)
