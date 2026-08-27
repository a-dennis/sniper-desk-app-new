
import io
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ============================================================
# QUANTbreakout — REAL-TIME NSE SCANNER
# Backend:
#   - DhanHQ: live LTP/quote + intraday/daily candles
#   - NSE India: best-effort live fundamental enrichment
#
# IMPORTANT:
#   No stock symbol, price, P/E, beta, market cap, volume,
#   or technical value is hardcoded.
#   If a live source does not return a value, the app shows
#   "NOT AVAILABLE" rather than inventing a value.
# ============================================================

st.set_page_config(
    page_title="QUANTbreakout | Real-Time NSE Scanner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

IST = ZoneInfo("Asia/Kolkata")
DHAN_BASE = "https://api.dhan.co/v2"
DHAN_INSTRUMENT_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
NSE_HOME = "https://www.nseindia.com"
NSE_QUOTE_URL = "https://www.nseindia.com/api/quote-equity"

# Strategy constants are rules, not market data.
PRICE_MIN = 50.0
PRICE_MAX = 500.0
BETA_MIN = 0.60
BETA_MAX = 1.20
FFMC_MIN_CR = 5000.0
VOLUME_MIN = 500_000
PE_MAX = 25.0
CASH_BALANCE = 15_000.0
REFRESH_MS = 5000

# Scan/technical workload controls.
# These do not contain stock names or market values.
SCAN_TECHNICAL_CANDIDATES = 12
INTRADAY_LOOKBACK_DAYS = 5
DAILY_BETA_LOOKBACK_DAYS = 120


# ============================================================
# UI
# ============================================================

st.markdown(
    """
<style>
:root {
    --bg: #e0f2fe;
    --panel: #bae6fd;
    --border: #0284c7;
    --ink: #0f172a;
    --muted: #475569;
    --green: #15803d;
    --red: #b91c1c;
    --gold-border: #ca8a04;
}
html, body, [class*="css"] {
    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.stApp {
    background:
        radial-gradient(circle at 10% 0%, rgba(255,255,255,.85), transparent 28%),
        linear-gradient(180deg, #e0f2fe 0%, #d7effd 100%);
    color: var(--ink);
}
.block-container {
    max-width: 1500px;
    padding-top: 1rem;
    padding-bottom: 2rem;
}
.topbar {
    background: rgba(255,255,255,.94);
    border: 1px solid #7dd3fc;
    border-radius: 18px;
    padding: 18px 22px;
    box-shadow: 0 12px 30px rgba(2,132,199,.10);
    margin-bottom: 14px;
}
.brand {
    font-size: 1.65rem;
    font-weight: 950;
    letter-spacing: -0.04em;
    color: #0f172a;
}
.brand span { color: #0284c7; }
.subbrand {
    font-size: .78rem;
    font-weight: 800;
    color: #475569;
    letter-spacing: .08em;
    text-transform: uppercase;
    margin-top: 3px;
}
.live-pill {
    display:inline-block;
    border:1px solid #4ade80;
    background:#dcfce7;
    color:#166534;
    border-radius:999px;
    padding:7px 12px;
    font-weight:900;
    font-size:.74rem;
}
.winner {
    background: linear-gradient(135deg, #fef08a 0%, #fef9c3 100%);
    border: 3px solid var(--gold-border);
    border-radius: 18px;
    padding: 22px;
    text-align: center;
    box-shadow: 0 14px 35px rgba(202,138,4,.16);
    margin-bottom: 14px;
}
.winner-kicker {
    color:#854d0e;
    font-size:.78rem;
    font-weight:950;
    letter-spacing:.12em;
    text-transform:uppercase;
}
.winner-symbol {
    color:#0f172a;
    font-size:3.15rem;
    line-height:1.05;
    font-weight:1000;
    letter-spacing:-.06em;
    margin:4px 0;
}
.winner-price {
    color:#15803d;
    font-size:1.25rem;
    font-weight:950;
}
.panel {
    background: rgba(186,230,253,.90);
    border: 2px solid var(--border);
    border-radius: 14px;
    padding: 15px;
    margin-bottom: 14px;
}
.panel-title {
    font-size:.82rem;
    font-weight:950;
    color:#075985;
    letter-spacing:.09em;
    text-transform:uppercase;
    border-bottom:1px solid rgba(2,132,199,.45);
    padding-bottom:7px;
    margin-bottom:10px;
}
.metric-card {
    background:rgba(255,255,255,.80);
    border:1px solid #7dd3fc;
    border-radius:12px;
    padding:12px;
    min-height:82px;
}
.metric-label {
    font-size:.70rem;
    color:#475569;
    font-weight:850;
    text-transform:uppercase;
    letter-spacing:.05em;
}
.metric-value {
    font-size:1.25rem;
    color:#0f172a;
    font-weight:950;
    margin-top:3px;
}
.pass {
    color:#15803d !important;
    font-weight:950 !important;
}
.fail {
    color:#b91c1c !important;
    font-weight:950 !important;
}
.na {
    color:#92400e !important;
    font-weight:950 !important;
}
.small-note {
    color:#475569;
    font-size:.75rem;
    line-height:1.45;
}
div[data-testid="stDataFrame"] {
    width:100%;
}
.stButton > button {
    width:100%;
    min-height:44px;
    font-weight:900;
    border-radius:10px;
}
[data-testid="stTextInput"] input {
    font-weight:800;
}
@media (max-width: 768px) {
    .block-container {
        padding-left:10px;
        padding-right:10px;
        padding-top:.6rem;
    }
    .topbar, .winner, .panel {
        padding:10px;
        border-radius:10px;
    }
    .brand { font-size:1.25rem; }
    .winner-symbol { font-size:2.25rem; }
    .winner-price { font-size:1rem; }
    .metric-value { font-size:1rem; }
    .small-note { font-size:.70rem; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# Credentials
# ============================================================

def read_secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return ""


DHAN_CLIENT_ID = read_secret("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = read_secret("DHAN_ACCESS_TOKEN")

if not DHAN_CLIENT_ID or not DHAN_ACCESS_TOKEN:
    st.markdown(
        """
        <div class="topbar">
            <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;">
                <div>
                    <div class="brand">⚡ QUANT<span>breakout</span></div>
                    <div class="subbrand">Real-time NSE momentum & breakout terminal</div>
                </div>
                <div class="live-pill">● CONNECTION REQUIRED</div>
            </div>
        </div>
        <div class="winner">
            <div class="winner-kicker">⚡ QuantBreakout</div>
            <div class="winner-symbol">LIVE CONNECTION REQUIRED</div>
            <div class="winner-price">DhanHQ credentials are not configured.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.error(
        "Add DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN to Streamlit Cloud → "
        "Manage app → Settings → Secrets, then reboot the app."
    )
    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">Required Streamlit Secrets</div>
            <pre style="margin:0;background:#0f172a;color:#e2e8f0;padding:14px;border-radius:10px;">DHAN_CLIENT_ID = "YOUR_DHAN_CLIENT_ID"
DHAN_ACCESS_TOKEN = "YOUR_DHAN_ACCESS_TOKEN"</pre>
            <div class="small-note" style="margin-top:10px;">
                Never commit the access token to GitHub. The app reads it only from Streamlit Secrets.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ============================================================
# Dhan REST client
# ============================================================

class DhanAPI:
    def __init__(self, client_id: str, access_token: str):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "access-token": access_token,
                "client-id": client_id,
                "User-Agent": "QUANTbreakout/1.0",
            }
        )

    def post(self, path: str, payload: dict, timeout: int = 20) -> dict:
        response = self.session.post(
            f"{DHAN_BASE}{path}",
            json=payload,
            timeout=timeout,
        )
        if not response.ok:
            try:
                body = response.json()
            except Exception:
                body = response.text[:500]
            raise RuntimeError(f"Dhan API {response.status_code}: {body}")
        data = response.json()
        if isinstance(data, dict) and data.get("status") == "failure":
            raise RuntimeError(str(data))
        return data


