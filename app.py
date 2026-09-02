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
import yfinance as yf

from kotak_client import (
    IST,
    Instrument,
    get_commodities_universe,
    get_crypto_universe,
    get_fno_universe,
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
    fresh_vwap_cross_check,
    momentum_check,
    supertrend_check,
    volume_surge_check,
    vwap_check,
)
from portfolio import render_portfolio_section
from signal_logger import log_signal, read_log_bytes
from news import fetch_news, classify_sentiment, aggregate_sentiment
from backtest_engine import run_symbol_backtest
from breakout_engine import detect_setup, position_size_for_setup

MIN_WINNING_SCORE = 4
SHORTLIST_SIZE = 25
ALERT_COOLDOWN_MINUTES = 15
PENNY_PRICE_FLOOR = 20  # NSE equities below this price are excluded as likely penny stocks

SEGMENTS = ["NSE Equities", "F&O Eligible Stocks", "Commodities (Global Proxy)", "Crypto"]
EQUITY_LIKE_SEGMENTS = ("NSE Equities", "F&O Eligible Stocks")  # 11-row matrix, fundamentals, already-INR pricing
UNIT_LABEL = {"NSE Equities": "SHARES", "F&O Eligible Stocks": "SHARES (confirm lot size with your broker)",
              "Commodities (Global Proxy)": "UNITS (proxy)", "Crypto": "COINS/UNITS"}
NEWS_QUERY_SUFFIX = {"NSE Equities": "share price NSE", "F&O Eligible Stocks": "share price NSE F&O",
                     "Commodities (Global Proxy)": "price commodity market news", "Crypto": "cryptocurrency price news"}

