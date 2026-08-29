"""
fundamentals.py
----------------
Kotak Neo has no fundamentals endpoint (P/E, Beta, Market Cap, D/E), so this
module fills that one gap using yfinance — but ONLY via direct ticker lookup
(yf.Ticker("X.NS").info), never yf.Search(). That distinction matters: the
notepad's rate-limit warning is about free-text search calls, not direct
ticker access. Direct lookups are far less likely to get an app blocked.

Cached for a full trading day: none of these four numbers move meaningfully
intraday, so there is no reason to re-fetch them every 10 seconds alongside
the live price feed.
"""

from __future__ import annotations

import streamlit as st
import yfinance as yf


@st.cache_data(ttl=60 * 60 * 20, show_spinner=False)  # ~20h, safely spans one trading day
def get_fundamentals(nse_symbol: str) -> dict:
    """Returns pe, beta, market_cap_cr, debt_to_equity -- any of which may be
    None if Yahoo doesn't have it, or if it returned something that isn't a
    usable number (happens occasionally for thinly-covered stocks). Callers
    decide how to treat a None (mark DATA UNAVAILABLE vs. auto-pass)."""
    ticker = yf.Ticker(f"{nse_symbol}.NS")
    try:
        info = ticker.info
    except Exception:
        info = {}

    def clean(value):
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None
        return None if f != f else f  # filters out NaN too

    market_cap = clean(info.get("marketCap"))
    market_cap_cr = round(market_cap / 1e7, 1) if market_cap else None  # rupees -> crores

    return {
        "pe": clean(info.get("trailingPE")),
        "beta": clean(info.get("beta")),
        "market_cap_cr": market_cap_cr,
        "debt_to_equity": clean(info.get("debtToEquity")),
    }