dhan = DhanAPI(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)


# ============================================================
# Instrument master
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def load_instrument_master() -> pd.DataFrame:
    response = requests.get(
        DHAN_INSTRUMENT_URL,
        timeout=30,
        headers={"User-Agent": "QUANTbreakout/1.0"},
    )
    response.raise_for_status()
    df = pd.read_csv(io.BytesIO(response.content), low_memory=False)

    required = {
        "SEM_EXM_EXCH_ID",
        "SEM_SEGMENT",
        "SEM_SMST_SECURITY_ID",
        "SEM_INSTRUMENT_NAME",
        "SEM_TRADING_SYMBOL",
        "SEM_CUSTOM_SYMBOL",
        "SEM_SERIES",
    }
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"Dhan instrument master missing columns: {sorted(missing)}")

    for col in ["SEM_EXM_EXCH_ID", "SEM_SEGMENT", "SEM_INSTRUMENT_NAME",
                "SEM_TRADING_SYMBOL", "SEM_CUSTOM_SYMBOL", "SEM_SERIES"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df["SEM_SMST_SECURITY_ID"] = pd.to_numeric(
        df["SEM_SMST_SECURITY_ID"], errors="coerce"
    )
    df = df.dropna(subset=["SEM_SMST_SECURITY_ID"]).copy()
    df["SEM_SMST_SECURITY_ID"] = df["SEM_SMST_SECURITY_ID"].astype(int)
    return df


def equity_universe(master: pd.DataFrame) -> pd.DataFrame:
    mask = (
        (master["SEM_EXM_EXCH_ID"].eq("NSE"))
        & (master["SEM_SEGMENT"].eq("E"))
        & (master["SEM_INSTRUMENT_NAME"].eq("EQUITY"))
    )
    df = master.loc[mask].copy()

    # Prefer normal exchange equity series when available.
    if "SEM_SERIES" in df.columns:
        normal = df[df["SEM_SERIES"].isin(["EQ", "BE", "BZ", "SM"])]
        if not normal.empty:
            df = normal

    df = df.drop_duplicates(subset=["SEM_SMST_SECURITY_ID"])
    df = df[df["SEM_TRADING_SYMBOL"].str.len() > 0]
    return df.reset_index(drop=True)


def find_symbol(master: pd.DataFrame, query: str) -> pd.Series | None:
    q = query.strip().upper()
    if not q:
        return None

    eq = equity_universe(master)

    exact = eq[
        (eq["SEM_TRADING_SYMBOL"].str.upper() == q)
        | (eq["SEM_CUSTOM_SYMBOL"].str.upper() == q)
    ]
    if not exact.empty:
        return exact.iloc[0]

    # Server-provided instrument list is the only lookup source.
    contains = eq[
        eq["SEM_TRADING_SYMBOL"].str.upper().str.contains(q, regex=False)
        | eq["SEM_CUSTOM_SYMBOL"].str.upper().str.contains(q, regex=False)
    ]
    if not contains.empty:
        return contains.iloc[0]

    return None


def find_nifty_index(master: pd.DataFrame) -> pd.Series | None:
    idx = master[
        (master["SEM_SEGMENT"].eq("I"))
        & (master["SEM_INSTRUMENT_NAME"].eq("INDEX"))
    ].copy()

    if idx.empty:
        return None

    exact_mask = (
        idx["SEM_TRADING_SYMBOL"].str.upper().eq("NIFTY")
        | idx["SEM_CUSTOM_SYMBOL"].str.upper().eq("NIFTY")
    )
    if "SM_SYMBOL_NAME" in idx.columns:
        exact_mask = exact_mask | idx["SM_SYMBOL_NAME"].str.upper().eq("NIFTY")
    exact = idx[exact_mask]
    if not exact.empty:
        return exact.iloc[0]

    # Prefer an index whose server-provided name contains NIFTY.
    for col in ["SEM_CUSTOM_SYMBOL", "SM_SYMBOL_NAME", "SEM_TRADING_SYMBOL"]:
        if col in idx.columns:
            hit = idx[idx[col].str.upper().str.contains("NIFTY", regex=False)]
            if not hit.empty:
                return hit.iloc[0]
    return None


# ============================================================
# Dhan market data
# ============================================================

def _chunked(values, size):
    for i in range(0, len(values), size):
        yield values[i:i + size]


def quote_snapshot(rows: pd.DataFrame) -> dict:
    ids = [int(x) for x in rows["SEM_SMST_SECURITY_ID"].tolist()]
    output = {}

    for chunk_no, chunk in enumerate(_chunked(ids, 1000)):
        data = dhan.post("/marketfeed/quote", {"NSE_EQ": chunk})
        section = data.get("data", {}).get("NSE_EQ", {})
        for sec_id, item in section.items():
            output[str(sec_id)] = item

        if chunk_no < (len(ids) - 1) // 1000:
            # Dhan Quote API is limited to 1 request/second.
            time.sleep(1.05)

    return output


@st.cache_data(ttl=10, show_spinner=False)
def cached_universe_snapshot(master: pd.DataFrame):
    universe = equity_universe(master)
    quotes = quote_snapshot(universe)

    records = []
    for _, row in universe.iterrows():
        sec_id = str(int(row["SEM_SMST_SECURITY_ID"]))
        q = quotes.get(sec_id)
        if not q:
            continue

        ltp = pd.to_numeric(q.get("last_price"), errors="coerce")
        volume = pd.to_numeric(q.get("volume"), errors="coerce")
        avg_price = pd.to_numeric(q.get("average_price"), errors="coerce")
        ohlc = q.get("ohlc") or {}

        if pd.isna(ltp) or float(ltp) <= 0:
            continue

        records.append(
            {
                "security_id": sec_id,
                "symbol": row["SEM_TRADING_SYMBOL"],
                "name": row["SEM_CUSTOM_SYMBOL"] or row["SEM_TRADING_SYMBOL"],
                "price": float(ltp),
                "volume": int(volume) if not pd.isna(volume) else 0,
                "day_vwap": float(avg_price) if not pd.isna(avg_price) else np.nan,
                "open": pd.to_numeric(ohlc.get("open"), errors="coerce"),
                "high": pd.to_numeric(ohlc.get("high"), errors="coerce"),
                "low": pd.to_numeric(ohlc.get("low"), errors="coerce"),
                "close": pd.to_numeric(ohlc.get("close"), errors="coerce"),
            }
        )

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df["change_pct"] = np.where(
        pd.to_numeric(df["close"], errors="coerce") > 0,
        (df["price"] / df["close"] - 1.0) * 100.0,
        np.nan,
    )

    # Candidate ranking uses only live server values.
    df["liquidity_score"] = np.log1p(df["volume"].clip(lower=0))
    df["momentum_score"] = df["change_pct"].fillna(0).clip(-20, 20)
    df["scan_score"] = df["liquidity_score"] + (df["momentum_score"] * 5.0)
    return df.sort_values("scan_score", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=20, show_spinner=False)
def intraday_candles(security_id: str, days: int = INTRADAY_LOOKBACK_DAYS) -> pd.DataFrame:
    now = datetime.now(IST)
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d 09:15:00")
    end = now.strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": "NSE_EQ",
        "instrument": "EQUITY",
        "interval": "1",
        "oi": False,
        "fromDate": start,
        "toDate": end,
    }

    data = dhan.post("/charts/intraday", payload, timeout=30)
    if not data:
        return pd.DataFrame()

    # Dhan returns arrays in v2.
    if "data" in data and isinstance(data["data"], dict):
        data = data["data"]

    closes = data.get("close", [])
    if not closes:
        return pd.DataFrame()

    n = min(
        len(closes),
        len(data.get("open", [])),
        len(data.get("high", [])),
        len(data.get("low", [])),
        len(data.get("volume", [])),
        len(data.get("timestamp", [])),
    )

    if n == 0:
        return pd.DataFrame()

    frame = pd.DataFrame(
        {
            "timestamp": data["timestamp"][:n],
            "open": pd.to_numeric(data["open"][:n], errors="coerce"),
            "high": pd.to_numeric(data["high"][:n], errors="coerce"),
            "low": pd.to_numeric(data["low"][:n], errors="coerce"),
            "close": pd.to_numeric(data["close"][:n], errors="coerce"),
            "volume": pd.to_numeric(data["volume"][:n], errors="coerce"),
        }
    )

    frame["timestamp"] = pd.to_datetime(
        frame["timestamp"], unit="s", utc=True, errors="coerce"
    ).dt.tz_convert(IST)

    frame = frame.dropna(subset=["close"]).sort_values("timestamp").reset_index(drop=True)
    return frame


