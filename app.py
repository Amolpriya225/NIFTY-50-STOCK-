import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import math

st_autorefresh(interval=10000, key="live_refresh")
st.set_page_config(page_title="NIFTY OPTIONS PRO", layout="wide")
st.title("NIFTY 50 + OPTIONS - LIVE TRADING")

# --- NSE Option Chain Fetcher ---
@st.cache_data(ttl=15)
def get_nse_option_chain(symbol="NIFTY"):
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/option-chain"
        }
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        resp = session.get(url, headers=headers, timeout=5)
        return resp.json()
    except Exception as e:
        return None

@st.cache_data(ttl=5)
def get_spot_data(ticker, period, interval):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def analyze_option_trend(spot_df):
    # Spot ke basis par trend
    spot_df['SMA20'] = spot_df['Close'].rolling(20).mean()
    spot_df['SMA50'] = spot_df['Close'].rolling(50).mean()
    delta = spot_df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    spot_df['RSI'] = 100 - (100 / (1 + rs))

    sma20 = float(spot_df['SMA20'].iloc[-1])
    sma50 = float(spot_df['SMA50'].iloc[-1])
    rsi = float(spot_df['RSI'].iloc[-1])
    close = float(spot_df['Close'].iloc[-1])

    # Trend logic
    if sma20 > sma50 and rsi < 70 and rsi > 45:
        return "BULLISH", rsi, sma20, sma50
    elif sma20 < sma50 and rsi > 30 and rsi < 55:
        return "BEARISH", rsi, sma20, sma50
    else:
        return "SIDEWAYS", rsi, sma20, sma50

# Sidebar
idx_map = {"NIFTY 50": ("^NSEI", "NIFTY", 50), "BANK NIFTY": ("^NSEBANK", "BANKNIFTY", 100), "FIN NIFTY": ("^CNXFIN", "FINNIFTY", 50)}
sel = st.selectbox("Index Select Karo", list(idx_map.keys()))
spot_ticker, nse_symbol, step = idx_map[sel]
timeframe = st.selectbox("Chart TimeFrame", ["5m", "15m", "1h", "1d"], index=1)
period_map = {"5m": "1d", "15m": "5d", "1h": "1mo", "1d": "6mo"}

spot_df = get_spot_data(spot_ticker, period_map[timeframe], timeframe)
if spot_df.empty:
    st.error("Data nahi mila, Market band ho sakta hai")
    st.stop()

spot_price = float(spot_df['Close'].iloc[-1])
trend, rsi_val, sma20, sma50 = analyze_option_trend(spot_df)

# Metrics
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric(f"{sel} LIVE", f"{spot_price:.2f}", f"RSI: {rsi_val:.1f}")
c2.metric("TREND", trend)
c3.metric("SMA20", f"{sma20:.1f}")
c4.metric("SMA50", f"{sma50:.1f}")
c5.metric("Last Update", datetime.now().strftime("%H:%M:%S"))

# Chart
fig = go.Figure(data=[go.Candlestick(x=spot_df.index, open=spot_df['Open'], high=spot_df['High'], low=spot_df['Low'], close=spot_df['Close'])])
fig.update_layout(height=400, xaxis_rangeslider_visible=False, template="plotly_white")
fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.15], pattern="hour")])
st.plotly_chart(fig, use_container_width=True)

# Options Chain
st.divider()
st.subheader(f" {sel} Options Chain - ATM & ITM Near {spot_price:.2f}")

option_data = get_nse_option_chain(nse_symbol)
if not option_data:
    st.warning("NSE se live option data nahi aa raha, approximate strikes dikha raha hu (yfinance limitation)")
    # Fallback: manual strikes
    atm = round(spot_price / step) * step
    strikes = [atm - step*3, atm - step*2, atm - step, atm, atm + step, atm + step*2, atm + step*3]
    oc_list = []
    for s in strikes:
        oc_list.append({"strike": s, "CE_last": 0, "PE_last": 0, "CE_OI": 0, "PE_OI": 0, "CE_chng": 0, "PE_chng": 0})
