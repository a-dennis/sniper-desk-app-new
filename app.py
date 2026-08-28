"""
QuantBreakout Scanner Terminal
-------------------------------
Streamlit app implementing MASTER_PRODUCTION_ARCHITECTURE.txt against a
Kotak Neo live data feed (prices/volume/candles) + yfinance (fundamentals).

Run locally:
    streamlit run app.py

Deploy: push this folder to your GitHub repo, then point Streamlit
Community Cloud at it. See README.md for the secrets you need to configure.
"""

from __future__ import annotations

import datetime as dt
import time

import streamlit as st

from kotak_client import (
    IST,
    Instrument,
    get_intraday_candles,
    get_live_quotes,
    get_nse_equity_universe,
    market_is_open,
)
from fundamentals import get_fundamentals
from indicators import (
    ema_cross_check,
    momentum_check,
    supertrend_check,
    volume_surge_check,
    vwap_check,
)

CAPITAL = 15_000
MAX_SCAN_UNIVERSE = 250  # see README "Tuning the scan pool" before raising this

st.set_page_config(page_title="QuantBreakout Scanner", layout="wide", page_icon="⚡")

# ---------------------------------------------------------------- styling --
st.markdown(
    """
    <style>
    .stApp { background-color: #e0f2fe; }
    .qb-panel {
        background-color: #bae6fd;
        border: 1px solid #0284c7;
        border-radius: 10px;
        padding: 16px;
    }
    .qb-text { color: #0f172a; }
    .qb-gold-banner {
        width: 100%;
        background: linear-gradient(180deg, #fef08a 0%, #fef9c3 100%);
        border: 3px solid #ca8a04;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
    }
    .qb-badge-pass { color: #ffffff; background:#15803d; padding:3px 10px; border-radius:6px; font-weight:600; }
    .qb-badge-fail { color: #ffffff; background:#b91c1c; padding:3px 10px; border-radius:6px; font-weight:600; }
    .qb-badge-unavail { color: #0f172a; background:#cbd5e1; padding:3px 10px; border-radius:6px; font-weight:600; }
    thead tr th { background-color: #ffffff !important; color:#0f172a !important; }
    @media (max-width: 768px) {
        .qb-panel { padding: 10px; }
        html, body, [class*="css"] { font-size: 13px; }
        .stDataFrame { overflow-x: auto; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- state ----
if "pointer" not in st.session_state:
    st.session_state.pointer = 0
if "manual_symbol" not in st.session_state:
    st.session_state.manual_symbol = None
if "last_snapshot" not in st.session_state:
    st.session_state.last_snapshot = None  # cached values for after-hours display


def badge(verdict: str) -> str:
    label = {"pass": "PASS", "fail": "FAIL", "unavailable": "DATA UNAVAILABLE"}[verdict]
    cls = {"pass": "qb-badge-pass", "fail": "qb-badge-fail", "unavailable": "qb-badge-unavail"}[verdict]
    return f'<span class="{cls}">{label}</span>'


def bounded(value: float | None, lo: float, hi: float) -> str:
    if value is None:
        return "unavailable"
    return "pass" if lo <= value <= hi else "fail"


def gte(value: float | None, threshold: float) -> str:
    if value is None:
        return "unavailable"
    return "pass" if value >= threshold else "fail"


def lte(value: float | None, threshold: float) -> str:
    if value is None:
        return "unavailable"
    return "pass" if value <= threshold else "fail"


@st.cache_data(ttl=60, show_spinner=False)
def build_scan_pool() -> list[Instrument]:
    """Full official universe, trimmed to a manageable live-polling pool.
    See README for why we don't poll all ~2,300 NSE equities every 10s."""
    universe = get_nse_equity_universe()
    return universe[:MAX_SCAN_UNIVERSE]


def evaluate_symbol(inst: Instrument) -> dict:
    quotes = get_live_quotes([inst]).get(inst.trading_symbol, {})
    ltp = quotes.get("ltp", 0.0)
    volume = quotes.get("volume", 0)
    candles = get_intraday_candles(inst.instrument_token)
    fund = get_fundamentals(inst.trading_symbol)

    rows = []

    v = fund["pe"]
    rows.append(("Price-to-Earnings Ratio", lte(v, 25),
                  f"{v:.2f}" if v is not None else "LIVE FUNDAMENTAL SOURCE REQUIRED"))

    rows.append(("CMP Allocation Bounds", bounded(ltp, 50, 500),
                  f"₹{ltp:.2f} (₹50 - ₹500)"))

    v = fund["beta"]
    rows.append(("Volatility Shield / Beta", bounded(v, 0.60, 1.20),
                  f"{v:.2f}" if v is not None else "LIVE FUNDAMENTAL SOURCE REQUIRED"))

    v = fund["market_cap_cr"]
    rows.append(("Free-Float Market Cap", gte(v, 5000),
                  f"₹{v:,.0f} Cr" if v is not None else "LIVE FUNDAMENTAL SOURCE REQUIRED"))

    rows.append(("Volume Liquidity Depth Floor", gte(volume, 500_000),
                  f"{volume:,} (Min: 500,000)"))

    v = fund["debt_to_equity"]
    rows.append(("Debt-to-Equity", "unavailable" if v is None else "pass",
                  f"{v:.2f}" if v is not None else "LIVE FUNDAMENTAL SOURCE REQUIRED"))

    verdict, detail = vwap_check(candles, ltp)
    rows.append(("VWAP Support Anchoring", verdict, detail))

    verdict, detail = ema_cross_check(candles)
    rows.append(("EMA 9 / 21 Cross", verdict, detail))

    verdict, detail = supertrend_check(candles)
    rows.append(("Supertrend Speed Engine", verdict, detail))

    verdict, detail = volume_surge_check(candles)
    rows.append(("Institutional Volume Mean Surge", verdict, detail))

    verdict, detail = momentum_check(candles)
    rows.append(("Intraday Momentum Acceleration", verdict, detail))

    return {
        "symbol": inst.trading_symbol,
        "ltp": ltp,
        "change": quotes.get("change", 0.0),
        "change_pct": quotes.get("change_pct", 0.0),
        "volume": volume,
        "rows": rows,
    }


def pick_winner(pool: list[Instrument]) -> dict:
    """Highest live traded volume among the scan pool = 'breakout winner'."""
    quotes = get_live_quotes(pool)
    if not quotes:
        return evaluate_symbol(pool[0])
    top_symbol = max(quotes, key=lambda s: quotes[s]["volume"])
    top_inst = next(i for i in pool if i.trading_symbol == top_symbol)
    return evaluate_symbol(top_inst)


# ---------------------------------------------------------------- header ---
left, right = st.columns([3, 1])
with left:
    st.markdown("### ⚡ QUANTBREAKOUT")
    st.caption("Real-Time NSE Scanner — Powered by Kotak Neo")
with right:
    if st.button("🔄 REFRESH NOW", use_container_width=True):
        st.cache_data.clear()

is_open = market_is_open()
status_cols = st.columns(4)
status_cols[0].metric("MARKET STATUS", "🟢 LIVE" if is_open else "🔴 CLOSED")
status_cols[1].metric("LAST UPDATED", dt.datetime.now(IST).strftime("%H:%M:%S"))
status_cols[2].metric("SCAN POOL", f"{MAX_SCAN_UNIVERSE} EQUITIES")
status_cols[3].metric("SERVER TIME (IST)", dt.datetime.now(IST).strftime("%H:%M:%S"))

if not is_open:
    st.info("Market is closed — showing the last fetched values from the most recent session, not live polling.")

try:
    pool = build_scan_pool()
except Exception as e:
    st.error(f"Could not load the NSE universe from Kotak Neo: {e}")
    st.stop()

# ---------------------------------------------------------- current pick ---
if st.session_state.manual_symbol:
    inst = next((i for i in pool if i.trading_symbol == st.session_state.manual_symbol), None)
    if inst is None:
        st.warning(f"'{st.session_state.manual_symbol}' not found in the scan pool — showing auto winner instead.")
        st.session_state.manual_symbol = None

if st.session_state.manual_symbol:
    snapshot = evaluate_symbol(inst)
elif is_open or st.session_state.last_snapshot is None:
    snapshot = pick_winner(pool)
    st.session_state.last_snapshot = snapshot
else:
    snapshot = st.session_state.last_snapshot

# ---------------------------------------------------------------- banner ---
pass_count = sum(1 for _, v, _ in snapshot["rows"] if v == "pass")
fail_count = sum(1 for _, v, _ in snapshot["rows"] if v == "fail")
unavail_count = sum(1 for _, v, _ in snapshot["rows"] if v == "unavailable")
score = round(100 * pass_count / len(snapshot["rows"]), 1)

st.markdown(
    f"""
    <div class="qb-gold-banner">
        <span style="background:#ca8a04;color:white;padding:4px 14px;border-radius:16px;">⭐ REAL-TIME QUANT BREAKOUT WINNER</span>
        <h1 style="margin:8px 0 0 0;">{snapshot['symbol']}</h1>
        <h2 style="color:#15803d;margin:4px 0;">₹{snapshot['ltp']:,.2f}</h2>
        <p>Change: {snapshot['change']:+.2f} ({snapshot['change_pct']:+.2f}%) &nbsp;|&nbsp; Volume: {snapshot['volume']:,} &nbsp;|&nbsp; Score: {score}%</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------- nav + override -
nav1, nav2 = st.columns(2)
current_symbols = [i.trading_symbol for i in pool]
try:
    idx = current_symbols.index(snapshot["symbol"])
except ValueError:
    idx = 0

if nav1.button("❬ PREVIOUS ASSET", use_container_width=True):
    st.session_state.manual_symbol = current_symbols[(idx - 1) % len(current_symbols)]
    st.rerun()
if nav2.button("NEXT ASSET ❭", use_container_width=True):
    st.session_state.manual_symbol = current_symbols[(idx + 1) % len(current_symbols)]
    st.rerun()

manual_input = st.text_input("🔍 MANUAL CHECK OVERRIDE FIELD", placeholder="e.g. SBIN, INFY, ICICIBANK")
if manual_input:
    st.session_state.manual_symbol = manual_input.strip().upper()
    st.rerun()

# ---------------------------------------------------------------- matrix ---
col_matrix, col_summary = st.columns([3, 1])

with col_matrix:
    st.markdown("#### 📋 11-Parameter Strategy Matrix")
    table_rows = "".join(
        f"<tr><td>{i+1}</td><td>{name}</td><td>{badge(verdict)}</td><td>{detail}</td></tr>"
        for i, (name, verdict, detail) in enumerate(snapshot["rows"])
    )
    st.markdown(
        f"""
        <table class="qb-text" style="width:100%; border-collapse:collapse;">
        <thead><tr><th>#</th><th>Parameter</th><th>Verdict</th><th>Live Metric Value</th></tr></thead>
        <tbody>{table_rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

with col_summary:
    st.markdown('<div class="qb-panel">', unsafe_allow_html=True)
    st.markdown("**📊 Live Summary**")
    st.metric("Pass Conditions", f"{pass_count} / 11")
    st.metric("Fail Conditions", f"{fail_count} / 11")
    st.metric("Data Unavailable", f"{unavail_count} / 11")
    st.metric("Matrix Score", f"{score}%")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------- position sizer -
st.markdown("#### 🧮 Position Sizing (₹15,000 Capital)")
price = snapshot["ltp"] or 0.01
shares = int(round(CAPITAL / price))
risk_unit = price * 0.008
sl = price - (risk_unit * 1.5)
tp = price + (risk_unit * 3.0)

size_cols = st.columns(4)
size_cols[0].markdown(f'<div class="qb-panel">🛒 <b>Buy Exactly</b><br><span style="font-size:1.4em;">{shares} SHARES</span></div>', unsafe_allow_html=True)
size_cols[1].markdown(f'<div class="qb-panel">🛡️ <b>Risk Unit</b><br><span style="font-size:1.4em;">₹{risk_unit:,.2f}</span></div>', unsafe_allow_html=True)
size_cols[2].markdown(f'<div class="qb-panel">🔒 <b>Stop Loss</b><br><span style="font-size:1.4em;color:#b91c1c;">₹{sl:,.2f}</span></div>', unsafe_allow_html=True)
size_cols[3].markdown(f'<div class="qb-panel">🎯 <b>Take Profit</b><br><span style="font-size:1.4em;color:#15803d;">₹{tp:,.2f}</span></div>', unsafe_allow_html=True)

st.caption(
    f"Risk per trade: ₹{risk_unit:,.2f} ({(risk_unit/price*100):.2f}%) | SL: 1.5x Risk | TP: 3.0x Risk. "
    "This is a fixed mechanical calculation from the formulas you specified, not investment advice."
)

# ---------------------------------------------------------- auto refresh --
if is_open and not st.session_state.manual_symbol:
    time.sleep(10)
    st.rerun()