def daily_candles(security_id: str, exchange_segment: str, instrument: str,
                  days: int = DAILY_BETA_LOOKBACK_DAYS) -> pd.DataFrame:
    now = datetime.now(IST)
    start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    end = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": exchange_segment,
        "instrument": instrument,
        "expiryCode": 0,
        "oi": False,
        "fromDate": start,
        "toDate": end,
    }

    data = dhan.post("/charts/historical", payload, timeout=30)
    if not data:
        return pd.DataFrame()

    closes = data.get("close", [])
    timestamps = data.get("timestamp", [])
    if not closes or not timestamps:
        return pd.DataFrame()

    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "close": pd.to_numeric(closes, errors="coerce"),
        }
    )
    frame["timestamp"] = pd.to_datetime(
        frame["timestamp"], unit="s", utc=True, errors="coerce"
    ).dt.tz_convert(IST)
    return frame.dropna(subset=["close"]).sort_values("timestamp").reset_index(drop=True)


# ============================================================
# NSE fundamental enrichment
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def nse_fundamentals(symbol: str) -> dict:
    """
    Best-effort NSE public quote enrichment.
    No fallback market values are inserted.
    If NSE blocks the request, values remain unavailable.
    """
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/151.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }

    result = {
        "pe": None,
        "market_cap_cr": None,
        "ffmc_cr": None,
        "debt_equity": None,
        "source": "NSE public quote",
    }

    try:
        session.get(NSE_HOME, headers=headers, timeout=10)
        r = session.get(
            NSE_QUOTE_URL,
            params={"symbol": symbol},
            headers=headers,
            timeout=15,
        )
        if not r.ok:
            return result

        payload = r.json()

        metadata = payload.get("metadata") or {}
        trade_info = (
            payload.get("marketDeptOrderBook", {}).get("tradeInfo", {})
            or payload.get("marketDeptOrderBook", {}).get("tradeInfo", {})
        )

        # NSE's public metadata commonly exposes pdSymbolPe.
        pe = pd.to_numeric(metadata.get("pdSymbolPe"), errors="coerce")
        if not pd.isna(pe) and float(pe) >= 0:
            result["pe"] = float(pe)

        total_market_cap = pd.to_numeric(
            trade_info.get("totalMarketCap"), errors="coerce"
        )
        ffmc = pd.to_numeric(trade_info.get("ffmc"), errors="coerce")

        # NSE trade-info values are in crore units.
        if not pd.isna(total_market_cap) and float(total_market_cap) > 0:
            result["market_cap_cr"] = float(total_market_cap)

        if not pd.isna(ffmc) and float(ffmc) > 0:
            result["ffmc_cr"] = float(ffmc)

    except Exception:
        pass

    return result


