import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="V44 PRO AI TRADER", layout="wide")

st.title("🤖 V44 PRO AI TRADER")

API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", None)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh AI Scan"):
    st.cache_data.clear()
    st.rerun()

# =========================
# DARK MODE UI
# =========================
st.markdown("""
<style>

.stApp {
    background:#05070D;
    color:#EAEAEA;
}

h1,h2,h3 {
    color:#00E5FF;
}

.card {
    background:#0B1220;
    padding:14px;
    border-radius:14px;
    margin-bottom:12px;
    border:1px solid #1f2937;
}

.buy { border-left:5px solid #00FF88; }
.sell { border-left:5px solid #FF3B3B; }

</style>
""", unsafe_allow_html=True)

# =========================
# COINS
# =========================
coins = ["BTC/USD","ETH/USD","XRP/USD","SOL/USD","ADA/USD","DOGE/USD","BNB/USD"]

selected = st.sidebar.multiselect("Coins", coins, default=coins)

# =========================
# DATA
# =========================
@st.cache_data(ttl=30)
def load_data(symbol):

    if not API_KEY:
        return None

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": "15min",
        "outputsize": 200,
        "apikey": API_KEY
    }

    r = requests.get(url, params=params).json()

    if "values" not in r:
        return None

    df = pd.DataFrame(r["values"])
    df = df.iloc[::-1]

    for c in ["open","high","low","close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

# =========================
# STRUCTURE + MOMENTUM
# =========================
def structure(df):

    price = df["close"].iloc[-1]

    window = 20

    support = df["low"].rolling(window).min().iloc[-1]
    resistance = df["high"].rolling(window).max().iloc[-1]

    atr = (df["high"] - df["low"]).rolling(window).mean().iloc[-1]

    momentum = df["close"].pct_change().rolling(5).mean().iloc[-1]

    return price, support, resistance, atr, momentum

# =========================
# V44 AI ENGINE
# =========================
def engine(price, support, resistance, atr, momentum):

    rng = resistance - support

    score = 50
    reasons = []

    # =========================
    # TREND BIAS
    # =========================
    if momentum > 0:
        score += 10
        reasons.append("Bullish momentum")
        trend = "BULL"
    else:
        score -= 10
        reasons.append("Bearish momentum")
        trend = "BEAR"

    # =========================
    # BREAKOUT LOGIC
    # =========================
    breakout = price > resistance * 0.999
    breakdown = price < support * 1.001

    near_support = price <= support * 1.002
    near_resistance = price >= resistance * 0.998

    # =========================
    # SIGNAL ENGINE
    # =========================
    if breakout:
        signal = "BREAKOUT BUY"
        direction = "BUY"
        entry = resistance
        sl = support
        tp = resistance + rng
        score += 30
        reasons.append("Breakout confirmed")

    elif breakdown:
        signal = "BREAKDOWN SELL"
        direction = "SELL"
        entry = support
        sl = resistance
        tp = support - rng
        score += 30
        reasons.append("Breakdown confirmed")

    elif near_support:
        signal = "SUPPORT BUY"
        direction = "BUY"
        entry = support
        sl = support - atr
        tp = resistance
        score += 20
        reasons.append("Liquidity at support")

    elif near_resistance:
        signal = "RESISTANCE SELL"
        direction = "SELL"
        entry = resistance
        sl = resistance + atr
        tp = support
        score += 20
        reasons.append("Liquidity at resistance")

    else:
        signal = "NO EDGE"
        direction = "WAIT"
        entry = price
        sl = price - atr
        tp = price + atr
        score -= 5
        reasons.append("Market neutral")

    # =========================
    # RR SCORE IMPACT
    # =========================
    risk = abs(entry - sl)
    reward = abs(tp - entry)

    rr = round(reward / risk, 2) if risk != 0 else 0

    if rr > 2:
        score += 15
        reasons.append("High RR setup")
    elif rr < 1.2:
        score -= 10
        reasons.append("Poor RR")

    # =========================
    # AI PROBABILITY MODEL
    # =========================
    buy_prob = max(0, min(100, score + np.random.randint(-5, 5)))
    sell_prob = 100 - buy_prob

    score = max(0, min(100, score))

    return signal, direction, entry, sl, tp, rr, score, buy_prob, sell_prob, reasons, trend

# =========================
# RUN SCAN
# =========================
results = []
charts = {}

for coin in selected:

    df = load_data(coin)

    if df is None or df.empty:
        continue

    price, support, resistance, atr, momentum = structure(df)

    signal, direction, entry, sl, tp, rr, score, buy_prob, sell_prob, reasons, trend = engine(
        price, support, resistance, atr, momentum
    )

    charts[coin] = df

    results.append({
        "Coin": coin,
        "Signal": signal,
        "Direction": direction,
        "Price": price,
        "Entry": entry,
        "SL": sl,
        "TP": tp,
        "RR": rr,
        "Score": score,
        "Buy%": buy_prob,
        "Sell%": sell_prob,
        "Trend": trend,
        "Reasons": reasons
    })

df = pd.DataFrame(results).sort_values("Score", ascending=False)

# =========================
# KPI
# =========================
c1, c2, c3 = st.columns(3)

c1.metric("🟢 BUY % AVG", round(df["Buy%"].mean(), 2))
c2.metric("🔴 SELL % AVG", round(df["Sell%"].mean(), 2))
c3.metric("🔥 TOP SCORE", df["Score"].max())

# =========================
# AI RANKING
# =========================
st.subheader("🤖 V44 AI MARKET RANKING")

for i, r in df.iterrows():

    cls = "buy" if r["Direction"] == "BUY" else "sell"

    st.markdown(f"""
    <div class="card {cls}">

    <h3>{r['Coin']} – {r['Direction']} ({r['Trend']})</h3>

    <p>{r['Signal']}</p>

    <hr>

    💰 Price: {r['Price']}<br>
    🎯 Entry: {r['Entry']}<br>
    🛑 SL: {r['SL']}<br>
    📈 TP: {r['TP']}<br>

    <hr>

    📊 RR: {r['RR']}<br>
    🧠 Score: {r['Score']}<br>
    🤖 BUY PROB: {r['Buy%']}%<br>
    🤖 SELL PROB: {r['Sell%']}%

    <hr>

    🧠 AI REASONS:<br>
    {"<br>".join(["- " + x for x in r["Reasons"]])}

    </div>
    """, unsafe_allow_html=True)
