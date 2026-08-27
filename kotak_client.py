"""
kotak_client.py
----------------
Thin wrapper around the official Kotak Neo Python SDK (neo_api_client).

WHY THIS FILE EXISTS
Kotak Neo's SDK is not on PyPI under a stable name — it's installed straight
from GitHub (see requirements.txt). Its exact login handshake has changed
across SDK versions (v1 used login() + session_2fa(otp), v2 uses
totp_login()). Because this sandbox has no network path to Kotak's servers,
none of this has been tested against a live account. Treat this file as a
correct-by-documentation starting point, run it once with your real
credentials, and adjust the exact call signatures if Kotak has tweaked them
by the time you deploy (check https://github.com/Kotak-Neo/Kotak-neo-api-v2
for the current docs).

CREDENTIALS NEEDED (put these in Streamlit secrets, never in code):
    KOTAK_CONSUMER_KEY     -> from Neo web/app: Invest > Trade API > generate app
    KOTAK_CONSUMER_SECRET  -> same screen
    KOTAK_MOBILE_NUMBER    -> your registered mobile, "+91XXXXXXXXXX"
    KOTAK_UCC              -> your client code (visible in your Neo profile)
    KOTAK_TOTP_SECRET      -> the TOTP seed you registered for API 2FA
                              (NOT a 6-digit code — the underlying secret,
                              so the app can generate fresh codes itself)
    KOTAK_MPIN             -> your 6-digit trading MPIN
"""

from __future__ import annotations

import io
import time
import datetime as dt
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import pyotp
import requests
import streamlit as st

try:
    from neo_api_client import NeoAPI
except ImportError:
    NeoAPI = None  # surfaced as a friendly error in the UI, see get_client()

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def market_is_open(now: Optional[dt.datetime] = None) -> bool:
    """NSE cash market hours: 9:15–15:30 IST, Monday–Friday."""
    now = now or dt.datetime.now(IST)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    open_t = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= now <= close_t


@st.cache_resource(show_spinner=False)
def get_client() -> "NeoAPI":
    """Create and log in a single shared Kotak Neo session for the app's lifetime.

    st.cache_resource means this runs once per server process, not once per
    request/rerun — important because logging in repeatedly will burn through
    Kotak's session limits and OTP/TOTP rate limits.
    """
    if NeoAPI is None:
        raise RuntimeError(
            "neo_api_client is not installed. Check requirements.txt — it must "
            "install from the Kotak-Neo GitHub repo, not PyPI."
        )

    secrets = st.secrets
    totp_code = pyotp.TOTP(secrets["KOTAK_TOTP_SECRET"]).now()

    client = NeoAPI(
        consumer_key=secrets["KOTAK_CONSUMER_KEY"],
        consumer_secret=secrets["KOTAK_CONSUMER_SECRET"],
        environment="prod",
        access_token=None,
        neo_fin_key=None,
    )

    # --- TOTP login (v2 SDK) ---
    client.totp_login(
        mobilenumber=secrets["KOTAK_MOBILE_NUMBER"],
        ucc=secrets["KOTAK_UCC"],
        totp=totp_code,
    )
    # Some SDK builds require a second MPIN validation step to finish the
    # session — if totp_login() alone doesn't fully authenticate on your
    # account, uncomment the line below (method name per current docs):
    # client.totp_validate(mpin=secrets["KOTAK_MPIN"])

    return client


@dataclass
class Instrument:
    trading_symbol: str
    instrument_token: str
    exchange_segment: str = "nse_cm"


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def get_nse_equity_universe() -> list[Instrument]:
    """Pull the *official* NSE cash-market instrument master from Kotak Neo.

    This is the mechanism that satisfies "no hardcoded stock names": Kotak
    publishes a downloadable scrip-master file rather than requiring a
    free-text search call, so we get the full live universe without ever
    hitting the search-rate-limit problem the notepad warned about.

    Cached for 12h — the tradeable-symbol list does not change intraday.
    """
    client = get_client()
    file_paths = client.scrip_master(exchange_segment="nse_cm")
    # Response shape varies by SDK version: usually a dict with a CSV URL.
    url = file_paths.get("filesPaths", file_paths.get("data", [None]))[0] \
        if isinstance(file_paths, dict) else file_paths[0]

    csv_bytes = requests.get(url, timeout=30).content
    df = pd.read_csv(io.BytesIO(csv_bytes))

    # Column names vary slightly by export version — normalise defensively.
    cols = {c.lower(): c for c in df.columns}
    sym_col = cols.get("ptrdsymbol") or cols.get("trading_symbol") or cols.get("symbol")
    tok_col = cols.get("pinstrumenttoken") or cols.get("instrument_token") or cols.get("token")
    series_col = cols.get("pgroup") or cols.get("series")

    if series_col:
        df = df[df[series_col].astype(str).str.upper().isin(["EQ", "BE"])]

    universe = [
        Instrument(trading_symbol=str(row[sym_col]), instrument_token=str(row[tok_col]))
        for _, row in df.iterrows()
        if pd.notna(row[sym_col]) and pd.notna(row[tok_col])
    ]
    return universe


def get_live_quotes(instruments: list[Instrument]) -> dict[str, dict]:
    """Batch live LTP/volume/OHLC quotes for a list of instruments.

    Returns {trading_symbol: {"ltp":..., "volume":..., "change":..., "change_pct":...}}
    """
    client = get_client()
    tokens = [
        {"instrument_token": i.instrument_token, "exchange_segment": i.exchange_segment}
        for i in instruments
    ]
    raw = client.quotes(instrument_tokens=tokens, quote_type="all")
    out = {}
    data = raw.get("data", raw) if isinstance(raw, dict) else raw
    for row, inst in zip(data, instruments):
        out[inst.trading_symbol] = {
            "ltp": float(row.get("ltp", row.get("last_traded_price", 0)) or 0),
            "volume": int(row.get("volume", row.get("total_traded_volume", 0)) or 0),
            "change": float(row.get("change", 0) or 0),
            "change_pct": float(row.get("percentage_change", row.get("change_percentage", 0)) or 0),
        }
    return out


@st.cache_data(ttl=10, show_spinner=False)
def get_intraday_candles(instrument_token: str, exchange_segment: str = "nse_cm",
                          interval: str = "1minute") -> pd.DataFrame:
    """1-minute OHLCV candles for the current session, used for VWAP / EMA /
    Supertrend / volume-surge / momentum. Cached for 10s to match the app's
    own refresh cadence — avoids re-fetching the same candle set on every
    Streamlit rerun within that window.
    """
    client = get_client()
    today = dt.datetime.now(IST).strftime("%Y-%m-%d")
    raw = client.historical_chart(
        exchange_segment=exchange_segment,
        instrument_token=instrument_token,
        interval=interval,
        from_date=today,
        to_date=today,
    )
    data = raw.get("data", raw) if isinstance(raw, dict) else raw
    df = pd.DataFrame(data)
    if df.empty:
        return df
    rename = {c: c.lower() for c in df.columns}
    df = df.rename(columns=rename)
    expected = ["open", "high", "low", "close", "volume"]
    for col in expected:
        if col not in df.columns:
            df[col] = pd.NA
    return df[expected].dropna(how="all")
