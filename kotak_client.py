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
from dataclasses import dataclass
from typing import Optional

import pandas as pd
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
    """Returns the curated liquid-stock list above. Cached for 12h (list
    barely changes)."""
    return [Instrument(trading_symbol=s) for s in NSE_LIQUID_UNIVERSE]


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
            hist = yf.Ticker(f"{inst.trading_symbol}.NS").history(period="2d", interval="1d")
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
    """1-minute OHLCV candles for the current session, used for VWAP / EMA /
    Supertrend / volume-surge / momentum. `instrument_token` here is just
    the trading symbol (see Instrument dataclass above).
    """
    try:
        df = yf.Ticker(f"{instrument_token}.NS").history(period="1d", interval=interval)
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return df
    df = df.rename(columns={c: c.lower() for c in df.columns})
    expected = ["open", "high", "low", "close", "volume"]
    for col in expected:
        if col not in df.columns:
            df[col] = pd.NA
    return df[expected].dropna(how="all")
