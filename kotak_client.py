"""
kotak_client.py
----------------
NOTE: despite the filename (kept so app.py doesn't need any changes), this
now pulls data from free public Yahoo Finance data via yfinance, NOT from
Kotak Neo. This avoids needing broker API keys, TOTP, MPIN, or the SEBI
static-IP whitelisting requirement entirely, since we're not connecting to
any broker's order/trading system — just reading public market prices.

Trade-off: Yahoo's free data can occasionally lag by a few minutes and is an
unofficial source, so treat prices as "close to real-time" rather than
tick-perfect. Good enough for a personal screening tool.

No credentials or Streamlit secrets are required for this file to work.
"""

from __future__ import annotations

import datetime as dt
import io
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

# A curated list of liquid, well-known NSE stocks. Kept short on purpose —
# polling too many symbols too often against Yahoo's free (unofficial, rate
# limited) endpoint will get the app throttled. Feel free to add/remove
# symbols here (NSE trading symbol, no ".NS" suffix — that's added
# automatically).
# Trimmed to ~20 names on purpose: the app now scores EVERY stock in this
# list each cycle (not just checking volume), so a smaller, genuinely liquid
# set means fresher data per stock and fewer Yahoo rate-limit hiccups.
NSE_LIQUID_UNIVERSE = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL",
    "ITC", "LT", "KOTAKBANK", "AXISBANK", "BAJFINANCE", "MARUTI", "SUNPHARMA",
    "TITAN", "TATAMOTORS", "TATASTEEL", "ADANIENT", "HCLTECH", "JSWSTEEL",
]


def market_is_open(now: Optional[dt.datetime] = None) -> bool:
    """NSE cash market hours: 9:15–15:30 IST, Monday–Friday."""
    now = now or dt.datetime.now(IST)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    open_t = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= now <= close_t


@dataclass
class Instrument:
    trading_symbol: str
    instrument_token: str = ""  # unused with yfinance, kept for compatibility
    exchange_segment: str = "nse_cm"


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_nse_equity_universe() -> list[Instrument]:
    """Curated fallback list, used only if the full official NSE list
    (get_full_nse_universe below) can't be fetched for some reason."""
    return [Instrument(trading_symbol=s) for s in NSE_LIQUID_UNIVERSE]


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_full_nse_universe() -> list[Instrument]:
    """Pulls the complete official NSE cash-market equity list (~2,000
    symbols) directly from NSE's own published archive. This is what makes
    the scanner cover 'all NSE stocks' rather than a fixed short list.

    Falls back to the curated liquid list if NSE's endpoint is unreachable
    or blocks the request (their site does sometimes rate-limit or reject
    requests without browser-like headers/cookies).
    """
    url = "https://archive.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/csv,*/*",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(io.BytesIO(resp.content))
        sym_col = next(c for c in df.columns if "SYMBOL" in c.upper())
        series_col = next((c for c in df.columns if "SERIES" in c.upper()), None)
        if series_col:
            df = df[df[series_col].astype(str).str.strip().str.upper() == "EQ"]
        symbols = df[sym_col].dropna().astype(str).str.strip().tolist()
        if len(symbols) < 500:  # sanity check -- something looked wrong, don't trust a tiny result
            raise ValueError("Unexpectedly small NSE universe returned")
        return [Instrument(trading_symbol=s) for s in symbols]
    except Exception:
        return get_nse_equity_universe()


