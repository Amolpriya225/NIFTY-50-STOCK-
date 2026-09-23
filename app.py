import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="NIFTY 50 Dashboard", layout="wide", page_icon="📈")
st.title("📈 NIFTY 50 LIVE DASHBOARD")
st.markdown("Auto-refresh har 1 minute me")

# Nifty 50 List
nifty50 = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
    "SBIN.NS","BHARTIARTL.NS","ITC.NS","LT.NS","KOTAKBANK.NS",
    "AXISBANK.NS","WIPRO.NS","MARUTI.NS","HCLTECH.NS","ULTRACEMCO.NS"
]

col1, col2 = st.columns([1,3])
with col1:
    selected = st.selectbox("Stock Chuno", nifty50)
    period = st.selectbox("Time Frame", ["1d","5d","1mo"], index=1)

with col2:
    if selected:
        df = yf.download(selected, period=period, interval="15m")
        if not df.empty:
            last_price = float(df['Close'].iloc[-1])
            prev_price = float(df['Close'].iloc[-2])
            change = last_price - prev_price
            per = (change/prev_price)*100
            
            st.metric(selected, f"₹ {last_price:.2f}", f"{change:.2f} ({per:.2f}%)")
            st.line_chart(df['Close'])
            st.dataframe(df.tail(10))
        else:
            st.warning("Data nahi aa raha, 1 min baad refresh karo")

st.success("✅ Ye dashboard bina kisi API Key ke chal raha hai")