else:
    records = option_data['records']['data']
    atm = option_data['records']['underlyingValue']
    atm_strike = round(atm / step) * step
    filtered = []
    for rec in records:
        if 'CE' in rec and 'PE' in rec:
            strike = rec['strikePrice']
            if atm_strike - step*3 <= strike <= atm_strike + step*3:
                filtered.append({
                    "strike": strike,
                    "CE_last": rec['CE']['lastPrice'],
                    "PE_last": rec['PE']['lastPrice'],
                    "CE_OI": rec['CE']['openInterest'],
                    "PE_OI": rec['PE']['openInterest'],
                    "CE_chng": rec['CE']['change'],
                    "PE_chng": rec['PE']['change'],
                })
    oc_list = sorted(filtered, key=lambda x: x['strike'])

# Recommendation Logic
def get_reco(option_type, trend, strike, spot):
    # option_type = CE or PE
    distance_pct = ((strike - spot)/spot)*100

    if option_type == "CE":
        if trend == "BULLISH" and strike >= spot and strike <= spot + step*2:
            # ATM CE Best
            signal = "BUY CE"
            sl_pct = -25 # Options me % bada hota hai
            tgt_pct = 50
            conf = 78
        elif trend == "BULLISH" and strike < spot:
            signal = "BUY ITM CE"
            sl_pct = -15
            tgt_pct = 30
            conf = 65
        elif trend == "BEARISH":
            signal = "EXIT / SELL CE"
            sl_pct = 0
            tgt_pct = 0
            conf = 85
        else:
            signal = "HOLD"
            sl_pct = -10
            tgt_pct = 10
            conf = 40
    else: # PE
        if trend == "BEARISH" and strike <= spot and strike >= spot - step*2:
            signal = "BUY PE"
            sl_pct = -25
            tgt_pct = 50
            conf = 78
        elif trend == "BEARISH" and strike > spot:
            signal = "BUY ITM PE"
            sl_pct = -15
            tgt_pct = 30
            conf = 65
        elif trend == "BULLISH":
            signal = "EXIT / SELL PE"
            sl_pct = 0
            tgt_pct = 0
            conf = 85
        else:
            signal = "HOLD"
            sl_pct = -10
            tgt_pct = 10
            conf = 40
    return signal, sl_pct, tgt_pct, conf

# Show Tables
col_ce, col_pe = st.columns(2)

with col_ce:
    st.markdown("### 📈 CALL (CE) OPTIONS")
    ce_rows = []
    for item in oc_list:
        sig, sl, tgt, conf = get_reco("CE", trend, item['strike'], spot_price)
        entry = item['CE_last']
        sl_price = entry * (1 + sl/100) if entry>0 else 0
        tgt_price = entry * (1 + tgt/100) if entry>0 else 0

        # EXIT Logic - Trend reverse
        exit_msg = ""
        if "EXIT" in sig:
            exit_msg = "🔴 Trend Reverse - Exit Now!"

        ce_rows.append({
            "Strike": item['strike'],
            "Type": "ATM" if item['strike']== round(spot_price/step)*step else ("ITM" if item['strike'] < spot_price else "OTM"),
            "LTP": item['CE_last'],
            "Chg": f"{item['CE_chng']:.2f}",
            "Signal": sig,
            "Conf%": f"{conf}%",
            "Entry": f"{entry:.2f}",
            "SL%": f"{sl}%",
            "TGT%": f"{tgt}%",
            "Exit Alert": exit_msg
        })
    st.dataframe(pd.DataFrame(ce_rows), use_container_width=True, height=300)

with col_pe:
    st.markdown("### 📉 PUT (PE) OPTIONS")
    pe_rows = []
    for item in oc_list:
        sig, sl, tgt, conf = get_reco("PE", trend, item['strike'], spot_price)
        entry = item['PE_last']
        pe_rows.append({
            "Strike": item['strike'],
            "Type": "ATM" if item['strike']== round(spot_price/step)*step else ("ITM" if item['strike'] > spot_price else "OTM"),
            "LTP": item['PE_last'],
            "Chg": f"{item['PE_chng']:.2f}",
            "Signal": sig,
            "Conf%": f"{conf}%",
            "Entry": f"{entry:.2f}",
            "SL%": f"{sl}%",
            "TGT%": f"{tgt}%",
            "Exit Alert": "🔴 Trend Reverse - Exit Now!" if "EXIT" in sig else ""
        })
    st.dataframe(pd.DataFrame(pe_rows), use_container_width=True, height=300)

st.info(f"**Logic:** Trend = {trend} (RSI {rsi_val:.1f}). Agar aapne CE kharida aur trend BEARISH ho gaya to EXIT signal ayega. SL -15% to -25% (Options risky), Target +30% to +50%. Yeh % Option ke LTP par hai.")