@st.cache_data(ttl=15 * 60, show_spinner=False)
def get_tier1_shortlist(instruments: list[Instrument], top_n: int = 50) -> list[Instrument]:
    """Tier 1: cheap batch daily-quote scan across the FULL NSE universe to
    find the most actively traded stocks right now, refreshed every 15
    minutes. This is what feeds Tier 2's live 10-second technical scan --
    see app.py. Uses yfinance's batch download (one request for many
    tickers) rather than one request per stock, which is both far faster
    and much gentler on Yahoo's free endpoint.
    """
    symbols = [i.trading_symbol for i in instruments]
    ranked = []
    chunk_size = 200  # batch requests to stay well under practical request-size limits
    for start in range(0, len(symbols), chunk_size):
        chunk = symbols[start:start + chunk_size]
        tickers = " ".join(f"{s}.NS" for s in chunk)
        try:
            data = yf.download(tickers, period="2d", interval="1d", group_by="ticker",
                                threads=True, progress=False)
        except Exception:
            continue
        for s in chunk:
            col = f"{s}.NS"
            try:
                sub = data[col] if len(chunk) > 1 else data
                if sub.empty or sub["Volume"].isna().all():
                    continue
                last_vol = float(sub["Volume"].iloc[-1])
                ranked.append((s, last_vol))
            except Exception:
                continue
    ranked.sort(key=lambda x: x[1], reverse=True)
    top_symbols = [s for s, _ in ranked[:top_n]]
    if not top_symbols:  # total failure -- fall back to the small curated list so the app still works
        return get_nse_equity_universe()[:top_n]
    return [Instrument(trading_symbol=s) for s in top_symbols]


INDEX_TICKERS = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"}


@st.cache_data(ttl=30, show_spinner=False)
def get_index_quotes() -> dict[str, dict]:
    """Live (a few minutes' lag) NIFTY 50 / BANK NIFTY quotes. Returns
    {"NIFTY 50": {"ltp":..., "change":..., "change_pct":...}, ...}."""
    out = {}
    for name, sym in INDEX_TICKERS.items():
        try:
            hist = yf.Ticker(sym).history(period="2d", interval="1d")
            if hist.empty:
                continue
            last = hist.iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else last["Close"]
            ltp = float(last["Close"])
            change = ltp - float(prev_close)
            change_pct = (change / prev_close * 100) if prev_close else 0.0
            out[name] = {"ltp": ltp, "change": change, "change_pct": change_pct}
        except Exception:
            continue
    return out


@st.cache_data(ttl=20, show_spinner=False)
def get_live_quotes(instruments: list[Instrument]) -> dict[str, dict]:
    """Batch 'live' (a few minutes' lag, free-tier) quotes for a list of
    instruments. Returns {trading_symbol: {"ltp", "volume", "change",
    "change_pct"}}. Cached 20s so we don't hammer Yahoo on every rerun."""
    out = {}
    for inst in instruments:
        try:
            hist = yf.Ticker(f"{inst.trading_symbol}.NS").history(period="5d", interval="1d")
            hist = hist.dropna(subset=["Close"])  # Yahoo sometimes appends an incomplete/NaN row
            if hist.empty:
                continue
            last = hist.iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else last["Close"]
            ltp = float(last["Close"])
            change = ltp - float(prev_close)
            change_pct = (change / prev_close * 100) if prev_close else 0.0
            out[inst.trading_symbol] = {
                "ltp": ltp,
                "volume": int(last["Volume"]),
                "change": change,
                "change_pct": change_pct,
            }
        except Exception:
            continue  # skip symbols Yahoo has trouble with rather than crash the app
    return out


@st.cache_data(ttl=30, show_spinner=False)
def get_intraday_candles(instrument_token: str, exchange_segment: str = "nse_cm",
                          interval: str = "1m") -> pd.DataFrame:
    """1-minute OHLCV candles for the most recent trading session, used for
    VWAP / EMA / Supertrend / volume-surge / momentum charts and checks.

    Uses a 5-day lookback rather than "1d" because Yahoo's "1d" period is a
    calendar day, not a trading day -- on a weekend or right after a
    holiday, "1d" can return nothing at all. Pulling 5 days and keeping only
    the most recent date that actually has data reliably gets you "the last
    real trading session" regardless of what day it is right now.
    """
    try:
        df = yf.Ticker(f"{instrument_token}.NS").history(period="5d", interval=interval)
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return df
    df = df.rename(columns={c: c.lower() for c in df.columns})
    expected = ["open", "high", "low", "close", "volume"]
    for col in expected:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[expected].dropna(subset=["open", "high", "low", "close"])
    if df.empty:
        return df
    last_date = df.index.date.max()
    return df[df.index.date == last_date]
