"""
QuantBreakout Scanner Terminal
-------------------------------
Streamlit app implementing MASTER_PRODUCTION_ARCHITECTURE.txt against free
Yahoo Finance data (prices/volume/candles/fundamentals).

Two-tier scanning:
  Tier 1: every 15 min, lightweight volume scan across the FULL official
          NSE equity universe (~2,000 stocks) to find the ~50 most active
          names right now.
  Tier 2: every 10 sec, full 5-signal technical analysis on that ~50-stock
          shortlist (this is what decides the winner).

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import datetime as dt
import time

import plotly.graph_objects as go
import streamlit as st

from kotak_client import (
    IST,
    Instrument,
    get_full_nse_universe,
    get_index_quotes,
    get_intraday_candles,
    get_live_quotes,
    get_tier1_shortlist,
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
from portfolio import render_portfolio_section
from signal_logger import log_signal, read_log_bytes

MIN_WINNING_SCORE = 4
SHORTLIST_SIZE = 50
ALERT_COOLDOWN_MINUTES = 15

st.set_page_config(page_title="QuantBreakout Scanner", layout="wide", page_icon="lightning")

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
    .qb-weak-banner {
        width: 100%;
        background: #e2e8f0;
        border: 3px solid #94a3b8;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
    }
    .qb-badge-pass { color: #ffffff; background:#15803d; padding:3px 10px; border-radius:6px; font-weight:600; }
    .qb-badge-fail { color: #ffffff; background:#b91c1c; padding:3px 10px; border-radius:6px; font-weight:600; }
    .qb-badge-unavail { color: #0f172a; background:#cbd5e1; padding:3px 10px; border-radius:6px; font-weight:600; }
    thead tr th { background-color: #ffffff !important; color:#0f172a !important; }
    .qb-index-strip { display:flex; gap:16px; margin-bottom:12px; }
    .qb-index-card { background:#bae6fd; border:1px solid #0284c7; border-radius:8px; padding:8px 16px; flex:1; }
    @media (max-width: 768px) {
        .qb-panel { padding: 10px; }
        html, body, [class*="css"] { font-size: 13px; }
        .stDataFrame { overflow-x: auto; }
        .qb-index-strip { flex-direction: column; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "manual_symbol" not in st.session_state:
    st.session_state.manual_symbol = None
if "last_snapshot" not in st.session_state:
    st.session_state.last_snapshot = None
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = {}


def badge(verdict):
    label = {"pass": "PASS", "fail": "FAIL", "unavailable": "DATA UNAVAILABLE"}[verdict]
    cls = {"pass": "qb-badge-pass", "fail": "qb-badge-fail", "unavailable": "qb-badge-unavail"}[verdict]
    return '<span class="' + cls + '">' + label + '</span>'


def bounded(value, lo, hi):
    if value is None:
        return "unavailable"
    return "pass" if lo <= value <= hi else "fail"


def gte(value, threshold):
    if value is None:
        return "unavailable"
    return "pass" if value >= threshold else "fail"


def lte(value, threshold):
    if value is None:
        return "unavailable"
    return "pass" if value <= threshold else "fail"


def evaluate_symbol(inst):
    quotes = get_live_quotes([inst]).get(inst.trading_symbol, {})
    ltp = quotes.get("ltp", 0.0)
    volume = quotes.get("volume", 0)
    candles = get_intraday_candles(inst.trading_symbol)
    fund = get_fundamentals(inst.trading_symbol)

    rows = []
    v = fund["pe"]
    rows.append(("Price-to-Earnings Ratio", lte(v, 25), (f"{v:.2f}" if v is not None else "LIVE FUNDAMENTAL SOURCE REQUIRED")))
    rows.append(("CMP Allocation Bounds", bounded(ltp, 50, 500), f"Rs {ltp:.2f} (Rs 50 - Rs 500)"))
    v = fund["beta"]
    rows.append(("Volatility Shield / Beta", bounded(v, 0.60, 1.20), (f"{v:.2f}" if v is not None else "LIVE FUNDAMENTAL SOURCE REQUIRED")))
    v = fund["market_cap_cr"]
    rows.append(("Free-Float Market Cap", gte(v, 5000), (f"Rs {v:,.0f} Cr" if v is not None else "LIVE FUNDAMENTAL SOURCE REQUIRED")))
    rows.append(("Volume Liquidity Depth Floor", gte(volume, 500000), f"{volume:,} (Min: 500,000)"))
    v = fund["debt_to_equity"]
    rows.append(("Debt-to-Equity", ("unavailable" if v is None else "pass"), (f"{v:.2f}" if v is not None else "LIVE FUNDAMENTAL SOURCE REQUIRED")))

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

    technical_rows = rows[6:]
    technical_score = sum(1 for row in technical_rows if row[1] == "pass")

    mcap_verdict = gte(fund["market_cap_cr"], 5000)
    safety_pass = mcap_verdict in ("pass", "unavailable")

    return {
        "symbol": inst.trading_symbol, "ltp": ltp,
        "change": quotes.get("change", 0.0), "change_pct": quotes.get("change_pct", 0.0),
        "volume": volume, "rows": rows,
        "technical_score": technical_score, "safety_pass": safety_pass,
    }


def scan_shortlist(shortlist):
    evaluations = [evaluate_symbol(inst) for inst in shortlist]
    evaluations.sort(key=lambda e: (e["technical_score"], e["volume"]), reverse=True)
    return evaluations


def pick_winner(evaluations):
    candidates = [e for e in evaluations if e["safety_pass"]] or evaluations
    best = max(candidates, key=lambda e: (e["technical_score"], e["volume"]))
    best["below_threshold"] = best["technical_score"] < MIN_WINNING_SCORE
    return best


left, right = st.columns([3, 1])
with left:
    st.markdown("### QUANTBREAKOUT")
    st.caption(f"Real-Time NSE Scanner - full universe screened, top {SHORTLIST_SIZE} tracked live")
with right:
    if st.button("REFRESH NOW", use_container_width=True):
        st.cache_data.clear()

index_quotes = get_index_quotes()
if index_quotes:
    idx_html = '<div class="qb-index-strip">'
    for name, q in index_quotes.items():
        color = "#15803d" if q["change"] >= 0 else "#b91c1c"
        sign = "+" if q["change"] >= 0 else ""
        idx_html += (
            '<div class="qb-index-card"><b>' + name + '</b><br>'
            '<span style="font-size:1.3em;">' + format(q["ltp"], ",.2f") + '</span> '
            '<span style="color:' + color + ';">' + sign + format(q["change"], ",.2f") +
            ' (' + sign + format(q["change_pct"], ".2f") + '%)</span></div>'
        )
    idx_html += "</div>"
    st.markdown(idx_html, unsafe_allow_html=True)

is_open = market_is_open()
status_cols = st.columns(4)
status_cols[0].metric("MARKET STATUS", "LIVE" if is_open else "CLOSED")
status_cols[1].metric("LAST UPDATED", dt.datetime.now(IST).strftime("%H:%M:%S"))
status_cols[2].metric("SHORTLIST SIZE", f"{SHORTLIST_SIZE} (from full NSE universe)")
status_cols[3].metric("SERVER TIME (IST)", dt.datetime.now(IST).strftime("%H:%M:%S"))

if not is_open:
    st.info("Market is closed - showing the last traded values from the most recent session.")

try:
    full_universe = get_full_nse_universe()
    shortlist = get_tier1_shortlist(full_universe, top_n=SHORTLIST_SIZE)
except Exception as e:
    st.error(f"Could not build the scan shortlist: {e}")
    st.stop()

st.caption(f"Tier 1 full-universe scan covered {len(full_universe)} NSE equities; "
           f"Tier 2 is live-tracking the {len(shortlist)} most active right now.")

if st.session_state.manual_symbol:
    inst = Instrument(trading_symbol=st.session_state.manual_symbol)
    snapshot = evaluate_symbol(inst)
    snapshot["below_threshold"] = snapshot["technical_score"] < MIN_WINNING_SCORE
    evaluations = None
elif is_open or st.session_state.last_snapshot is None:
    evaluations = scan_shortlist(shortlist)
    snapshot = pick_winner(evaluations)
    st.session_state.last_snapshot = snapshot
    if not snapshot["below_threshold"]:
        log_signal(snapshot["symbol"], snapshot["ltp"], snapshot["volume"],
                   snapshot["technical_score"],
                   round(100 * sum(1 for r in snapshot["rows"] if r[1] == "pass") / 11, 1), IST)
else:
    snapshot = st.session_state.last_snapshot
    evaluations = None

if not st.session_state.manual_symbol and snapshot["technical_score"] == 5:
    now = dt.datetime.now(IST)
    last_time = st.session_state.last_alert_time.get(snapshot["symbol"])
    if last_time is None or (now - last_time).total_seconds() > ALERT_COOLDOWN_MINUTES * 60:
        st.toast(f"PERFECT SIGNAL: {snapshot['symbol']} just hit 5/5!", icon="🎯")
        st.session_state.last_alert_time[snapshot["symbol"]] = now

pass_count = sum(1 for row in snapshot["rows"] if row[1] == "pass")
fail_count = sum(1 for row in snapshot["rows"] if row[1] == "fail")
unavail_count = sum(1 for row in snapshot["rows"] if row[1] == "unavailable")
score = round(100 * pass_count / len(snapshot["rows"]), 1)

banner_class = "qb-weak-banner" if snapshot.get("below_threshold") else "qb-gold-banner"
banner_label = ("BEST AVAILABLE (below 4/5 threshold)" if snapshot.get("below_threshold")
                else "REAL-TIME QUANT BREAKOUT WINNER")
banner_html = (
    '<div class="' + banner_class + '">'
    '<span style="background:#ca8a04;color:white;padding:4px 14px;border-radius:16px;">' + banner_label + '</span>'
    '<h1 style="margin:8px 0 0 0;">' + snapshot["symbol"] + '</h1>'
    '<h2 style="color:#15803d;margin:4px 0;">Rs ' + format(snapshot["ltp"], ",.2f") + '</h2>'
    '<p>Change: ' + format(snapshot["change"], "+.2f") + ' (' + format(snapshot["change_pct"], "+.2f") + '%) | '
    'Volume: ' + format(snapshot["volume"], ",") + ' | Technical Score: ' + str(snapshot["technical_score"]) + '/5</p>'
    '</div>'
)
st.markdown(banner_html, unsafe_allow_html=True)

if snapshot.get("below_threshold") and not st.session_state.manual_symbol:
    st.warning(f"No stock in the shortlist currently meets the {MIN_WINNING_SCORE}/5 minimum bar. Showing the closest match.")

manual_input = st.text_input("MANUAL CHECK OVERRIDE FIELD", placeholder="e.g. SBIN, INFY, ICICIBANK")
if manual_input:
    st.session_state.manual_symbol = manual_input.strip().upper()
    st.rerun()
if st.session_state.manual_symbol and st.button("Back to auto-scan"):
    st.session_state.manual_symbol = None
    st.rerun()

if evaluations:
    st.markdown("#### Top 5 Ranked Shortlist")
    top5 = evaluations[:5]
    rank_html = ('<table class="qb-text" style="width:100%; border-collapse:collapse;">'
                 '<thead><tr><th>Rank</th><th>Symbol</th><th>LTP</th><th>Technical Score</th><th>Volume</th></tr></thead><tbody>')
    for rank, e in enumerate(top5, start=1):
        rank_html += ("<tr><td>" + str(rank) + "</td><td>" + e["symbol"] + "</td><td>Rs " +
                      format(e["ltp"], ",.2f") + "</td><td>" + str(e["technical_score"]) + "/5</td><td>" +
                      format(e["volume"], ",") + "</td></tr>")
    rank_html += "</tbody></table>"
    st.markdown(rank_html, unsafe_allow_html=True)

st.markdown("#### Live Intraday Chart - " + snapshot["symbol"])
chart_candles = get_intraday_candles(snapshot["symbol"])
if chart_candles is not None and not chart_candles.empty:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=chart_candles.index, open=chart_candles["open"], high=chart_candles["high"],
                                  low=chart_candles["low"], close=chart_candles["close"], name=snapshot["symbol"]))
    typical = (chart_candles["high"] + chart_candles["low"] + chart_candles["close"]) / 3
    vwap_line = (typical * chart_candles["volume"]).cumsum() / chart_candles["volume"].cumsum().replace(0, 1)
    fig.add_trace(go.Scatter(x=chart_candles.index, y=vwap_line, mode="lines", name="VWAP",
                              line=dict(color="#0284c7", width=2)))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False,
                       plot_bgcolor="#e0f2fe", paper_bgcolor="#e0f2fe")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough intraday candle data to draw a chart for this stock right now.")

col_matrix, col_summary = st.columns([3, 1])
with col_matrix:
    st.markdown("#### 11-Parameter Strategy Matrix")
    table_rows = ""
    i = 0
    for name, verdict, detail in snapshot["rows"]:
        i += 1
        table_rows += "<tr><td>" + str(i) + "</td><td>" + name + "</td><td>" + badge(verdict) + "</td><td>" + detail + "</td></tr>"
    table_html = ('<table class="qb-text" style="width:100%; border-collapse:collapse;">'
                  '<thead><tr><th>#</th><th>Parameter</th><th>Verdict</th><th>Live Metric Value</th></tr></thead>'
                  '<tbody>' + table_rows + '</tbody></table>')
    st.markdown(table_html, unsafe_allow_html=True)

with col_summary:
    st.markdown('<div class="qb-panel">', unsafe_allow_html=True)
    st.markdown("**Live Summary**")
    st.metric("Pass Conditions", f"{pass_count} / 11")
    st.metric("Fail Conditions", f"{fail_count} / 11")
    st.metric("Data Unavailable", f"{unavail_count} / 11")
    st.metric("Matrix Score", f"{score}%")
    st.metric("Intraday Technical Score", f"{snapshot['technical_score']} / 5")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("#### Position Sizing")
capital = st.number_input("Your trading capital (Rs)", min_value=1000, step=1000, value=15000)
price = snapshot["ltp"] or 0.01
shares = int(round(capital / price))
risk_unit = price * 0.008
sl = price - (risk_unit * 1.5)
tp = price + (risk_unit * 3.0)

size_cols = st.columns(4)
size_cols[0].markdown('<div class="qb-panel">Buy Exactly<br><span style="font-size:1.4em;">' + str(shares) + ' SHARES</span></div>', unsafe_allow_html=True)
size_cols[1].markdown('<div class="qb-panel">Risk Unit<br><span style="font-size:1.4em;">Rs ' + format(risk_unit, ",.2f") + '</span></div>', unsafe_allow_html=True)
size_cols[2].markdown('<div class="qb-panel">Stop Loss<br><span style="font-size:1.4em;color:#b91c1c;">Rs ' + format(sl, ",.2f") + '</span></div>', unsafe_allow_html=True)
size_cols[3].markdown('<div class="qb-panel">Take Profit<br><span style="font-size:1.4em;color:#15803d;">Rs ' + format(tp, ",.2f") + '</span></div>', unsafe_allow_html=True)

risk_pct = risk_unit / price * 100
st.caption("Risk per trade: Rs " + format(risk_unit, ",.2f") + " (" + format(risk_pct, ".2f") +
           "%) | SL: 1.5x Risk | TP: 3.0x Risk. Not investment advice.")

st.divider()
render_portfolio_section(get_live_quotes, Instrument)

st.divider()
log_bytes = read_log_bytes()
if log_bytes:
    st.download_button("Download signal_log.csv", log_bytes, file_name="signal_log.csv", mime="text/csv")

if is_open and not st.session_state.manual_symbol:
    time.sleep(10)
    st.rerun()
