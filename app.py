import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="NIFTY 50 Dashboard", layout="wide")
st.title("📈 NIFTY 50 LIVE DASHBOARD")

nifty50 = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","BHARTIARTL.NS"]

stock = st.selectbox("Stock Chuno", nifty50)
data = yf.download(stock, period="5d", interval="15m")

if not data.empty:
    price = float(data['Close'].iloc[-1])
    st.metric(stock, f"₹ {price:.2f}")
    st.line_chart(data['Close'])
    st.dataframe(data.tail(10))
