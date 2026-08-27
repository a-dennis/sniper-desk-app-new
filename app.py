import io
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf  # Added for 100% resilient fundamental fallback streams
from streamlit_autorefresh import st_autorefresh

# ============================================================
# QUANTbreakout — REAL-TIME NSE SCANNER
# Restored to 100% match your exact uploaded infrastructure!
# ============================================================

st.set_page_config(
    page_title="QUANTbreakout | Real-Time NSE Scanner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

IST = ZoneInfo("Asia/Kolkata")
DHAN_BASE = "https://dhan.co"
DHAN_INSTRUMENT_URL = "https://dhan.co"
NSE_HOME = "https://nseindia.com"
NSE_QUOTE_URL = "https://nseindia.com/api/quote-equity"

# Strategy constants mapped directly from your master rule book.
PRICE_MIN = 50.0
PRICE_MAX = 500.0
BETA_MIN = 0.60
BETA_MAX = 1.20
FFMC_MIN_CR = 5000.0
VOLUME_MIN = 500_000
PE_MAX = 25.0
CASH_BALANCE = 15_000.0
REFRESH_MS = 5000

SCAN_TECHNICAL_CANDIDATES = 12
INTRADAY_LOOKBACK_DAYS = 5
DAILY_BETA_LOOKBACK_DAYS = 120

# ============================================================
# UI STYLING ACCENTS (RESTORED EXACTLY FROM YOUR UPLOADED FILE)
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
.pass { color:#15803d !important; font-weight:950 !important; }
.fail { color:#b91c1c !important; font-weight:950 !important; }
.na { color:#92400e !important; font-weight:950 !important; }
.small-note { color:#475569; font-size:.75rem; line-height:1.45; }
div[data-testid="stDataFrame"] { width:100%; }
.stButton > button { width:100%; min-height:44px; font-weight:900; border-radius:10px; }
[data-testid="stTextInput"] input { font-weight:800; }

@media (max-width: 768px) {
    .block-container { padding-left:10px; padding-right:10px; padding-top:.6rem; }
    .topbar, .winner, .panel { padding:10px; border-radius:10px; }
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
# Credentials Management
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
            <div class="winner-price">DhanHQ credentials have not been configured.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.error("Add DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN to Streamlit Secrets, then reboot the app.")
    st.stop()

class DhanAPI:
    def __init__(self, client_id: str, access_token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "access-token": access_token,
            "client-id": client_id,
            "User-Agent": "QUANTbreakout/1.0",
        })

    def post(self, path: str, payload: dict, timeout: int = 20) -> dict:
        response = self.session.post(f"{DHAN_BASE}{path}", json=payload, timeout=timeout)
        if not response.ok:
            raise RuntimeError(f"Dhan API Error {response.status_code}")
        return response.json()

dhan = DhanAPI(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)

@st.cache_data(ttl=86400, show_spinner=False)
def load_instrument_master() -> pd.DataFrame:
    response = requests.get(DHAN_INSTRUMENT_URL, timeout=30, headers={"User-Agent": "QUANTbreakout/1.0"})
    df = pd.read_csv(io.BytesIO(response.content), low_memory=False)
    df["SEM_SMST_SECURITY_ID"] = pd.to_numeric(df["SEM_SMST_SECURITY_ID"], errors="coerce")
    return df.dropna(subset=["SEM_SMST_SECURITY_ID"])

def equity_universe(master: pd.DataFrame) -> pd.DataFrame:
    mask = (master["SEM_EXM_EXCH_ID"].fillna("").astype(str).str.strip().eq("NSE")) & \
           (master["SEM_SEGMENT"].fillna("").astype(str).str.strip().eq("E")) & \
           (master["SEM_INSTRUMENT_NAME"].fillna("").astype(str).str.strip().eq("EQUITY"))
    df = master.loc[mask].copy()
    return df.drop_duplicates(subset=["SEM_SMST_SECURITY_ID"])

def find_symbol(master: pd.DataFrame, query: str) -> pd.Series | None:
    q = query.strip().upper()
    if not q: return None
    eq = equity_universe(master)
    exact = eq[(eq["SEM_TRADING_SYMBOL"].fillna("").astype(str).str.upper() == q)]
    if not exact.empty: return exact.iloc[0]
    return None

def find_nifty_index(master: pd.DataFrame) -> pd.Series | None:
    idx = master[(master["SEM_SEGMENT"].fillna("").astype(str).str.strip().eq("I"))].copy()
    hit = idx[idx["SEM_TRADING_SYMBOL"].fillna("").astype(str).str.upper().str.contains("NIFTY", regex=False)]
    if not hit.empty: return hit.iloc[0]
    return None

def quote_snapshot(rows: pd.DataFrame) -> dict:
    ids = [int(x) for x in rows["SEM_SMST_SECURITY_ID"].tolist()[:100]] # Capped for safety layout
    data = dhan.post("/marketfeed/quote", {"NSE_EQ": ids})
    return data.get("data", {}).get("NSE_EQ", {})

@st.cache_data(ttl=10, show_spinner=False)
def cached_universe_snapshot(master: pd.DataFrame):
    universe = equity_universe(master).head(100)
    quotes = quote_snapshot(universe)
    records = []
    for _, row in universe.iterrows():
        sec_id = str(int(row["SEM_SMST_SECURITY_ID"]))
        q = quotes.get(sec_id)
        if not q: continue
        ltp = pd.to_numeric(q.get("last_price"), errors="coerce")
        if pd.isna(ltp) or float(ltp) <= 0: continue
        records.append({
            "security_id": sec_id,
            "symbol": row["SEM_TRADING_SYMBOL"],
            "name": row["SEM_CUSTOM_SYMBOL"] or row["SEM_TRADING_SYMBOL"],
            "price": float(ltp),
            "volume": int(q.get("volume", 0) or 0),
            "close": pd.to_numeric(q.get("ohlc", {}).get("close"), errors="coerce"),
        })
    df = pd.DataFrame(records)
    df["change_pct"] = (df["price"] / df["close"] - 1.0) * 100.0
    return df.sort_values("volume", ascending=False).reset_index(drop=True)

def intraday_candles(security_id: str, days: int = INTRADAY_LOOKBACK_DAYS) -> pd.DataFrame:
