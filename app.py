```python
import io
import math
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st

# ============================================================
# QUANTbreakout
# DhanHQ REAL-TIME NSE DATA ENGINE
# ============================================================

st.set_page_config(
    page_title="QUANTbreakout",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# STRATEGY CONFIGURATION
# These are rules, NOT stock data.
# ============================================================

PE_MAX = 25.0
CMP_MIN = 50.0
CMP_MAX = 500.0
BETA_MIN = 0.60
BETA_MAX = 1.20
MARKET_CAP_MIN_CR = 5000.0
VOLUME_MIN = 500_000

EMA_FAST = 9
EMA_SLOW = 21

VOLUME_SURGE_MULTIPLIER = 2.0

CAPITAL = 15000.0
RISK_PERCENT = 0.008
SL_MULTIPLIER = 1.5
TP_MULTIPLIER = 3.0

DHAN_BASE = "https://api.dhan.co/v2"
INSTRUMENT_MASTER_URL = (
    "https://images.dhan.co/api-data/"
    "api-scrip-master-detailed.csv"
)

# ============================================================
# DHAN CREDENTIALS
# Add these through Streamlit Secrets.
# ============================================================

DHAN_ACCESS_TOKEN = st.secrets.get(
    "DHAN_ACCESS_TOKEN",
    ""
)

DHAN_CLIENT_ID = st.secrets.get(
    "DHAN_CLIENT_ID",
    ""
)

# ============================================================
# UI
# ============================================================

st.markdown(
    """
<style>

@import url(
'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap'
);

html, body, [class*="css"] {
    font-family: Inter, sans-serif !important;
}

.stApp {
    background:
        radial-gradient(
            circle at 10% 0%,
            rgba(255,255,255,.75),
            transparent 28%
        ),
        linear-gradient(
            180deg,
            #e0f2fe 0%,
            #d9effb 100%
        );
}

.block-container {
    max-width: 1500px;
    padding-top: 12px;
}

#MainMenu,
footer,
header {
    visibility: hidden;
}

.topbar {
    display:flex;
    justify-content:space-between;
    align-items:center;

    padding:12px 16px;

    background:rgba(255,255,255,.65);

    border:
        1px solid
        #0284c7;

    border-radius:14px;

    margin-bottom:12px;

    box-shadow:
        0 8px 25px
        rgba(2,132,199,.10);
}

.logo {
    font-size:1.35rem;
    font-weight:900;
    color:#075985;
}

.logo span {
    color:#0f172a;
}

.live {
    background:#dcfce7;
    border:1px solid #22c55e;
    color:#166534;

    padding:5px 10px;

    border-radius:999px;

    font-size:.68rem;
    font-weight:900;
}

.winner {
    text-align:center;

    padding:24px 15px;

    border:
        3px solid
        #ca8a04;

    border-radius:18px;

    background:
        linear-gradient(
            135deg,
            #fef08a,
            #fef9c3,
            #fff7b0
        );

    box-shadow:
        0 12px 35px
        rgba(202,138,4,.18);

    margin-bottom:12px;
}

.winner-label {
    font-size:.76rem;
    font-weight:900;
    letter-spacing:1.3px;
    color:#854d0e;
}

.winner-symbol {
    font-size:
        clamp(
            2.7rem,
            8vw,
            5rem
        );

    line-height:1;

    margin-top:5px;

    font-weight:900;

    color:#0f172a;
}

.winner-name {
    margin-top:7px;

    font-size:.85rem;

    color:#475569;

    font-weight:600;
}

.winner-price {
    margin-top:9px;

    font-size:1.55rem;

    color:#15803d;

    font-weight:900;
}

.panel {
    background:
        rgba(186,230,253,.78);

    border:
        1px solid
        #0284c7;

    border-radius:14px;

    padding:14px;

    margin-bottom:12px;

    box-shadow:
        0 6px 18px
        rgba(2,132,199,.08);
}

.panel-title {
    font-size:.78rem;
    font-weight:900;

    color:#075985;

    letter-spacing:.9px;

    text-transform:uppercase;

    margin-bottom:10px;
}

.matrix {
    width:100%;

    border-collapse:
        separate;

    border-spacing:0;

    border:
        1px solid
        #0284c7;

    border-radius:10px;

    overflow:hidden;

    font-size:.76rem;
}

.matrix th {
    background:#075985;
    color:white;

    padding:9px;

    text-align:left;

    font-weight:800;
}

.matrix td {
    padding:8px 9px;

    border-top:
        1px solid
        rgba(2,132,199,.18);

    background:
        rgba(255,255,255,.48);

    color:#0f172a;
}

.pass {
    color:#15803d;
    font-weight:900;
}

.fail {
    color:#b91c1c;
    font-weight:900;
}

.na {
    color:#64748b;
    font-weight:800;
}

.position {
    background:
        linear-gradient(
            135deg,
            #bae6fd,
            #e0f2fe
        );

    border:
        2px solid
        #0284c7;

    border-radius:15px;

    padding:15px;
}

.position-title {
    color:#075985;

    font-weight:900;

    font-size:.78rem;

    letter-spacing:1px;

    text-transform:uppercase;

    margin-bottom:10px;
}

.position-grid {
    display:grid;

    grid-template-columns:
        repeat(4,1fr);

    gap:9px;
}

.position-item {
    background:
        rgba(255,255,255,.55);

    border-radius:10px;

    padding:10px;
}

.position-label {
    font-size:.62rem;

    color:#475569;

    font-weight:800;
}

.position-value {
    margin-top:4px;

    font-size:1rem;

    font-weight:900;
}

@media(max-width:768px){

    .block-container {
        padding:
            7px 10px 18px !important;
    }

    .winner {
        padding:19px 10px;
    }

    .winner-symbol {
        font-size:2.8rem;
    }

    .position-grid {
        grid-template-columns:
            repeat(2,1fr);
    }

    .matrix {
        font-size:.66rem;
    }

    .matrix th,
    .matrix td {
        padding:6px;
    }
}

</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# AUTHENTICATION CHECK
# ============================================================

if not DHAN_ACCESS_TOKEN or not DHAN_CLIENT_ID:

    st.markdown(
        """
<div class="winner">

<div class="winner-label">
⚡ QUANTBREAKOUT
</div>

<div class="winner-symbol">
LIVE DATA CONNECTION
</div>

<div class="winner-name">
DhanHQ credentials are not configured.
</div>

</div>
""",
        unsafe_allow_html=True,
    )

    st.info(
        "Add DHAN_ACCESS_TOKEN and DHAN_CLIENT_ID "
        "to Streamlit Secrets."
    )

    st.stop()


# ============================================================
# DHAN HEADERS
# ============================================================

HEADERS = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": DHAN_CLIENT_ID,
    "Content-Type": "application/json",
    "Accept": "application/json",
}


# ============================================================
# LOAD DYNAMIC INSTRUMENT UNIVERSE
# ============================================================

@st.cache_data(ttl=3600)
def load_instruments():

    response = requests.get(
        INSTRUMENT_MASTER_URL,
        timeout=20,
    )

    response.raise_for_status()

    df = pd.read_csv(
        io.BytesIO(response.content),
        low_memory=False,
    )

    return df


def get_nse_equity_universe():

    df = load_instruments()

    # Dynamically identify relevant columns.
    exchange_col = next(
        (
            c for c in df.columns
            if c.upper() in
            [
                "EXCH_ID",
                "SEM_EXM_EXCH_ID"
            ]
        ),
        None,
    )

    segment_col = next(
        (
            c for c in df.columns
            if c.upper() in
            [
                "SEGMENT",
                "SEM_SEGMENT"
            ]
        ),
        None,
    )

    security_col = next(
        (
            c for c in df.columns
            if c.upper() in
            [
                "SECURITY_ID",
                "SEM_SMST_SECURITY_ID"
            ]
        ),
        None,
    )

    symbol_col = next(
        (
            c for c in df.columns
            if c.upper() in
            [
                "SYMBOL_NAME",
                "SEM_CUSTOM_SYMBOL",
                "DISPLAY_NAME"
            ]
        ),
        None,
    )

    if not all(
        [
            exchange_col,
            segment_col,
            security_col,
            symbol_col,
        ]
    ):
        raise RuntimeError(
            "Dhan instrument-master column mapping "
            "could not be resolved."
        )

    mask = (
        df[exchange_col]
        .astype(str)
        .str.upper()
        .eq("NSE")
    )

    mask &= (
        df[segment_col]
        .astype(str)
        .str.upper()
        .str.contains("EQUITY")
    )

    universe = df.loc[
        mask,
        [
            security_col,
            symbol_col,
        ],
    ].copy()

    universe.columns = [
        "security_id",
        "symbol",
    ]

    universe["security_id"] = (
        universe["security_id"]
        .astype(str)
    )

    universe["symbol"] = (
        universe["symbol"]
        .astype(str)
        .str.strip()
    )

    universe = universe.drop_duplicates(
        subset=["security_id"]
    )

    universe = universe[
        universe["symbol"].ne("")
    ]

    return universe.reset_index(
        drop=True
    )


# ============================================================
# DHAN LIVE QUOTE API
# ============================================================

def chunks(items, size):

    for i in range(
        0,
        len(items),
        size,
    ):
        yield items[i:i + size]


def fetch_quotes(instruments):

    records = []

    # Dhan supports up to 1000 instruments
    # per market quote request.
    for batch in chunks(
        instruments,
        1000,
    ):

        payload = {
            "NSE_EQ": [
                int(x)
                for x in batch
            ]
        }

        response = requests.post(
            f"{DHAN_BASE}/marketfeed/quote",
            headers=HEADERS,
            json=payload,
            timeout=15,
        )

        response.raise_for_status()

        body = response.json()

        data = body.get(
            "data",
            {}
        )

        segment = data.get(
            "NSE_EQ",
            {}
        )

        for security_id, quote in segment.items():

            records.append(
                {
                    "security_id":
                        str(security_id),

                    "last_price":
                        quote.get(
                            "last_price"
                        ),

                    "volume":
                        quote.get(
                            "volume"
                        ),
                }
            )

    return pd.DataFrame(records)


# ============================================================
# INTRADAY CANDLES
# ============================================================

def fetch_intraday(
    security_id,
):

    now = datetime.now()

    start = now - timedelta(
        hours=8
    )

    payload = {
        "securityId":
            str(security_id),

        "exchangeSegment":
            "NSE_EQ",

        "instrument":
            "EQUITY",

        "interval":
            "1",

        "oi":
            False,

        "fromDate":
            start.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "toDate":
            now.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
    }

    response = requests.post(
        f"{DHAN_BASE}/charts/intraday",
        headers=HEADERS,
        json=payload,
        timeout=15,
    )

    response.raise_for_status()

    body = response.json()

    if not body:
        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "open":
                body.get("open", []),

            "high":
                body.get("high", []),

            "low":
                body.get("low", []),

            "close":
                body.get("close", []),

            "volume":
                body.get("volume", []),

            "timestamp":
                body.get(
                    "timestamp",
                    []
                ),
        }
    )

    for col in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    return df.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )


# ============================================================
# INDICATORS
# ============================================================

def vwap(df):

    if df.empty:
        return None

    typical = (
        df["high"]
        + df["low"]
        + df["close"]
    ) / 3

    volume = df["volume"]

    total_volume = volume.sum()

    if total_volume <= 0:
        return None

    return float(
        (
            typical * volume
        ).sum()
        / total_volume
    )


def ema(df, period):

    if len(df) < period:
        return None

    value = (
        df["close"]
        .ewm(
            span=period,
            adjust=False
        )
        .mean()
        .iloc[-1]
    )

    return float(value)


def volume_surge(df):

    if len(df) < 21:
        return None

    current = float(
        df["volume"].iloc[-1]
    )

    average = float(
        df["volume"]
        .iloc[-21:-1]
        .mean()
    )

    if average <= 0:
        return None

    return current / average


def supertrend(df):

    if len(df) < 12:
        return None

    period = 10
    multiplier = 3.0

    previous_close = (
        df["close"].shift(1)
    )

    tr = pd.concat(
        [
            df["high"]
            - df["low"],

            (
                df["high"]
                - previous_close
            ).abs(),

            (
                df["low"]
                - previous_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = (
        tr.rolling(period)
        .mean()
    )

    hl2 = (
        df["high"]
        + df["low"]
    ) / 2

    upper = (
        hl2
        + multiplier * atr
    )

    lower = (
        hl2
        - multiplier * atr
    )

    return bool(
        df["close"].iloc[-1]
        > upper.iloc[-1]
    )


# ============================================================
# POSITION CALCULATOR
# ============================================================

def position(price):

    if not price or price <= 0:
        return None

    shares = math.floor(
        CAPITAL / price
    )

    risk_unit = (
        price * RISK_PERCENT
    )

    stop_loss = (
        price
        - risk_unit * SL_MULTIPLIER
    )

    take_profit = (
        price
        + risk_unit * TP_MULTIPLIER
    )

    return (
        shares,
        risk_unit,
        stop_loss,
        take_profit,
    )


# ============================================================
# RENDER MATRIX
# ============================================================

def render_matrix(
    symbol,
    name,
    rows,
):

    html = """
<table class="matrix">

<thead>
<tr>
<th>PARAMETER</th>
<th>STOCK CODE</th>
<th>STOCK NAME</th>
<th>VERDICT</th>
<th>LIVE METRIC</th>
</tr>
</thead>

<tbody>
"""

    for parameter, metric, verdict in rows:

        if verdict is True:
            status = (
                '<span class="pass">'
                '🟢 PASS'
                '</span>'
            )

        elif verdict is False:
            status = (
                '<span class="fail">'
                '🔴 FAIL'
                '</span>'
            )

        else:
            status = (
                '<span class="na">'
                '⚪ DATA UNAVAILABLE'
                '</span>'
            )

        html += f"""
<tr>
<td>{parameter}</td>
<td>{symbol}</td>
<td>{name}</td>
<td>{status}</td>
<td>{metric}</td>
</tr>
"""

    html += """
</tbody>
</table>
"""

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


# ============================================================
# DYNAMIC SCANNER
# ============================================================

universe = get_nse_equity_universe()

st.markdown(
    f"""
<div class="topbar">

<div class="logo">
⚡ QUANT<span>breakout</span>
</div>

<div class="live">
● DHAN LIVE DATA
</div>

</div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# MANUAL CHECK
# ============================================================

st.markdown(
    """
<div class="panel">

<div class="panel-title">
🔍 Manual Check Override
</div>

""",
    unsafe_allow_html=True,
)

manual = st.text_input(
    "NSE Symbol",
    placeholder="Enter any NSE symbol",
    label_visibility="collapsed",
)

manual_button = st.button(
    "⚡ CHECK LIVE STOCK",
    use_container_width=True,
)

st.markdown(
    "</div>",
    unsafe_allow_html=True,
)

# ============================================================
# SELECT UNIVERSE
# ============================================================

if manual_button and manual:

    selected = universe[
        universe["symbol"]
        .str.upper()
        .eq(
            manual.strip().upper()
        )
    ]

    if selected.empty:

        st.error(
            "Symbol not found in the "
            "live Dhan instrument universe."
        )

        st.stop()

    scan_universe = selected

else:

    scan_universe = universe


# ============================================================
# QUOTE SCAN
# ============================================================

quote_df = fetch_quotes(
    scan_universe[
        "security_id"
    ].tolist()
)

if quote_df.empty:

    st.error(
        "Dhan returned no live quote data."
    )

    st.stop()


# ============================================================
# JOIN DYNAMIC SYMBOLS
# ============================================================

market = scan_universe.merge(
    quote_df,
    on="security_id",
    how="inner",
)

market["last_price"] = pd.to_numeric(
    market["last_price"],
    errors="coerce",
)

market["volume"] = pd.to_numeric(
    market["volume"],
    errors="coerce",
)

market = market.dropna(
    subset=["last_price"]
)

# ============================================================
# LIQUIDITY / PRICE FILTER
# ============================================================

market = market[
    (market["last_price"] >= CMP_MIN)
    &
    (market["last_price"] <= CMP_MAX)
]

market = market[
    market["volume"] >= VOLUME_MIN
]

# ============================================================
# SCAN TECHNICAL CANDIDATES
# ============================================================

results = []

# To avoid hammering the data API,
# technical candles are requested only
# after live quote/liquidity filtering.

for _, stock in market.iterrows():

    try:

        candles = fetch_intraday(
            stock["security_id"]
        )

        if candles.empty:
            continue

        price = float(
            stock["last_price"]
        )

        current_vwap = vwap(
            candles
        )

        ema9 = ema(
            candles,
            EMA_FAST
        )

        ema21 = ema(
            candles,
            EMA_SLOW
        )

        surge = volume_surge(
            candles
        )

        trend = supertrend(
            candles
        )

        # ====================================================
        # IMPORTANT:
        # Fundamentals such as P/E, Beta, Free-Float Market
        # Cap and Debt/Equity are NOT fabricated here.
        #
        # They must come from a licensed fundamentals source.
        # Therefore these remain DATA UNAVAILABLE until that
        # source is connected.
        # ====================================================

        rows = [

            (
                "Price-to-Earnings Ratio",
                "DATA SOURCE REQUIRED",
                None,
            ),

            (
                "CMP Allocation Bounds",
                f"₹{price:,.2f}",
                CMP_MIN
                <= price
                <= CMP_MAX,
            ),

            (
                "Volatility Shield / Beta",
                "DATA SOURCE REQUIRED",
                None,
            ),

            (
                "Free-Float Market Cap",
                "DATA SOURCE REQUIRED",
                None,
            ),

            (
                "Volume Liquidity Floor",
                f"{stock['volume']:,.0f}",
                stock["volume"]
                >= VOLUME_MIN,
            ),

            (
                "Debt-to-Equity",
                "DATA SOURCE REQUIRED",
                None,
            ),

            (
                "VWAP Support",
                "DATA UNAVAILABLE"
                if current_vwap is None
                else
                f"₹{current_vwap:,.4f}",

                None
                if current_vwap is None
                else
                price >= current_vwap,
            ),

            (
                "EMA 9 / 21",
                "DATA UNAVAILABLE"
                if ema9 is None
                or ema21 is None
                else
                f"₹{ema9:,.2f} / "
                f"₹{ema21:,.2f}",

                None
                if ema9 is None
                or ema21 is None
                else
                ema9 > ema21,
            ),

            (
                "Supertrend",
                "DATA UNAVAILABLE"
                if trend is None
                else
                (
                    "Bullish"
                    if trend
                    else
                    "Bearish"
                ),

                trend,
            ),

            (
                "Institutional Volume Surge",
                "DATA UNAVAILABLE"
                if surge is None
                else
                f"{surge:.2f}× average",

                None
                if surge is None
                else
                surge
                >= VOLUME_SURGE_MULTIPLIER,
            ),

            (
                "Intraday Momentum",
                "DATA SOURCE REQUIRED",
                None,
            ),
        ]

        available = [
            x[2]
            for x in rows
            if x[2] is not None
        ]

        passes = sum(
            1
            for x in available
            if x
        )

        fails = sum(
            1
            for x in available
            if not x
        )

        unavailable = (
            11 - len(available)
        )

        score = (
            passes / 11
        ) * 100

        results.append(
            {
                "symbol":
                    stock["symbol"],

                "price":
                    price,

                "volume":
                    stock["volume"],

                "rows":
                    rows,

                "passes":
                    passes,

                "fails":
                    fails,

                "unavailable":
                    unavailable,

                "score":
                    score,
            }
        )

    except Exception:
        continue


# ============================================================
# RANK
# ============================================================

if not results:

    st.warning(
        "No qualifying live market records "
        "were returned."
    )

    st.stop()

results.sort(
    key=lambda x: (
        x["passes"],
        x["score"],
        x["volume"],
    ),
    reverse=True,
)

winner = results[0]


# ============================================================
# WINNER
# ============================================================

st.markdown(
    f"""
<div class="winner">

<div class="winner-label">
⭐ REAL-TIME QUANT BREAKOUT WINNER
</div>

<div class="winner-symbol">
{winner["symbol"]}
</div>

<div class="winner-name">
Dynamically supplied by Dhan instrument universe
</div>

<div class="winner-price">
₹{winner["price"]:,.2f}
</div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# MATRIX
# ============================================================

st.markdown(
    """
<div class="panel">

<div class="panel-title">
📊 11-Parameter Strategy Matrix
</div>
""",
    unsafe_allow_html=True,
)

render_matrix(
    winner["symbol"],
    winner["symbol"],
    winner["rows"],
)

st.markdown(
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# POSITION
# ============================================================

p = position(
    winner["price"]
)

if p:

    shares, risk, sl, tp = p

    st.markdown(
        f"""
<div class="position">

<div class="position-title">
🧮 ₹15,000 Fixed Strategy Risk Bracket
</div>

<div class="position-grid">

<div class="position-item">
<div class="position-label">
BUY EXACTLY
</div>

<div class="position-value">
{shares} SHARES
</div>
</div>

<div class="position-item">
<div class="position-label">
RISK UNIT
</div>

<div class="position-value">
₹{risk:,.2f}
</div>
</div>

<div class="position-item">
<div class="position-label">
🔒 STOP LOSS
</div>

<div class="position-value">
₹{sl:,.2f}
</div>
</div>

<div class="position-item">
<div class="position-label">
🎯 TAKE PROFIT
</div>

<div class="position-value">
₹{tp:,.2f}
</div>
</div>

</div>

</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# STATUS
# ============================================================

st.markdown(
    f"""
<div style="
text-align:center;
margin-top:10px;
font-size:.68rem;
font-weight:800;
color:#475569;
">

LIVE DHAN MARKET DATA
•
{len(universe):,} DYNAMIC NSE EQUITY INSTRUMENTS
•
{len(results):,} TECHNICAL CANDIDATES
•
{datetime.now().strftime("%H:%M:%S")}

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# REFRESH
# ============================================================

time.sleep(10)
st.rerun()
```
