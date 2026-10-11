
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="NIFTY SPOT PRO",
    page_icon="📊",
    layout="wide"
)

st_autorefresh(interval=30000, key="refresh")

st.title("📊 NIFTY SPOT PRO")
st.caption(
    "EMA 9/21 | RSI 14 | Entry | Stop Loss | Targets"
)
st.warning(
    "शैक्षणिक संकेतांसाठी. हा अधिकृत रिअल-टाइम डेटा नाही. "
    "सिग्नलवरून थेट ट्रेड करू नका."
)

TIME_MAP = {
    "5M": {"period": "5d", "interval": "5m"},
    "15M": {"period": "1mo", "interval": "15m"},
    "1H": {"period": "3mo", "interval": "1h"},
    "1D": {"period": "1y", "interval": "1d"},
}


@st.cache_data(ttl=30)
def get_data(period, interval):
    ticker = yf.Ticker("^NSEI")
    df = ticker.history(
        period=period,
        interval=interval,
        auto_adjust=False,
        timeout=15
    )
    if df.empty:
        return df

    df = df.dropna(
        subset=["Open", "High", "Low", "Close"]
    ).copy()

    df["EMA9"] = df["Close"].ewm(
        span=9, adjust=False
    ).mean()

    df["EMA21"] = df["Close"].ewm(
        span=21, adjust=False
    ).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()

    rs = avg_gain / avg_loss.where(avg_loss != 0)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["RSI"] = df["RSI"].fillna(50)

    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

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
        targets = [
            entry + risk,
            entry + 2 * risk,
            entry + 3 * risk,
        ]
    elif signal == "SELL":
        targets = [
            entry - risk,
            entry - 2 * risk,
            entry - 3 * risk,
        ]
    else:
        targets = [None, None, None]

    return {
        "signal": signal,
        "entry": entry,
        "sl": sl,
        "risk": risk,
        "targets": targets,
        "rsi": rsi,
        "ema9": ema9,
        "ema21": ema21,
        "atr": atr,
    }


def show_timeframe(name):
    cfg = TIME_MAP[name]

    try:
        df = get_data(cfg["period"], cfg["interval"])
    except Exception as e:
        st.error(f"डेटा मिळवताना समस्या: {e}")
        return

    if df.empty or len(df) < 30:
        st.error(
            f"{name}: पुरेसा डेटा उपलब्ध नाही. "
            "थोड्या वेळाने पुन्हा प्रयत्न करा."
        )
        return

    levels = calculate_signal(df)

    if levels is None:
        st.warning("ATR तयार करण्यासाठी पुरेसा डेटा नाही.")
        return

    close = float(df["Close"].iloc[-1])
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("NIFTY SPOT", f"{close:,.2f}")
    c2.metric("SIGNAL", levels["signal"])
    c3.metric("RSI (14)", f"{levels['rsi']:.1f}")
    c4.metric("EMA TREND", 
              "Bullish" if levels["ema9"] > levels["ema21"]
              else "Bearish")

    if levels["signal"] == "WAIT":
        st.info(
            "सध्या सर्व BUY/SELL अटी पूर्ण झालेल्या नाहीत. "
            "WAIT म्हणजे ट्रेड घेण्याची शिफारस नाही."
        )
    else:
        st.write(f"**संकेताधारित Entry:** {levels['entry']:,.2f}")
        st.write(f"**ATR आधारित Stop Loss:** {levels['sl']:,.2f}")
        st.write(
            f"**जोखीम अंतर:** {levels['risk']:,.2f} "
            "NIFTY पॉइंट्स"
        )

        t1, t2, t3 = levels["targets"]
        a, b, c = st.columns(3)
        a.metric("Target 1 (1:1)", f"{t1:,.2f}")
        b.metric("Target 2 (1:2)", f"{t2:,.2f}")
        c.metric("Target 3 (1:3)", f"{t3:,.2f}")

    st.caption(
        "हे स्तर शेवटच्या उपलब्ध कँडलच्या Close वर आधारित आहेत. "
        "सिग्नलची यशस्विता किंवा नफा हमखास नाही."
    )

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="NIFTY"
    ))

    fig.add_trace(go.Scatter(
        x=df.index, y=df["EMA9"],
        name="EMA 9", mode="lines"
    ))

    fig.add_trace(go.Scatter(
        x=df.index, y=df["EMA21"],
        name="EMA 21", mode="lines"
    ))

    if levels["sl"] is not None:
        fig.add_hline(
            y=levels["entry"], line_color="blue",
            annotation_text="Entry"
        )
        fig.add_hline(
            y=levels["sl"], line_color="red",
            line_dash="dash", annotation_text="SL"
        )

        for i, target in enumerate(levels["targets"], 1):
            fig.add_hline(
                y=target,
                line_dash="dot",
                annotation_text=f"T{i}"
            )

    fig.update_layout(
        height=550,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h"),
        margin=dict(t=30, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("RSI (14)")
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"],
        name="RSI", mode="lines"
    ))
    rsi_fig.add_hline(y=70, line_dash="dash")
    rsi_fig.add_hline(y=30, line_dash="dash")
    rsi_fig.update_layout(
        height=250,
        template="plotly_dark",
        yaxis=dict(range=[0, 100])
    )
    st.plotly_chart(rsi_fig, use_container_width=True)

    with st.expander("शेवटच्या 10 कँडल्सचा डेटा"):
        st.dataframe(
            df[["Open", "High", "Low", "Close",
                "EMA9", "EMA21", "RSI", "ATR"]]
            .tail(10).round(2),
            use_container_width=True
        )


tab5, tab15, tab1h, tab1d = st.tabs(
    ["5 MIN", "15 MIN", "1 HOUR", "1 DAY"]
)

with tab5:
    show_timeframe("5M")

with tab15:
    show_timeframe("15M")

with tab1h:
    show_timeframe("1H")

with tab1d:
    show_timeframe("1D")

# NIFTY SPOT PRO dashboard
