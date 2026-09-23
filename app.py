import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="NIFTY 50 LIVE", layout="wide")
st.title("📈 NIFTY 50 LIVE DASHBOARD")

nifty50 = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "KOTAKBANK.NS"]

stock = st.selectbox("Stock Chuno", nifty50)

@st.cache_data(ttl=60)
def get_data(ticker):
    data = yf.download(ticker, period="1d", interval="5m", progress=False)
    return data

data = get_data(stock)

if data.empty:
    st.error(f"{stock} ka data abhi nahi mil raha, 1 min baad refresh karo. Market band bhi ho sakta hai.")
else:
    try:
        # Close price nikalne ka safe tarika
        close_data = data['Close']
        if isinstance(close_data, pd.DataFrame):
            close_data = close_data.iloc[:, 0]
        
        price = float(close_data.iloc[-1])
        st.metric(label=f"{stock} Live Price", value=f"₹ {price:.2f}")

        st.line_chart(close_data)
        st.dataframe(data.tail())
    except Exception as e:
        st.error(f"Data load me issue: {e}")
