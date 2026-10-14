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