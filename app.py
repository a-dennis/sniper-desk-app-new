"""
QuantBreakout Scanner Terminal
-------------------------------
Multi-segment scanner (NSE Equities / Commodities / Crypto) built on free
Yahoo Finance data. Same 5-signal technical engine (VWAP, EMA 9/21 cross,
Supertrend, volume surge, momentum) powers all three segments; equity-only
rules (price band, market cap floor, fundamentals) only apply to NSE.

NSE Equities: two-tier scan across the full ~2,000-stock official universe.
Commodities: fixed list of global futures used as a DIRECTIONAL PROXY for
  MCX movement (COMEX/NYMEX prices in USD, not exact MCX/INR contract
  prices) -- good for spotting momentum to time a real MCX entry, not for
  precise position sizing against actual MCX contract specs.
Crypto: fixed list of major coins, real global USD prices, trades 24/7.

Commodity/crypto prices are converted from USD to Rupees using a live
USD/INR rate so position sizing against a Rupee capital amount is
meaningful (this is a display/sizing conversion only -- currency-invariant
technical checks like EMA-cross or momentum are unaffected either way).

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
    get_commodities_universe,
    get_crypto_universe,
    get_full_nse_universe,
    get_index_quotes,
    get_intraday_candles,
    get_live_quotes,
    get_tier1_shortlist,
    get_usdinr_rate,
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
from news import fetch_news, classify_sentiment, aggregate_sentiment
from backtest_engine import run_symbol_backtest

MIN_WINNING_SCORE = 4
SHORTLIST_SIZE = 25
ALERT_COOLDOWN_MINUTES = 15

SEGMENTS = ["NSE Equities", "Commodities (Global Proxy)", "Crypto"]
UNIT_LABEL = {"NSE Equities": "SHARES", "Commodities (Global Proxy)": "UNITS (proxy)", "Crypto": "COINS/UNITS"}
NEWS_QUERY_SUFFIX = {"NSE Equities": "share price NSE", "Commodities (Global Proxy)": "price commodity market news",
                     "Crypto": "cryptocurrency price news"}

st.set_page_config(page_title="QuantBreakout Scanner", layout="wide", page_icon="lightning")

st.markdown(
    """
    <style>
    .stApp { background-color: #eff6ff; }
    .qb-panel {
        background-color: #ffffff;
        border: 1px solid #bae6fd;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(2,132,199,0.08);
    }
    .qb-text { color: #0f172a; }
    .qb-badge-pass { color: #ffffff; background:#15803d; padding:3px 10px; border-radius:6px; font-weight:600; }
    .qb-badge-fail { color: #ffffff; background:#b91c1c; padding:3px 10px; border-radius:6px; font-weight:600; }
    .qb-badge-unavail { color: #0f172a; background:#cbd5e1; padding:3px 10px; border-radius:6px; font-weight:600; }
    thead tr th { background-color: #0284c7 !important; color:#ffffff !important; padding:8px !important; }
    tbody tr td { padding:6px 8px !important; border-bottom:1px solid #e0f2fe; }
    .qb-stat-strip { display:flex; gap:14px; margin-bottom:14px; flex-wrap:wrap; }
    .qb-stat-card {
        background:#ffffff; border:1px solid #bae6fd; border-radius:12px;
        padding:12px 18px; flex:1; min-width:150px;
        box-shadow: 0 1px 3px rgba(2,132,199,0.08);
    }
    .qb-stat-label { font-size:0.75em; color:#64748b; font-weight:600; letter-spacing:0.03em; }
    .qb-stat-value { font-size:1.4em; font-weight:700; color:#0f172a; }
    @media (max-width: 768px) {
        .qb-panel { padding: 10px; }
        html, body, [class*="css"] { font-size: 13px; }
        .stDataFrame { overflow-x: auto; }
        .qb-stat-strip { flex-direction: column; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- segment --
if "segment" not in st.session_state:
    st.session_state.segment = SEGMENTS[0]

segment = st.selectbox("📂 Select Segment", SEGMENTS,
                        index=SEGMENTS.index(st.session_state.segment))
if segment != st.session_state.segment:
    # Switching segments invalidates anything tied to the old one's symbols.
    st.session_state.segment = segment
    st.session_state.manual_symbol = None
    st.session_state.top10_pointer = 0
    st.session_state.bt_hunt_result = None
    st.session_state.bt_hunt_checked = []
    st.session_state.backtest_results = {}
    st.rerun()

if "manual_symbol" not in st.session_state:
    st.session_state.manual_symbol = None
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = {}
if "backtest_results" not in st.session_state:
    st.session_state.backtest_results = {}


def render_backtest_button(display_symbol, yahoo_ticker, key_suffix=""):
    """Renders a Backtest button + cached result (if any) for a symbol."""
    if st.button("🧪 Backtest this stock", key="backtest_btn_" + display_symbol + key_suffix):
        with st.spinner(f"Backtesting {display_symbol} against the last 7 days of real data..."):
            result = run_symbol_backtest(yahoo_ticker, display_symbol=display_symbol)
        st.session_state.backtest_results[display_symbol] = result

    result = st.session_state.backtest_results.get(display_symbol)
    if result:
        if result["verdict"] == "PASS":
            st.success(f"✅ BACKTEST PASS — {result['detail']}")
        elif result["verdict"] == "FAIL":
            st.error(f"❌ BACKTEST FAIL — {result['detail']}")
        else:
            st.warning(f"⚠️ INSUFFICIENT DATA — {result['detail']}")


def stat_card(label, value, color="#0f172a"):
    return ('<div class="qb-stat-card"><div class="qb-stat-label">' + label + '</div>'
            '<div class="qb-stat-value" style="color:' + color + ';">' + value + '</div></div>')


def badge(verdict):
    label = {"pass": "PASS", "fail": "FAIL", "unavailable": "DATA UNAVAILABLE"}[verdict]
    cls = {"pass": "qb-badge-pass", "fail": "qb-badge-fail", "unavailable": "qb-badge-unavail"}[verdict]
    return '<span class="' + cls + '">' + label + '</span>'


def _safe_float(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:
        return None
    return f


def bounded(value, lo, hi):
    value = _safe_float(value)
    if value is None:
        return "unavailable"
    return "pass" if lo <= value <= hi else "fail"


def gte(value, threshold):
    value = _safe_float(value)
    if value is None:
        return "unavailable"
    return "pass" if value >= threshold else "fail"


def lte(value, threshold):
    value = _safe_float(value)
    if value is None:
        return "unavailable"
    return "pass" if value <= threshold else "fail"


def fmt_or_msg(value, template="{:.2f}"):
    safe = _safe_float(value)
    if safe is None:
        return "LIVE FUNDAMENTAL SOURCE REQUIRED"
    return template.format(safe)


def evaluate_symbol(inst, segment):
    is_equity = segment == "NSE Equities"
    quotes = get_live_quotes([inst]).get(inst.trading_symbol, {})
    ltp = quotes.get("ltp", 0.0)
    volume = quotes.get("volume", 0)
    change = quotes.get("change", 0.0)
    change_pct = quotes.get("change_pct", 0.0)
    candles = get_intraday_candles(inst.yahoo_ticker)

    if not is_equity:
        # Convert USD -> INR for display/sizing. Currency-invariant checks
        # (EMA cross, momentum direction, etc.) give identical pass/fail
        # results either way, so converting here keeps everything downstream
        # (matrix numbers, chart, position sizing) consistently in Rupees.
        rate = get_usdinr_rate()
        if not candles.empty:
            candles = candles.copy()
            for col in ("open", "high", "low", "close"):
                candles[col] = candles[col] * rate
        ltp = ltp * rate
        change = change * rate
        # change_pct is a ratio -- unaffected by currency conversion

    rows = []
    if is_equity:
        fund = get_fundamentals(inst.trading_symbol)
        v = fund["pe"]
        rows.append(("Price-to-Earnings Ratio", lte(v, 25), fmt_or_msg(v)))
        rows.append(("CMP Allocation Bounds", bounded(ltp, 50, 500), f"Rs {ltp:.2f} (Rs 50 - Rs 500)"))
        v = fund["beta"]
        rows.append(("Volatility Shield / Beta", bounded(v, 0.60, 1.20), fmt_or_msg(v)))
        v = fund["market_cap_cr"]
        rows.append(("Free-Float Market Cap", gte(v, 5000), "Rs " + fmt_or_msg(v, "{:,.0f}") + " Cr" if _safe_float(v) is not None else fmt_or_msg(v)))
        rows.append(("Volume Liquidity Depth Floor", gte(volume, 500000), f"{volume:,} (Min: 500,000)"))
        v = fund["debt_to_equity"]
        v_safe = _safe_float(v)
        rows.append(("Debt-to-Equity", ("unavailable" if v_safe is None else "pass"), fmt_or_msg(v)))

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

    technical_rows = rows[6:] if is_equity else rows
    technical_score = sum(1 for row in technical_rows if row[1] == "pass")

    if is_equity:
        mcap_verdict = gte(fund["market_cap_cr"], 5000)
        safety_pass = mcap_verdict in ("pass", "unavailable")
    else:
        safety_pass = ltp is not None and ltp > 0

    return {
        "symbol": inst.trading_symbol, "yahoo_ticker": inst.yahoo_ticker, "ltp": ltp,
        "change": change, "change_pct": change_pct,
        "volume": volume, "rows": rows,
        "technical_score": technical_score, "safety_pass": safety_pass,
    }


def scan_shortlist(shortlist, segment):
    evaluations = [evaluate_symbol(inst, segment) for inst in shortlist]
    evaluations.sort(key=lambda e: (e["technical_score"], e["volume"]), reverse=True)
    return evaluations


def compact_card(badge_text, badge_color, badge_bg, symbol, price, border_color, bg_gradient,
                  stat1_label, stat1_value, stat1_color,
                  stat2_label, stat2_value, stat2_color,
                  stat3_label, stat3_value, stat3_color):
    return (
        '<div style="max-width:480px;margin:0 auto 16px auto;border:2px solid ' + border_color + ';'
        'border-radius:16px;padding:18px;text-align:center;background:' + bg_gradient + ';'
        'box-shadow:0 4px 12px rgba(0,0,0,0.08);">'
        '<span style="background:' + badge_bg + ';color:' + badge_color + ';padding:3px 12px;'
        'border-radius:14px;font-size:0.72em;font-weight:700;">' + badge_text + '</span>'
        '<h2 style="margin:8px 0 0 0;">' + symbol + '</h2>'
        '<div style="font-size:1.5em;font-weight:700;color:#0f172a;margin:2px 0 10px 0;">Rs ' + price + '</div>'
        '<div style="display:flex;gap:8px;">'
        '<div style="flex:1;background:#ffffffaa;border-radius:8px;padding:6px 4px;">'
        '<div style="font-size:0.65em;color:#64748b;font-weight:600;">' + stat1_label + '</div>'
        '<div style="font-weight:700;color:' + stat1_color + ';">' + stat1_value + '</div></div>'
        '<div style="flex:1;background:#ffffffaa;border-radius:8px;padding:6px 4px;">'
        '<div style="font-size:0.65em;color:#64748b;font-weight:600;">' + stat2_label + '</div>'
        '<div style="font-weight:700;color:' + stat2_color + ';">' + stat2_value + '</div></div>'
        '<div style="flex:1;background:#ffffffaa;border-radius:8px;padding:6px 4px;">'
        '<div style="font-size:0.65em;color:#64748b;font-weight:600;">' + stat3_label + '</div>'
        '<div style="font-weight:700;color:' + stat3_color + ';">' + stat3_value + '</div></div>'
        '</div></div>'
    )


def pick_winner(evaluations):
    candidates = [e for e in evaluations if e["safety_pass"]] or evaluations
    best = max(candidates, key=lambda e: (e["technical_score"], e["volume"]))
    best["below_threshold"] = best["technical_score"] < MIN_WINNING_SCORE
    return best


def build_universe_and_shortlist(segment):
    """Returns (full_universe, shortlist, universe_caption)."""
    if segment == "NSE Equities":
        full_universe = get_full_nse_universe()
        shortlist = get_tier1_shortlist(full_universe, top_n=SHORTLIST_SIZE)
        caption = (f"Tier 1 full-universe scan covered {len(full_universe)} NSE equities; "
                   f"Tier 2 is tracking the {len(shortlist)} most active right now.")
        return full_universe, shortlist, caption
    elif segment == "Commodities (Global Proxy)":
        shortlist = get_commodities_universe()
        return shortlist, shortlist, f"Tracking {len(shortlist)} global commodity proxies (COMEX/NYMEX, USD->INR converted)."
    else:
        shortlist = get_crypto_universe()
        return shortlist, shortlist, f"Tracking {len(shortlist)} major cryptocurrencies (24/7, USD->INR converted)."


def segment_is_open(segment):
    if segment == "NSE Equities":
        return market_is_open()
    if segment == "Crypto":
        return True  # trades 24/7
    return dt.datetime.now(IST).weekday() < 5  # commodities: rough weekday approximation


# ---------------------------------------------------------------- header ---
left, right = st.columns([3, 1])
with left:
    st.markdown("### ⚡ QUANTBREAKOUT")
    st.caption(f"Real-Time Scanner — {segment}")
with right:
    if st.button("🔄 REFRESH NOW", use_container_width=True):
        st.cache_data.clear()

index_quotes = get_index_quotes()
is_open = segment_is_open(segment)

strip_html = '<div class="qb-stat-strip">'
if segment == "NSE Equities":
    for name, q in index_quotes.items():
        color = "#15803d" if q["change"] >= 0 else "#b91c1c"
        sign = "+" if q["change"] >= 0 else ""
        strip_html += stat_card(name, format(q["ltp"], ",.2f") + " (" + sign + format(q["change_pct"], ".2f") + "%)", color)
strip_html += stat_card("MARKET STATUS", "🟢 LIVE" if is_open else "🔴 CLOSED", "#15803d" if is_open else "#b91c1c")
strip_html += stat_card("SERVER TIME (IST)", dt.datetime.now(IST).strftime("%H:%M:%S"))
if segment != "NSE Equities":
    strip_html += stat_card("USD/INR RATE", format(get_usdinr_rate(), ",.2f"))
strip_html += "</div>"
st.markdown(strip_html, unsafe_allow_html=True)

if not is_open:
    st.info("Market is closed — showing the last completed session's data.")
if segment == "Commodities (Global Proxy)":
    st.caption("⚠️ Directional reference only — global COMEX/NYMEX proxy prices, not exact MCX contract prices.")

try:
    full_universe, shortlist, universe_caption = build_universe_and_shortlist(segment)
except Exception as e:
    st.error(f"Could not build the scan shortlist: {e}")
    st.stop()

st.caption(universe_caption)

# ---------------------------------------------------------- snapshot -------
if st.session_state.manual_symbol:
    match = next((i for i in shortlist if i.trading_symbol == st.session_state.manual_symbol), None)
    inst = match or Instrument(trading_symbol=st.session_state.manual_symbol)
    snapshot = evaluate_symbol(inst, segment)
    snapshot["below_threshold"] = snapshot["technical_score"] < MIN_WINNING_SCORE
    evaluations = None
else:
    evaluations = scan_shortlist(shortlist, segment)
    snapshot = pick_winner(evaluations)
    if not snapshot["below_threshold"]:
        log_signal(snapshot["symbol"], snapshot["ltp"], snapshot["volume"],
                   snapshot["technical_score"],
                   round(100 * sum(1 for r in snapshot["rows"] if r[1] == "pass") / len(snapshot["rows"]), 1), IST)

if not st.session_state.manual_symbol and snapshot["technical_score"] == 5:
    now = dt.datetime.now(IST)
    last_time = st.session_state.last_alert_time.get(snapshot["symbol"])
    if last_time is None or (now - last_time).total_seconds() > ALERT_COOLDOWN_MINUTES * 60:
        st.toast(f"PERFECT SIGNAL: {snapshot['symbol']} just hit 5/5!", icon="🎯")
        st.session_state.last_alert_time[snapshot["symbol"]] = now

pass_count = sum(1 for row in snapshot["rows"] if row[1] == "pass")
fail_count = sum(1 for row in snapshot["rows"] if row[1] == "fail")
unavail_count = sum(1 for row in snapshot["rows"] if row[1] == "unavailable")
total_rows = len(snapshot["rows"])
score = round(100 * pass_count / total_rows, 1)

# ---------------------------------------------------------- nav + search ---
shortlist_symbols = [i.trading_symbol for i in shortlist]
nav1, nav2, _ = st.columns([1, 1, 4])
try:
    idx = shortlist_symbols.index(snapshot["symbol"])
except ValueError:
    idx = 0

if nav1.button("❬ Prev", disabled=len(shortlist_symbols) < 2):
    st.session_state.manual_symbol = shortlist_symbols[(idx - 1) % len(shortlist_symbols)]
    st.rerun()
if nav2.button("Next ❭", disabled=len(shortlist_symbols) < 2):
    st.session_state.manual_symbol = shortlist_symbols[(idx + 1) % len(shortlist_symbols)]
    st.rerun()

with st.form("manual_search_form", clear_on_submit=False):
    sc1, sc2 = st.columns([4, 1])
    placeholder = "e.g. SBIN, INFY, ICICIBANK" if segment == "NSE Equities" else "e.g. " + shortlist_symbols[0]
    manual_input = sc1.text_input("🔍 MANUAL CHECK OVERRIDE FIELD", placeholder=placeholder,
                                   label_visibility="collapsed")
    search_clicked = sc2.form_submit_button("🔍 Search", use_container_width=True)
    if search_clicked and manual_input.strip():
        typed = manual_input.strip().upper()
        if segment != "NSE Equities" and typed not in shortlist_symbols:
            st.error(f"'{typed}' isn't in the {segment} list. Available: {', '.join(shortlist_symbols)}")
        else:
            st.session_state.manual_symbol = typed
            st.rerun()

if st.session_state.manual_symbol:
    if st.button("⬅ Back to auto-scan"):
        st.session_state.manual_symbol = None
        st.rerun()

# ---------------------------------------------------------- ranked list ----
if evaluations:
    top_n = min(10, len(evaluations))
    top10 = evaluations[:top_n]
    if "top10_pointer" not in st.session_state:
        st.session_state.top10_pointer = 0
    st.session_state.top10_pointer %= len(top10)
    idx10 = st.session_state.top10_pointer
    current10 = top10[idx10]

    st.markdown(f"#### 🏆 Top {top_n} Ranked Shortlist")
    st.caption(f"Showing rank {idx10 + 1} of {len(top10)}")

    nav10a, nav10b, _ = st.columns([1, 1, 4])
    if nav10a.button("❬ Prev", key="top10_prev", disabled=len(top10) < 2):
        st.session_state.top10_pointer = (idx10 - 1) % len(top10)
        st.rerun()
    if nav10b.button("Next ❭", key="top10_next", disabled=len(top10) < 2):
        st.session_state.top10_pointer = (idx10 + 1) % len(top10)
        st.rerun()

    qualifies10 = current10["technical_score"] >= MIN_WINNING_SCORE
    max_score10 = len(current10["rows"]) if segment != "NSE Equities" else 5
    badge_bg10 = "#ca8a04" if qualifies10 else "#94a3b8"
    badge_text10 = ("⭐ RANK " + str(idx10 + 1) + " OF " + str(top_n) + " — LIVE WINNER") if (idx10 == 0 and qualifies10) \
        else ("RANK " + str(idx10 + 1) + " OF " + str(top_n))
    bg_gradient10 = "linear-gradient(135deg, #fef9c3 0%, #fde68a 100%)" if qualifies10 else "#f1f5f9"
    border10 = "#ca8a04" if qualifies10 else "#94a3b8"
    change_color10 = "#15803d" if current10["change_pct"] >= 0 else "#b91c1c"

    st.markdown(compact_card(
        badge_text10, "#ffffff", badge_bg10, current10["symbol"], format(current10["ltp"], ",.2f"),
        border10, bg_gradient10,
        "CHANGE", format(current10["change_pct"], "+.2f") + "%", change_color10,
        "VOLUME", format(current10["volume"], ","), "#0f172a",
        "TECH SCORE", str(current10["technical_score"]) + "/" + str(max_score10), "#15803d" if qualifies10 else "#64748b",
    ), unsafe_allow_html=True)

    if idx10 == 0 and not qualifies10:
        st.caption(f"No {'stock' if segment=='NSE Equities' else 'instrument'} in the shortlist currently meets the {MIN_WINNING_SCORE}/{max_score10} minimum bar -- showing the closest match.")

    v10c1, v10c2 = st.columns(2)
    if v10c1.button("View full details", key="view_top10_" + current10["symbol"], use_container_width=True):
        st.session_state.manual_symbol = current10["symbol"]
        st.rerun()
    with v10c2:
        render_backtest_button(current10["symbol"], current10["yahoo_ticker"], key_suffix="_top10")

    # ---- Backtest-Validated Pick: one click hunts through the shortlist in
    # priority order (live 4/5+ qualifiers first), stopping at the first
    # historical PASS it finds. top10 is already sorted, so qualifiers
    # naturally come first without any reordering needed. ----
    st.markdown("#### 🎯 Backtest-Validated Pick")

    if "bt_hunt_result" not in st.session_state:
        st.session_state.bt_hunt_result = None
    if "bt_hunt_checked" not in st.session_state:
        st.session_state.bt_hunt_checked = []

    hunt_label = "🎯 Hunt for a validated stock" if not st.session_state.bt_hunt_checked else "🎯 Hunt again"
    if st.button(hunt_label):
        checked_this_hunt = []
        found = None
        with st.spinner(f"Hunting through the Top {len(top10)} for a historically validated match..."):
            for e in top10:
                result = run_symbol_backtest(e["yahoo_ticker"], display_symbol=e["symbol"])
                checked_this_hunt.append((e, result))
                if result["verdict"] == "PASS":
                    found = (e, result)
                    break
        st.session_state.bt_hunt_checked = checked_this_hunt
        st.session_state.bt_hunt_result = found
        st.rerun()

    if st.session_state.bt_hunt_checked:
        st.caption(f"Last hunt checked {len(st.session_state.bt_hunt_checked)} of {len(top10)} in the shortlist before stopping.")

    if st.session_state.bt_hunt_result:
        cand, result = st.session_state.bt_hunt_result
        is_fallback = cand["technical_score"] < MIN_WINNING_SCORE
        if is_fallback:
            st.warning(f"⚠️ No instrument with an active {MIN_WINNING_SCORE}/{max_score10}+ live signal passed backtest this hunt -- "
                       f"falling back to {cand['symbol']}, which has a weaker live score ({cand['technical_score']}/{max_score10}) "
                       f"but a solid historical track record.")
        st.markdown(compact_card(
            "✅ BACKTEST PASS" + (" (fallback)" if is_fallback else ""), "#ffffff",
            "#b45309" if is_fallback else "#0d9488",
            cand["symbol"], format(cand["ltp"], ",.2f"),
            "#b45309" if is_fallback else "#0d9488",
            "linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)" if is_fallback else "linear-gradient(135deg, #ccfbf1 0%, #99f6e4 100%)",
            "LIVE SCORE", str(cand["technical_score"]) + "/" + str(max_score10), "#b45309" if is_fallback else "#15803d",
            "WIN RATE", str(result["win_rate"]) + "%", "#0d9488",
            "AVG MOVE", format(result["avg_return"], "+.2f") + "%", "#0d9488" if result["avg_return"] >= 0 else "#b91c1c",
        ), unsafe_allow_html=True)
        if st.button("View full details for " + cand["symbol"], key="view_hunt_winner"):
            st.session_state.manual_symbol = cand["symbol"]
            st.rerun()
    elif st.session_state.bt_hunt_checked:
        st.info(f"No instrument in the current Top {len(top10)} passed backtest validation this hunt. "
                f"Try again after the shortlist refreshes, or trust the live signal on its own for now.")

# ---------------------------------------------------------- chart ----------
st.markdown("#### 📈 Live Intraday Chart — " + snapshot["symbol"])
chart_candles = get_intraday_candles(snapshot["yahoo_ticker"])
if segment != "NSE Equities" and chart_candles is not None and not chart_candles.empty:
    rate = get_usdinr_rate()
    chart_candles = chart_candles.copy()
    for col in ("open", "high", "low", "close"):
        chart_candles[col] = chart_candles[col] * rate
if chart_candles is not None and not chart_candles.empty:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=chart_candles.index, open=chart_candles["open"], high=chart_candles["high"],
                                  low=chart_candles["low"], close=chart_candles["close"], name=snapshot["symbol"]))
    typical = (chart_candles["high"] + chart_candles["low"] + chart_candles["close"]) / 3
    vwap_line = (typical * chart_candles["volume"]).cumsum() / chart_candles["volume"].cumsum().replace(0, 1)
    fig.add_trace(go.Scatter(x=chart_candles.index, y=vwap_line, mode="lines", name="VWAP",
                              line=dict(color="#0284c7", width=2)))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False,
                       plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                       legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No intraday candle data available for this instrument right now (Yahoo may be temporarily rate-limiting or this symbol has thin data). Try Refresh Now, or pick another.")

# ---------------------------------------------------------------- news -----
st.markdown("#### 📰 " + snapshot["symbol"] + " News")
stock_news = fetch_news(snapshot["symbol"] + " " + NEWS_QUERY_SUFFIX[segment])
if stock_news:
    sentiment_summary = aggregate_sentiment(stock_news)
    sentiment_color = {"Mostly Positive": "#15803d", "Mostly Negative": "#b91c1c", "Mixed / Neutral": "#64748b"}[sentiment_summary["overall"]]
    st.markdown(f"<b style='color:{sentiment_color};'>News Sentiment: {sentiment_summary['overall']}</b> "
                f"({sentiment_summary['positive']} positive, {sentiment_summary['negative']} negative, "
                f"{sentiment_summary['neutral']} neutral)", unsafe_allow_html=True)
    sentiment_icon = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}
    for n in stock_news:
        s = classify_sentiment(n["title"])
        st.markdown(f"{sentiment_icon[s]} [{n['title']}]({n['link']})  \n  <span style='color:#64748b;font-size:0.85em;'>{n['source']}</span>",
                    unsafe_allow_html=True)
else:
    st.caption("No recent headlines found for this instrument right now.")

if segment == "NSE Equities":
    with st.expander("📰 General Market News (Nifty / Sensex / RBI)"):
        market_news = fetch_news("Nifty Sensex market news India")
        if market_news:
            for n in market_news:
                s = classify_sentiment(n["title"])
                icon = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}[s]
                st.markdown(f"{icon} [{n['title']}]({n['link']})  \n  <span style='color:#64748b;font-size:0.85em;'>{n['source']}</span>",
                            unsafe_allow_html=True)
        else:
            st.caption("No recent market headlines found right now.")

# ---------------------------------------------------------------- matrix ---
col_matrix, col_summary = st.columns([3, 1])
with col_matrix:
    matrix_title = "11-Parameter Strategy Matrix" if segment == "NSE Equities" else "5-Signal Technical Matrix"
    st.markdown(f"#### 📋 {matrix_title}")
    table_rows = ""
    i = 0
    for name, verdict, detail in snapshot["rows"]:
        i += 1
        table_rows += "<tr><td>" + str(i) + "</td><td>" + name + "</td><td>" + badge(verdict) + "</td><td>" + detail + "</td></tr>"
    table_html = ('<table class="qb-text" style="width:100%; border-collapse:collapse; background:#ffffff; border-radius:8px; overflow:hidden;">'
                  '<thead><tr><th>#</th><th>Parameter</th><th>Verdict</th><th>Live Metric Value</th></tr></thead>'
                  '<tbody>' + table_rows + '</tbody></table>')
    st.markdown(table_html, unsafe_allow_html=True)

with col_summary:
    st.markdown('<div class="qb-panel">', unsafe_allow_html=True)
    st.markdown("**📊 Live Summary**")
    st.metric("Pass Conditions", f"{pass_count} / {total_rows}")
    st.metric("Fail Conditions", f"{fail_count} / {total_rows}")
    st.metric("Data Unavailable", f"{unavail_count} / {total_rows}")
    st.metric("Matrix Score", f"{score}%")
    st.metric("Intraday Technical Score", f"{snapshot['technical_score']} / {5 if segment != 'NSE Equities' else 5}")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------- position sizer -
st.markdown("#### 🧮 Position Sizing")
if segment != "NSE Equities":
    st.caption("Price converted from USD to Rupees at the current live rate for sizing purposes.")
capital = st.number_input("Your trading capital (Rs)", min_value=1000, step=1000, value=15000)
price = snapshot["ltp"]
if not price or price != price or price <= 0:
    price = None

if price is None:
    st.warning("Live price for this instrument is temporarily unavailable. Try Refresh Now.")
else:
    unit_label = UNIT_LABEL[segment]
    units = int(round(capital / price))
    risk_unit = price * 0.008
    sl = price - (risk_unit * 1.5)
    tp = price + (risk_unit * 3.0)

    size_cols = st.columns(4)
    size_cols[0].markdown('<div class="qb-panel">🛒 Buy Exactly<br><span style="font-size:1.4em;">' + str(units) + ' ' + unit_label + '</span></div>', unsafe_allow_html=True)
    size_cols[1].markdown('<div class="qb-panel">🛡️ Risk Unit<br><span style="font-size:1.4em;">Rs ' + format(risk_unit, ",.2f") + '</span></div>', unsafe_allow_html=True)
    size_cols[2].markdown('<div class="qb-panel">🔒 Stop Loss<br><span style="font-size:1.4em;color:#b91c1c;">Rs ' + format(sl, ",.2f") + '</span></div>', unsafe_allow_html=True)
    size_cols[3].markdown('<div class="qb-panel">🎯 Take Profit<br><span style="font-size:1.4em;color:#15803d;">Rs ' + format(tp, ",.2f") + '</span></div>', unsafe_allow_html=True)

    risk_pct = risk_unit / price * 100
    st.caption("Risk per trade: Rs " + format(risk_unit, ",.2f") + " (" + format(risk_pct, ".2f") +
               "%) | SL: 1.5x Risk | TP: 3.0x Risk. Not investment advice.")

st.divider()
if segment == "NSE Equities":
    render_portfolio_section(get_live_quotes, Instrument)
else:
    st.caption("📁 Portfolio tracking currently supports NSE Equities only.")

st.divider()
log_bytes = read_log_bytes()
if log_bytes:
    st.download_button("Download signal_log.csv", log_bytes, file_name="signal_log.csv", mime="text/csv")

if is_open and not st.session_state.manual_symbol:
    time.sleep(10)
    st.rerun()