st.set_page_config(page_title="QuantBreakout Scanner", layout="wide", page_icon="lightning")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    html, body, [class*="css"], .stMarkdown, .stButton>button, .stSelectbox, .stTextInput {
        font-family: 'Roboto', 'Helvetica Neue', Arial, sans-serif !important;
    }
    .stApp { background-color: #f4f6f8; }
    .block-container { padding-top: 1rem; }

    /* Dark utility top bar, like a financial portal's header strip */
    .qb-topbar {
        background:#0b1f3a; color:#e5e7eb; padding:8px 18px; font-size:0.78em;
        display:flex; justify-content:space-between; align-items:center;
        margin: -1rem -1rem 16px -1rem; border-radius: 0 0 6px 6px;
    }
    .qb-logo-badge {
        background:#00963f; color:#ffffff; font-weight:700; padding:4px 12px;
        border-radius:4px; letter-spacing:0.4px; font-size:1.05em;
    }

    /* Ticker strip: single bordered row with vertical dividers, like a
       market-index ticker on a financial news site */
    .qb-ticker-strip {
        display:flex; border:1px solid #d1d5db; border-radius:6px; background:#ffffff;
        overflow:hidden; margin-bottom:16px; flex-wrap:wrap;
    }
    .qb-ticker-item {
        flex:1; min-width:150px; padding:10px 16px; border-right:1px solid #e5e7eb; text-align:left;
    }
    .qb-ticker-item:last-child { border-right:none; }
    .qb-ticker-name { font-size:0.72em; color:#6b7280; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; }
    .qb-ticker-value { font-size:1.08em; font-weight:700; color:#111827; margin-top:2px; }
    .qb-ticker-change-up { color:#0a7d2e; font-weight:600; font-size:0.85em; }
    .qb-ticker-change-down { color:#c81e1e; font-weight:600; font-size:0.85em; }

    /* General cards / panels */
    .qb-panel {
        background-color: #ffffff;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .qb-text { color: #111827; }
    .qb-badge-pass { color: #ffffff; background:#0a7d2e; padding:3px 10px; border-radius:4px; font-weight:600; font-size:0.85em; }
    .qb-badge-fail { color: #ffffff; background:#c81e1e; padding:3px 10px; border-radius:4px; font-weight:600; font-size:0.85em; }
    .qb-badge-unavail { color: #374151; background:#e5e7eb; padding:3px 10px; border-radius:4px; font-weight:600; font-size:0.85em; }

    /* Tables: dark navy header, zebra-striped rows, clean borders */
    table.qb-text { border:1px solid #d1d5db !important; }
    thead tr th { background-color: #0b1f3a !important; color:#ffffff !important; padding:9px 10px !important; font-size:0.85em; text-transform:uppercase; letter-spacing:0.03em; }
    tbody tr td { padding:8px 10px !important; border-bottom:1px solid #e5e7eb; font-size:0.92em; }
    tbody tr:nth-child(even) td { background-color: #f8fafc; }

    /* Section headers -- bold with a green accent underline, like a portal's tab style */
    .qb-section-header { font-weight:700; color:#111827; border-bottom:3px solid #00963f; display:inline-block; padding-bottom:2px; margin-bottom:10px; }

    /* Buttons: single flat accent color instead of Streamlit's default */
    .stButton>button {
        background:#00963f; color:#ffffff; border:none; border-radius:4px; font-weight:600;
    }
    .stButton>button:hover { background:#00782f; color:#ffffff; }
    .stDownloadButton>button { background:#0b1f3a; color:#ffffff; border-radius:4px; font-weight:600; }

    @media (max-width: 768px) {
        .qb-panel { padding: 10px; }
        html, body, [class*="css"] { font-size: 13px; }
        .stDataFrame { overflow-x: auto; }
        .qb-ticker-strip { flex-direction: column; }
        .qb-ticker-item { border-right:none; border-bottom:1px solid #e5e7eb; }
    }
    </style>
    <div class="qb-topbar">
        <span><span class="qb-logo-badge">QUANTBREAKOUT</span>&nbsp;&nbsp;Real-Time Multi-Segment Scanner</span>
        <span>Personal Use Only • Data via Yahoo Finance</span>
    </div>
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


def ticker_item(label, value, change_str=None, is_up=True):
    change_html = ""
    if change_str is not None:
        arrow = "▲" if is_up else "▼"
        cls = "qb-ticker-change-up" if is_up else "qb-ticker-change-down"
        change_html = '<div class="' + cls + '">' + arrow + ' ' + change_str + '</div>'
    return ('<div class="qb-ticker-item"><div class="qb-ticker-name">' + label + '</div>'
            '<div class="qb-ticker-value">' + value + '</div>' + change_html + '</div>')


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


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_market_regime() -> dict:
    """Market Regime Filter, from the V2 strategy document: classifies
    whether NIFTY itself is trending up, trending down, or choppy/sideways,
    using EMA20 vs EMA50 on daily candles plus recent daily range context.
    Breakout setups are far less reliable in a choppy market -- the V2 spec
    explicitly says to sit out NEUTRAL regime rather than force signals."""
    try:
        hist = yf.Ticker("^NSEI").history(period="4mo", interval="1d")
        hist = hist.dropna(subset=["Close"])
    except Exception:
        return {"regime": "UNKNOWN", "detail": "Could not fetch NIFTY data for regime check."}
    if len(hist) < 55:
        return {"regime": "UNKNOWN", "detail": "Not enough NIFTY history for regime check."}

    close = hist["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    last_close, last_ema20, last_ema50 = close.iloc[-1], ema20.iloc[-1], ema50.iloc[-1]

    # Trend slope: how much has EMA20 itself moved over the last 5 days (in % terms)
    ema20_slope_pct = (ema20.iloc[-1] - ema20.iloc[-6]) / ema20.iloc[-6] * 100 if len(ema20) > 6 else 0

    if last_close > last_ema20 > last_ema50 and ema20_slope_pct > 0.3:
        return {"regime": "UPTREND", "detail": f"NIFTY above both EMA20/EMA50, rising ({ema20_slope_pct:+.2f}% over 5 days)."}
    if last_close < last_ema20 < last_ema50 and ema20_slope_pct < -0.3:
        return {"regime": "DOWNTREND", "detail": f"NIFTY below both EMA20/EMA50, falling ({ema20_slope_pct:+.2f}% over 5 days)."}
    return {"regime": "CHOPPY/NEUTRAL", "detail": f"NIFTY not showing a clear trend (EMA20 slope {ema20_slope_pct:+.2f}% over 5 days). "
                                                   f"Breakout setups are less reliable in this regime -- the V2 spec recommends sitting out rather than forcing signals."}


def evaluate_symbol(inst, segment):
    is_equity = segment in ("NSE Equities", "F&O Eligible Stocks")
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
        not_penny = ltp is not None and ltp >= PENNY_PRICE_FLOOR
        safety_pass = (mcap_verdict in ("pass", "unavailable")) and not_penny
    else:
        safety_pass = ltp is not None and ltp > 0

    # Non-scoring metadata: does this stock's LATEST bar show a fresh VWAP
    # cross with a volume surge, right now? This does NOT affect
    # technical_score -- it's a separate "catching the moment it starts"
    # signal, shown as a badge/filter rather than folded into the 0-5 score.
    fresh_cross, fresh_cross_detail = fresh_vwap_cross_check(candles)

    return {
        "symbol": inst.trading_symbol, "yahoo_ticker": inst.yahoo_ticker, "ltp": ltp,
        "change": change, "change_pct": change_pct,
        "volume": volume, "rows": rows,
        "technical_score": technical_score, "safety_pass": safety_pass,
        "fresh_vwap_cross": fresh_cross, "fresh_vwap_cross_detail": fresh_cross_detail,
    }


def scan_shortlist(shortlist, segment):
    evaluations = [evaluate_symbol(inst, segment) for inst in shortlist]
    evaluations.sort(key=lambda e: (e["technical_score"], e["volume"]), reverse=True)
    return evaluations


@st.cache_data(ttl=8, show_spinner=False)
def scan_shortlist_cached(symbol_ticker_pairs, segment):
    """Same as scan_shortlist, but cached for 8 seconds. Without this,
    Streamlit re-runs the ENTIRE script (and therefore re-scans every stock
    in the shortlist from scratch) on every single click -- Next, Search,
    opening a Backtest result, anything -- which is what was making the
    page feel slow. This lets clicks within the same few seconds reuse the
    same scan instead of repeating it."""
    rebuilt = [Instrument(trading_symbol=s, yahoo_ticker=t) for s, t in symbol_ticker_pairs]
    return scan_shortlist(rebuilt, segment)


def rating_label(score, max_score=5):
    """Maps the 0-5 technical score to a familiar Buy/Sell rating, like the
    technical rating gauges seen on TradingView/Moneycontrol. Purely a
    relabeling of the same mechanical score -- not separate advice."""
    pct = score / max_score
    if pct >= 1.0:
        return "STRONG BUY", "#065f46"
    if pct >= 0.8:
        return "BUY", "#0a7d2e"
    if pct >= 0.6:
        return "NEUTRAL", "#6b7280"
    if pct >= 0.4:
        return "SELL", "#c2410c"
    return "STRONG SELL", "#991b1b"


def rating_pill_html(score, max_score=5):
    label, color = rating_label(score, max_score)
    return ('<div style="text-align:center;margin:6px 0 12px 0;">'
            '<span style="background:' + color + ';color:#ffffff;padding:4px 16px;border-radius:20px;'
            'font-weight:700;font-size:0.85em;letter-spacing:0.03em;">' + label + '</span></div>')


def render_stock_header(symbol, price, change, change_pct, exchange_label="NSE"):
    """TradingView-style header: circular initial badge, name, exchange
    pill, big price with colored change -- purely a visual match, driven
    by our own real live data."""
    is_up = change >= 0
    color = "#0a7d2e" if is_up else "#c81e1e"
    sign = "+" if is_up else ""
    initial = symbol[0] if symbol else "?"
    st.markdown(
        '<div style="display:flex;align-items:center;gap:16px;margin:10px 0 4px 0;">'
        '<div style="width:56px;height:56px;border-radius:50%;background:#0b1f3a;color:#ffffff;'
        'display:flex;align-items:center;justify-content:center;font-size:1.6em;font-weight:700;">' + initial + '</div>'
        '<div>'
        '<div style="font-size:1.6em;font-weight:700;color:#111827;">' + symbol + '</div>'
        '<span style="background:#e5e7eb;color:#374151;padding:2px 10px;border-radius:4px;font-size:0.78em;font-weight:600;">'
        + exchange_label + '</span>'
        '</div></div>'
        '<div style="display:flex;align-items:baseline;gap:12px;margin:6px 0 16px 0;">'
        '<span style="font-size:2.1em;font-weight:700;color:#111827;">Rs ' + format(price, ",.2f") + '</span>'
        '<span style="font-size:1.1em;font-weight:600;color:' + color + ';">' + sign + format(change, ",.2f") +
        '&nbsp;' + sign + format(change_pct, ".2f") + '%</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_rating_gauge(score, max_score=5):
    """Semi-circle 'analyst rating'-style gauge (Strong Sell -> Strong Buy)
    with a needle, matching TradingView's technical rating widget style --
    driven by our own real 0-5 technical score, not third-party analyst data."""
    import math
    label, color = rating_label(score, max_score)
    fraction = max(0.0, min(1.0, score / max_score))
    angle_deg = 180 - (fraction * 180)
    angle_rad = math.radians(angle_deg)
    cx, cy, r = 150, 140, 110
    needle_len = r - 15
    tip_x = cx + needle_len * math.cos(angle_rad)
    tip_y = cy - needle_len * math.sin(angle_rad)

    def arc_path(start_deg, end_deg, radius):
        sx = cx + radius * math.cos(math.radians(start_deg))
        sy = cy - radius * math.sin(math.radians(start_deg))
        ex = cx + radius * math.cos(math.radians(end_deg))
        ey = cy - radius * math.sin(math.radians(end_deg))
        return f"M {sx:.1f} {sy:.1f} A {radius} {radius} 0 0 1 {ex:.1f} {ey:.1f}"

    bands = [
        (180, 144, "#f97316"),  # Strong Sell
        (144, 108, "#facc15"),  # Sell
        (108, 72, "#22c55e"),   # Neutral
        (72, 36, "#16a34a"),    # Buy
        (36, 0, "#bbf7d0"),     # Strong Buy
    ]
    arcs = "".join(
        f'<path d="{arc_path(s, e, r)}" stroke="{c}" stroke-width="18" fill="none" stroke-linecap="butt"/>'
        for s, e, c in bands
    )
    labels_svg = (
        '<text x="20" y="150" font-size="11" fill="#6b7280">Strong Sell</text>'
        '<text x="245" y="150" font-size="11" fill="#6b7280">Strong Buy</text>'
        '<text x="60" y="60" font-size="11" fill="#6b7280">Sell</text>'
        '<text x="225" y="60" font-size="11" fill="#6b7280">Buy</text>'
        '<text x="130" y="25" font-size="11" fill="#6b7280">Neutral</text>'
    )
    svg = f"""
    <svg viewBox="0 0 300 175" style="width:100%;max-width:340px;display:block;margin:0 auto;">
        {arcs}
        {labels_svg}
        <line x1="{cx}" y1="{cy}" x2="{tip_x:.1f}" y2="{tip_y:.1f}" stroke="#111827" stroke-width="3" stroke-linecap="round"/>
        <circle cx="{cx}" cy="{cy}" r="7" fill="#111827"/>
    </svg>
    <div style="text-align:center;font-size:1.4em;font-weight:700;color:{color};margin-top:-6px;">{label}</div>
    """
    st.markdown(svg, unsafe_allow_html=True)


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
    elif segment == "F&O Eligible Stocks":
        shortlist = get_fno_universe()
        return shortlist, shortlist, (f"Tracking {len(shortlist)} historically liquid F&O-eligible NSE stocks. "
                                       f"Cross-check current eligibility & lot size on NSE/your broker before trading.")
    elif segment == "Commodities (Global Proxy)":
        shortlist = get_commodities_universe()
        return shortlist, shortlist, f"Tracking {len(shortlist)} global commodity proxies (COMEX/NYMEX, USD->INR converted)."
    else:
        shortlist = get_crypto_universe()
        return shortlist, shortlist, f"Tracking {len(shortlist)} major cryptocurrencies (24/7, USD->INR converted)."


def segment_is_open(segment):
    if segment in ("NSE Equities", "F&O Eligible Stocks"):
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

strip_html = '<div class="qb-ticker-strip">'
if segment in EQUITY_LIKE_SEGMENTS:
    for name, q in index_quotes.items():
        is_up = q["change"] >= 0
        sign = "+" if is_up else ""
        strip_html += ticker_item(name, format(q["ltp"], ",.2f"),
                                   sign + format(q["change"], ",.2f") + " (" + sign + format(q["change_pct"], ".2f") + "%)", is_up)
strip_html += ticker_item("MARKET STATUS", "🟢 LIVE" if is_open else "🔴 CLOSED")
strip_html += ticker_item("SERVER TIME (IST)", dt.datetime.now(IST).strftime("%H:%M:%S"))
if segment not in EQUITY_LIKE_SEGMENTS:
    strip_html += ticker_item("USD/INR RATE", format(get_usdinr_rate(), ",.2f"))
strip_html += "</div>"
st.markdown(strip_html, unsafe_allow_html=True)

if not is_open:
    st.info("Market is closed — showing the last completed session's data.")
if segment == "Commodities (Global Proxy)":
    st.caption("⚠️ Directional reference only — global COMEX/NYMEX proxy prices, not exact MCX contract prices.")

if segment in EQUITY_LIKE_SEGMENTS:
    regime = get_market_regime()
    regime_style = {"UPTREND": ("#dcfce7", "#166534"), "DOWNTREND": ("#fee2e2", "#991b1b"),
                     "CHOPPY/NEUTRAL": ("#fef3c7", "#92400e"), "UNKNOWN": ("#e5e7eb", "#374151")}
    rbg, rfg = regime_style.get(regime["regime"], regime_style["UNKNOWN"])
    st.markdown(
        '<div style="background:' + rbg + ';color:' + rfg + ';padding:10px 16px;border-radius:8px;'
        'font-weight:600;margin-bottom:10px;">📊 Market Regime: ' + regime["regime"] + '</div>',
        unsafe_allow_html=True,
    )
    st.caption(regime["detail"])

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
    pairs = tuple((i.trading_symbol, i.yahoo_ticker) for i in shortlist)
    evaluations = scan_shortlist_cached(pairs, segment)
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
    placeholder = "e.g. SBIN, INFY, ICICIBANK" if segment in EQUITY_LIKE_SEGMENTS else "e.g. " + shortlist_symbols[0]
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

    st.markdown(f"#### 🏆 Top {top_n} Ranked Shortlist")
    only_fresh = st.checkbox("🚀 Show only stocks with a fresh VWAP cross + volume surge right now")
    display_list = [e for e in top10 if e["fresh_vwap_cross"]] if only_fresh else top10
    if only_fresh and not display_list:
        st.caption("No stock in the current shortlist has a fresh VWAP cross with volume surge on its latest bar right now -- this is a moment-specific signal, check back shortly.")

    for rank, e in enumerate(display_list, start=1):
        qualifies = e["technical_score"] >= MIN_WINNING_SCORE
        max_score = 5  # technical_score is always out of 5 regardless of segment
        badge_bg = "#ca8a04" if qualifies else "#94a3b8"
        badge_text = ("⭐ RANK " + str(rank) + " OF " + str(top_n) + " — LIVE WINNER") if (rank == 1 and qualifies) \
            else ("RANK " + str(rank) + " OF " + str(top_n))
        bg_gradient = "linear-gradient(135deg, #fef9c3 0%, #fde68a 100%)" if qualifies else "#f1f5f9"
        border = "#ca8a04" if qualifies else "#94a3b8"
        change_color = "#15803d" if e["change_pct"] >= 0 else "#b91c1c"

        st.markdown(compact_card(
            badge_text, "#ffffff", badge_bg, e["symbol"], format(e["ltp"], ",.2f"),
            border, bg_gradient,
            "CHANGE", format(e["change_pct"], "+.2f") + "%", change_color,
            "VOLUME", format(e["volume"], ","), "#0f172a",
            "TECH SCORE", str(e["technical_score"]) + "/" + str(max_score), "#15803d" if qualifies else "#64748b",
        ), unsafe_allow_html=True)
        st.markdown(rating_pill_html(e["technical_score"], max_score), unsafe_allow_html=True)
        if e["fresh_vwap_cross"]:
            st.markdown(
                '<div style="text-align:center;margin:-6px 0 10px 0;">'
                '<span style="background:#7c3aed;color:#ffffff;padding:3px 12px;border-radius:14px;'
                'font-size:0.78em;font-weight:700;">🚀 FRESH VWAP CROSS + VOLUME</span></div>',
                unsafe_allow_html=True,
            )

        if rank == 1 and not qualifies and not only_fresh:
            st.caption(f"No {'stock' if segment=='NSE Equities' else 'instrument'} in the shortlist currently meets the {MIN_WINNING_SCORE}/{max_score} minimum bar -- showing the closest match.")

        d1, d2 = st.columns(2)
        if d1.button("🔍 View Full Details + News", key="view_top10_" + e["symbol"], use_container_width=True):
            st.session_state.manual_symbol = e["symbol"]
            st.rerun()
        with d2:
            render_backtest_button(e["symbol"], e["yahoo_ticker"], key_suffix="_top10")
        st.markdown("---")

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
        cand_max_score = 5  # technical_score is always out of 5 regardless of segment
        if is_fallback:
            st.warning(f"⚠️ No instrument with an active {MIN_WINNING_SCORE}/{cand_max_score}+ live signal passed backtest this hunt -- "
                       f"falling back to {cand['symbol']}, which has a weaker live score ({cand['technical_score']}/{cand_max_score}) "
                       f"but a solid historical track record.")
        st.markdown(compact_card(
            "✅ BACKTEST PASS" + (" (fallback)" if is_fallback else ""), "#ffffff",
            "#b45309" if is_fallback else "#0d9488",
            cand["symbol"], format(cand["ltp"], ",.2f"),
            "#b45309" if is_fallback else "#0d9488",
            "linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)" if is_fallback else "linear-gradient(135deg, #ccfbf1 0%, #99f6e4 100%)",
            "LIVE SCORE", str(cand["technical_score"]) + "/" + str(cand_max_score), "#b45309" if is_fallback else "#15803d",
            "WIN RATE", str(result["win_rate"]) + "%", "#0d9488",
            "AVG MOVE", format(result["avg_return"], "+.2f") + "%", "#0d9488" if result["avg_return"] >= 0 else "#b91c1c",
        ), unsafe_allow_html=True)
        st.markdown(rating_pill_html(cand["technical_score"], cand_max_score), unsafe_allow_html=True)
        if st.button("View full details for " + cand["symbol"], key="view_hunt_winner"):
            st.session_state.manual_symbol = cand["symbol"]
            st.rerun()
    elif st.session_state.bt_hunt_checked:
        st.info(f"No instrument in the current Top {len(top10)} passed backtest validation this hunt. "
                f"Try again after the shortlist refreshes, or trust the live signal on its own for now.")

# ---------------------------------------------------------- stock header --
exchange_label = ("NSE" if segment == "NSE Equities" else "NSE (F&O)" if segment == "F&O Eligible Stocks"
                   else "COMEX/NYMEX (Proxy)" if segment == "Commodities (Global Proxy)" else "CRYPTO")
render_stock_header(snapshot["symbol"], snapshot["ltp"], snapshot["change"], snapshot["change_pct"], exchange_label)

gauge_col, _ = st.columns([1, 1])
with gauge_col:
    render_rating_gauge(snapshot["technical_score"], 5)

# ---------------------------------------------------------- ORB + retest --
if segment in EQUITY_LIKE_SEGMENTS:
    st.markdown("#### 🎯 Breakout Setup Detector (Retest + Anti-Chase)")
    st.caption("A separate, more selective check -- specifically designed to avoid entering an already-exhausted breakout.")
    current_regime = get_market_regime()
    if current_regime["regime"] == "CHOPPY/NEUTRAL":
        st.warning("⚠️ Market regime is CHOPPY/NEUTRAL right now -- breakout setups are statistically less reliable in this condition. Treat any signal below with extra caution.")
    five_min_candles = get_intraday_candles(snapshot["yahoo_ticker"], interval="5m")
    setup = detect_setup(five_min_candles)

    state_style = {
        "NO_SETUP": ("#e5e7eb", "#374151", "No setup"),
        "WATCHING_RETEST": ("#fef3c7", "#92400e", "Watching for retest"),
        "READY_TO_ENTER": ("#dcfce7", "#166534", "Ready to enter"),
        "TOO_LATE_CHASE": ("#fee2e2", "#991b1b", "Too late -- would be chasing"),
    }
    bg, fg, label = state_style.get(setup["state"], state_style["NO_SETUP"])
    dir_text = (" (" + setup["direction"] + ")") if setup["direction"] else ""
    st.markdown(
        '<div style="background:' + bg + ';color:' + fg + ';padding:12px 16px;border-radius:8px;font-weight:600;">'
        + label + dir_text + '</div>', unsafe_allow_html=True,
    )
    st.caption(setup["detail"])

    if setup["state"] == "READY_TO_ENTER":
        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Entry", f"Rs {setup['entry_price']:.2f}")
        rc2.metric("Stop Loss", f"Rs {setup['stop_loss']:.2f}")
        rc3.metric("Target", f"Rs {setup['target']:.2f}")
        orb_cap_col, orb_risk_col = st.columns(2)
        orb_capital = orb_cap_col.number_input("Capital (Rs)", min_value=1000, step=1000, value=15000, key="orb_capital")
        risk_pct_input = orb_risk_col.number_input("Risk % per trade", min_value=0.1, max_value=5.0, value=0.5, step=0.1, key="orb_risk_pct")
        sizing = position_size_for_setup(orb_capital, setup["entry_price"], setup["stop_loss"], risk_pct_input)
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Quantity", str(sizing["quantity"]))
        sc2.metric("Risk/Share", f"Rs {sizing['risk_per_share']:.2f}")
        sc3.metric("Max Risk", f"Rs {sizing['max_risk']:.2f}")

# ---------------------------------------------------------- chart ----------
st.markdown("#### 📈 Live Intraday Chart — " + snapshot["symbol"])
chart_candles = get_intraday_candles(snapshot["yahoo_ticker"])
if segment not in EQUITY_LIKE_SEGMENTS and chart_candles is not None and not chart_candles.empty:
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

if segment in EQUITY_LIKE_SEGMENTS:
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
    matrix_title = "11-Parameter Strategy Matrix" if segment in EQUITY_LIKE_SEGMENTS else "5-Signal Technical Matrix"
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
    st.metric("Intraday Technical Score", f"{snapshot['technical_score']} / 5")
    st.markdown(rating_pill_html(snapshot["technical_score"], 5), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------- position sizer -
st.markdown("#### 🧮 Position Sizing")
if segment not in EQUITY_LIKE_SEGMENTS:
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
if segment in EQUITY_LIKE_SEGMENTS:
    render_portfolio_section(get_live_quotes, Instrument)
else:
    st.caption("📁 Portfolio tracking currently supports NSE Equities and F&O Eligible Stocks only.")

st.divider()
log_bytes = read_log_bytes()
if log_bytes:
    st.download_button("Download signal_log.csv", log_bytes, file_name="signal_log.csv", mime="text/csv")

if is_open and not st.session_state.manual_symbol:
    time.sleep(10)
    st.rerun()