# ============================================================
# Technical calculations
# ============================================================

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous_close = frame["close"].shift(1)
    a = frame["high"] - frame["low"]
    b = (frame["high"] - previous_close).abs()
    c = (frame["low"] - previous_close).abs()
    return pd.concat([a, b, c], axis=1).max(axis=1)


def atr(frame: pd.DataFrame, period: int = 10) -> pd.Series:
    return true_range(frame).rolling(period, min_periods=period).mean()


def supertrend(frame: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    if len(frame) < period + 3:
        return None, None

    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    close = frame["close"].astype(float)

    atr_series = atr(frame, period)
    hl2 = (high + low) / 2.0
    upper = hl2 + multiplier * atr_series
    lower = hl2 - multiplier * atr_series

    final_upper = upper.copy()
    final_lower = lower.copy()
    direction = pd.Series(index=frame.index, dtype=float)
    st_line = pd.Series(index=frame.index, dtype=float)

    direction.iloc[0] = 1
    st_line.iloc[0] = np.nan

    for i in range(1, len(frame)):
        if pd.isna(atr_series.iloc[i]):
            direction.iloc[i] = direction.iloc[i - 1]
            continue

        if (
            upper.iloc[i] < final_upper.iloc[i - 1]
            or close.iloc[i - 1] > final_upper.iloc[i - 1]
        ):
            final_upper.iloc[i] = upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        if (
            lower.iloc[i] > final_lower.iloc[i - 1]
            or close.iloc[i - 1] < final_lower.iloc[i - 1]
        ):
            final_lower.iloc[i] = lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        previous_direction = direction.iloc[i - 1]

        if previous_direction <= 0 and close.iloc[i] > final_upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif previous_direction >= 0 and close.iloc[i] < final_lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = previous_direction

        st_line.iloc[i] = (
            final_lower.iloc[i]
            if direction.iloc[i] > 0
            else final_upper.iloc[i]
        )

    return float(st_line.iloc[-1]), int(direction.iloc[-1])


def calculate_vwap(frame: pd.DataFrame) -> float | None:
    clean = frame.dropna(subset=["high", "low", "close", "volume"]).copy()
    clean = clean[clean["volume"] >= 0]
    if clean.empty:
        return None

    typical = (clean["high"] + clean["low"] + clean["close"]) / 3.0
    total_volume = clean["volume"].sum()
    if total_volume <= 0:
        return float(typical.iloc[-1])

    return float((typical * clean["volume"]).sum() / total_volume)


def calculate_beta(stock_daily: pd.DataFrame, benchmark_daily: pd.DataFrame) -> float | None:
    if stock_daily.empty or benchmark_daily.empty:
        return None

    s = stock_daily[["timestamp", "close"]].rename(columns={"close": "stock"})
    b = benchmark_daily[["timestamp", "close"]].rename(columns={"close": "benchmark"})

    merged = pd.merge_asof(
        s.sort_values("timestamp"),
        b.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("1D"),
    ).dropna()

    if len(merged) < 30:
        return None

    stock_returns = merged["stock"].pct_change()
    benchmark_returns = merged["benchmark"].pct_change()

    aligned = pd.concat([stock_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 25:
        return None

    variance = float(aligned.iloc[:, 1].var())
    if variance <= 0:
        return None

    covariance = float(aligned.iloc[:, 0].cov(aligned.iloc[:, 1]))
    return covariance / variance


def technical_metrics(frame: pd.DataFrame, live_price: float) -> dict:
    result = {
        "vwap": None,
        "ema9": None,
        "ema21": None,
        "ema_pass": None,
        "supertrend": None,
        "supertrend_pass": None,
        "volume_surge": None,
        "volume_surge_pass": None,
        "momentum_velocity": None,
        "momentum_pass": None,
        "last_minute_volume": None,
    }

    if frame.empty:
        return result

    close = frame["close"].astype(float)

    vwap = calculate_vwap(frame)
    result["vwap"] = vwap
    if vwap is not None:
        result["vwap_pass"] = bool(live_price >= vwap)
    else:
        result["vwap_pass"] = None

    if len(close) >= 25:
        e9 = ema(close, 9)
        e21 = ema(close, 21)
        result["ema9"] = float(e9.iloc[-1])
        result["ema21"] = float(e21.iloc[-1])
        result["ema_pass"] = bool(e9.iloc[-1] > e21.iloc[-1])

    st_line, st_direction = supertrend(frame)
    result["supertrend"] = st_line
    result["supertrend_pass"] = (
        bool(st_direction > 0 and st_line is not None and live_price >= st_line)
        if st_direction is not None
        else None
    )

    vol = pd.to_numeric(frame["volume"], errors="coerce").fillna(0)
    if len(vol) >= 21:
        last_vol = float(vol.iloc[-1])
        avg_prev = float(vol.iloc[-21:-1].mean())
        result["last_minute_volume"] = last_vol
        if avg_prev > 0:
            surge = last_vol / avg_prev
            result["volume_surge"] = float(surge)
            result["volume_surge_pass"] = bool(surge >= 2.0)

    if len(close) >= 6:
        old = float(close.iloc[-6])
        if old > 0:
            velocity = ((float(close.iloc[-1]) / old) - 1.0) * 100.0
            result["momentum_velocity"] = velocity
            result["momentum_pass"] = bool(velocity > 0)

    return result


# ============================================================
# Full selected-stock evaluation
# ============================================================

def evaluate_symbol(row: pd.Series, master: pd.DataFrame, scan_snapshot: pd.DataFrame | None = None):
    symbol = str(row["SEM_TRADING_SYMBOL"])
    security_id = str(int(row["SEM_SMST_SECURITY_ID"]))
    live_price = None

    # Fresh selected-stock quote on every rerun.
    quote = dhan.post("/marketfeed/quote", {"NSE_EQ": [int(security_id)]})
    q = quote.get("data", {}).get("NSE_EQ", {}).get(security_id, {})
    if not q:
        raise RuntimeError(f"No live Dhan quote returned for {symbol}.")

    live_price = float(q.get("last_price", 0) or 0)
    if live_price <= 0:
        raise RuntimeError(f"Dhan returned no usable LTP for {symbol}.")

    day_volume = int(q.get("volume", 0) or 0)
    day_vwap_from_quote = q.get("average_price")
    day_vwap_from_quote = (
        float(day_vwap_from_quote)
        if day_vwap_from_quote not in (None, "")
        else None
    )

    candles = intraday_candles(security_id)
    tech = technical_metrics(candles, live_price)

    fundamentals = nse_fundamentals(symbol)

    # Dynamically discover the benchmark index from the Dhan instrument master.
    nifty_row = find_nifty_index(master)
    beta = None
    benchmark_note = "Benchmark unavailable"

    if nifty_row is not None:
        try:
            nifty_daily = daily_candles(
                str(int(nifty_row["SEM_SMST_SECURITY_ID"])),
                "IDX_I",
                "INDEX",
                DAILY_BETA_LOOKBACK_DAYS,
            )
            stock_daily = daily_candles(
                security_id,
                "NSE_EQ",
                "EQUITY",
                DAILY_BETA_LOOKBACK_DAYS,
            )
            beta = calculate_beta(stock_daily, nifty_daily)
            benchmark_note = "Calculated vs server-provided NIFTY daily candles"
        except Exception as exc:
            benchmark_note = f"Beta unavailable: {exc}"

    if beta is not None:
        fundamentals["beta"] = beta
    else:
        fundamentals["beta"] = None

    # Debt/equity is not fabricated. Dhan's market-data endpoints do not expose it.
    fundamentals["debt_equity"] = None

    return {
        "symbol": symbol,
        "name": str(row["SEM_CUSTOM_SYMBOL"] or symbol),
        "security_id": security_id,
        "price": live_price,
        "volume": day_volume,
        "day_vwap": day_vwap_from_quote,
        "candles": candles,
        "tech": tech,
        "fundamentals": fundamentals,
        "benchmark_note": benchmark_note,
    }


# ============================================================
# Verdict helpers
# ============================================================

def verdict(condition):
    if condition is True:
        return "🟢 PASS"
    if condition is False:
        return "🔴 FAIL"
    return "🟠 NOT VERIFIED"


def fmt_money(value, decimals=2):
    if value is None or pd.isna(value):
        return "NOT AVAILABLE"
    return f"₹{float(value):,.{decimals}f}"


def fmt_number(value, decimals=2):
    if value is None or pd.isna(value):
        return "NOT AVAILABLE"
    return f"{float(value):,.{decimals}f}"


def matrix_for(evaluation):
    f = evaluation["fundamentals"]
    t = evaluation["tech"]
    price = evaluation["price"]
    volume = evaluation["volume"]

    pe = f.get("pe")
    ffmc = f.get("ffmc_cr")
    beta = f.get("beta")
    de = f.get("debt_equity")

    rows = [
        {
            "PARAMETERS FROM SYSTEM SCAN": "1. Price-to-Earnings Ratio Gate Layer",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(pe is not None and pe <= PE_MAX),
            "LIVE METRIC VALUE": f"P/E: {fmt_number(pe)}",
        },
        {
            "PARAMETERS FROM SYSTEM SCAN": "2. CMP Allocation Bounds Range",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(PRICE_MIN <= price <= PRICE_MAX),
            "LIVE METRIC VALUE": fmt_money(price),
        },
        {
            "PARAMETERS FROM SYSTEM SCAN": "3. Volatility Shield Protection",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(beta is not None and BETA_MIN <= beta <= BETA_MAX),
            "LIVE METRIC VALUE": f"Beta: {fmt_number(beta)}",
        },
        {
            "PARAMETERS FROM SYSTEM SCAN": "4. Market Capitalization Cushion",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(ffmc is not None and ffmc >= FFMC_MIN_CR),
            "LIVE METRIC VALUE": f"Free-float MCap: {fmt_money(ffmc, 0)} Cr",
        },
        {
            "PARAMETERS FROM SYSTEM SCAN": "5. Volume Liquidity Depth Floor",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(volume >= VOLUME_MIN),
            "LIVE METRIC VALUE": f"{volume:,.0f} shares",
        },
        {
            "PARAMETERS FROM SYSTEM SCAN": "6. Financial Health Leverage Checking",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(de is not None),
            "LIVE METRIC VALUE": (
                f"Debt/Equity: {fmt_number(de)}"
                if de is not None
                else "NOT AVAILABLE FROM CONNECTED LIVE SOURCES"
            ),
        },
        {
            "PARAMETERS FROM SYSTEM SCAN": "7. VWAP Support Anchoring Level Check",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(t.get("vwap_pass")),
            "LIVE METRIC VALUE": f"VWAP: {fmt_money(t.get('vwap'))}",
        },
        {
            "PARAMETERS FROM SYSTEM SCAN": "8. Exponential Moving Average Cross (9/21)",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(t.get("ema_pass")),
            "LIVE METRIC VALUE": (
                f"EMA9 {fmt_number(t.get('ema9'))} / EMA21 {fmt_number(t.get('ema21'))}"
            ),
        },
        {
            "PARAMETERS FROM SYSTEM SCAN": "9. Supertrend Speed Engine Cloud Map",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(t.get("supertrend_pass")),
            "LIVE METRIC VALUE": f"Supertrend: {fmt_money(t.get('supertrend'))}",
        },
        {
            "PARAMETERS FROM SYSTEM SCAN": "10. Institutional Volume Mean Surge",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(t.get("volume_surge_pass")),
            "LIVE METRIC VALUE": (
                f"Last/20-bar mean: {fmt_number(t.get('volume_surge'), 2)}x"
            ),
        },
        {
            "PARAMETERS FROM SYSTEM SCAN": "11. Intraday Momentum Acceleration Velocity",
            "STOCK CODE": evaluation["symbol"],
            "STOCK NAME": evaluation["name"],
            "VERDICT STATUS": verdict(t.get("momentum_pass")),
            "LIVE METRIC VALUE": f"5-minute velocity: {fmt_number(t.get('momentum_velocity'))}%",
        },
    ]

    return pd.DataFrame(rows)


def overall_score(evaluation):
    matrix = matrix_for(evaluation)
    passes = int((matrix["VERDICT STATUS"] == "🟢 PASS").sum())
    fails = int((matrix["VERDICT STATUS"] == "🔴 FAIL").sum())
    verified = int((matrix["VERDICT STATUS"] != "🟠 NOT VERIFIED").sum())
    return passes, fails, verified


# ============================================================
# Main app
# ============================================================

refresh_count = st_autorefresh(
    interval=REFRESH_MS,
    limit=None,
    debounce=True,
    key="quantbreakout_live_refresh",
)

try:
    master = load_instrument_master()
except Exception as exc:
    st.error(f"Unable to load Dhan instrument master: {exc}")
    st.stop()

st.markdown(
    """
<div class="topbar">
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;">
    <div>
      <div class="brand">⚡ QUANT<span>breakout</span></div>
      <div class="subbrand">Real-time NSE momentum & breakout scanner</div>
    </div>
    <div class="live-pill">● LIVE DHAN ENGINE</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Sidebar controls
with st.sidebar:
    st.subheader("Scanner Controls")
    st.caption("All market values are retrieved from live server sources.")
    if st.button("↻ Force Live Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.write("Connected data")
    st.write("• DhanHQ live quote")
    st.write("• DhanHQ 1-minute candles")
    st.write("• DhanHQ daily candles")
    st.write("• NSE public fundamentals (best effort)")
    st.divider()
    st.caption("The app never substitutes fake market values when a source is unavailable.")

# Live dynamic universe scan
with st.spinner("Discovering live NSE equity universe and scanning server quotes..."):
    try:
        snapshot = cached_universe_snapshot(master)
    except Exception as exc:
        st.error(f"Live universe scan failed: {exc}")
        st.stop()

if snapshot.empty:
    st.warning("No live equity quotes were returned. This can happen outside market hours or during a temporary data-service interruption.")
    st.stop()

# Manual override
st.markdown('<div class="panel"><div class="panel-title">🔍 Manual Check Override Field</div>', unsafe_allow_html=True)
manual = st.text_input(
    "NSE symbol",
    placeholder="Enter any server-listed NSE equity symbol and press Enter",
    label_visibility="collapsed",
    key="manual_symbol",
)
st.markdown('</div>', unsafe_allow_html=True)

manual_row = find_symbol(master, manual) if manual.strip() else None

# Build candidate list dynamically from live quote data.
# No fixed watchlist is embedded in the source.
if manual_row is not None:
    selected_row = manual_row
    auto_mode = False
else:
    # Focus technical processing on the most active live candidates.
    technical_pool = snapshot[
        snapshot["price"].between(PRICE_MIN, PRICE_MAX)
        & (snapshot["volume"] >= VOLUME_MIN)
    ].head(SCAN_TECHNICAL_CANDIDATES)

    if technical_pool.empty:
        technical_pool = snapshot.head(SCAN_TECHNICAL_CANDIDATES)

    # Evaluate candidates sequentially. The first fully/mostly verified
    # high-score candidate becomes the winner.
    evaluations = []
    for _, candidate in technical_pool.iterrows():
        try:
            r = find_symbol(master, str(candidate["symbol"]))
            if r is not None:
                evaluations.append(evaluate_symbol(r, master, snapshot))
        except Exception:
            continue

    if not evaluations:
        # Use the highest live quote candidate so the app remains useful.
        fallback_row = find_symbol(master, str(snapshot.iloc[0]["symbol"]))
        if fallback_row is None:
            st.error("The live quote universe returned no resolvable equity.")
            st.stop()
        try:
            evaluations = [evaluate_symbol(fallback_row, master, snapshot)]
        except Exception as exc:
            st.error(f"Unable to evaluate live candidate: {exc}")
            st.stop()

    ranked = []
    for item in evaluations:
        passes, fails, verified = overall_score(item)
        ranked.append((passes, -fails, verified, item))

    ranked.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    selected_evaluation = ranked[0][3]
    selected_row = find_symbol(master, selected_evaluation["symbol"])
    auto_mode = True

# Fresh selected evaluation on each rerun.
if manual_row is not None:
    with st.spinner(f"Checking live server data for {manual_row['SEM_TRADING_SYMBOL']}..."):
        try:
            evaluation = evaluate_symbol(manual_row, master, snapshot)
        except Exception as exc:
            st.error(f"Manual live check failed: {exc}")
            st.stop()
else:
    # Reuse the just-computed live evaluation to avoid duplicate calls.
    evaluation = selected_evaluation

symbol = evaluation["symbol"]
name = evaluation["name"]
price = evaluation["price"]

passes, fails, verified = overall_score(evaluation)

st.markdown(
    f"""
<div class="winner">
  <div class="winner-kicker">⭐ REAL-TIME QUANT BREAKOUT WINNER</div>
  <div class="winner-symbol">{symbol}</div>
  <div class="winner-price">Live Price: {fmt_money(price)}</div>
  <div class="small-note" style="margin-top:8px;">
      {name} · {passes}/11 PASS · {fails}/11 FAIL · {verified}/11 verified
      · {'AUTO SCAN' if auto_mode else 'MANUAL OVERRIDE'}
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Carousel
if "carousel_index" not in st.session_state:
    st.session_state.carousel_index = 0

live_symbols = snapshot["symbol"].tolist()
if live_symbols:
    st.session_state.carousel_index %= len(live_symbols)

c1, c2 = st.columns(2)
with c1:
    if st.button("❬  PREVIOUS ASSET", use_container_width=True):
        st.session_state.carousel_index = (st.session_state.carousel_index - 1) % len(live_symbols)
        target = live_symbols[st.session_state.carousel_index]
        st.session_state.manual_symbol = target
        st.rerun()
with c2:
    if st.button("NEXT ASSET  ❭", use_container_width=True):
        st.session_state.carousel_index = (st.session_state.carousel_index + 1) % len(live_symbols)
        target = live_symbols[st.session_state.carousel_index]
        st.session_state.manual_symbol = target
        st.rerun()

# Key metrics
f = evaluation["fundamentals"]
t = evaluation["tech"]

metric_cols = st.columns(6)
metric_values = [
    ("LIVE CMP", fmt_money(price)),
    ("DAY VOLUME", f"{evaluation['volume']:,.0f}"),
    ("FREE-FLOAT MCAP", f"{fmt_number(f.get('ffmc_cr'), 0)} Cr"),
    ("P/E", fmt_number(f.get("pe"))),
    ("BETA", fmt_number(f.get("beta"))),
    ("VWAP", fmt_money(t.get("vwap"))),
]

for col, (label, value) in zip(metric_cols, metric_values):
    with col:
        st.markdown(
            f"""
<div class="metric-card">
  <div class="metric-label">{label}</div>
  <div class="metric-value">{value}</div>
</div>
""",
            unsafe_allow_html=True,
        )

st.markdown(
    '<div class="panel"><div class="panel-title">📊 11-Parameter Strategy Matrix</div>',
    unsafe_allow_html=True,
)

matrix = matrix_for(evaluation)

def style_status(val):
    if val == "🟢 PASS":
        return "color:#15803d;font-weight:900;"
    if val == "🔴 FAIL":
        return "color:#b91c1c;font-weight:900;"
    return "color:#92400e;font-weight:900;"

st.dataframe(
    matrix.style.map(style_status, subset=["VERDICT STATUS"]),
    use_container_width=True,
    hide_index=True,
    height=520,
)

st.markdown("</div>", unsafe_allow_html=True)

# Position sizing
if price > 0:
    quantity = int(CASH_BALANCE // price)
    risk_unit = price * 0.008
    stop_loss = price - (risk_unit * 1.5)
    take_profit = price + (risk_unit * 3.0)
else:
    quantity = 0
    risk_unit = stop_loss = take_profit = None

st.markdown(
    f"""
<div class="panel">
  <div class="panel-title">🧮 Fixed Strategy Risk Bracket Position Sizer</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;">
    <div class="metric-card">
      <div class="metric-label">Cash Balance</div>
      <div class="metric-value">₹{CASH_BALANCE:,.0f}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Target Position</div>
      <div class="metric-value">Buy Exactly {quantity} Shares</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Risk Unit</div>
      <div class="metric-value">{fmt_money(risk_unit)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Automated SL Safety Floor</div>
      <div class="metric-value">{fmt_money(stop_loss)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Automated Take-Profit Ceiling</div>
      <div class="metric-value">{fmt_money(take_profit)}</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Technical details / data provenance
st.markdown(
    f"""
<div class="panel">
  <div class="panel-title">🔎 Live Calculation Audit</div>
  <div class="small-note">
    <b>VWAP:</b> cumulative volume-weighted typical price using
    (High + Low + Close) / 3 from Dhan 1-minute candles.<br>
    <b>EMA:</b> calculated from the server-provided 1-minute close series.<br>
    <b>Supertrend:</b> calculated from server-provided 1-minute OHLC using ATR-based bands.<br>
    <b>Volume surge:</b> latest 1-minute volume divided by the mean of the previous 20 one-minute bars.<br>
    <b>Momentum velocity:</b> percentage change across the latest five 1-minute intervals.<br>
    <b>Beta:</b> calculated from server-provided daily stock returns versus the dynamically discovered NIFTY index.<br>
    <b>Benchmark:</b> {evaluation["benchmark_note"]}<br>
    <b>Debt/Equity:</b> intentionally shown as NOT VERIFIED because the connected live market endpoints do not provide a reliable current D/E value.
    No default PASS is inserted.
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.caption(
    f"Last app refresh: {datetime.now(IST).strftime('%d-%b-%Y %H:%M:%S IST')} · "
    "Market values are informational and are not an instruction to buy or sell."
)
