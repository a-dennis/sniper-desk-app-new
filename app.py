import io
import math
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# QUANTBREAKOUT
# REAL-TIME NSE SCANNER
# DhanHQ Market Data
# ============================================================

st.set_page_config(
    page_title="QUANTbreakout",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# STRATEGY SETTINGS
# These are strategy rules, NOT market data.
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

# Number of technically evaluated candidates.
# Stocks themselves are NEVER hardcoded.
MAX_TECHNICAL_CANDIDATES = 50

# Dhan market quote limit is 1000 instruments/request.
QUOTE_BATCH_SIZE = 1000

DHAN_BASE_URL = "https://api.dhan.co/v2"

INSTRUMENT_MASTER_URL = (
    "https://images.dhan.co/api-data/"
    "api-scrip-master-detailed.csv"
)


# ============================================================
# DHAN CREDENTIALS
# Store these in Streamlit Secrets.
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
# GLOBAL CSS
# ============================================================

st.markdown(
    """
<style>

@import url(
'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap'
);

html,
body,
[class*="css"] {
    font-family: Inter, sans-serif !important;
}

.stApp {
    background:
        radial-gradient(
            circle at 15% 0%,
            rgba(255,255,255,0.85),
            transparent 30%
        ),
        linear-gradient(
            180deg,
            #e0f2fe 0%,
            #dbeafe 100%
        );
}

.block-container {
    max-width: 1500px;
    padding-top: 12px;
    padding-bottom: 30px;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}


/* TOP HEADER */

.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;

    padding: 13px 17px;

    background: rgba(255,255,255,0.72);

    border:
        1px solid
        #0284c7;

    border-radius: 15px;

    margin-bottom: 12px;

    box-shadow:
        0 8px 25px
        rgba(2,132,199,0.10);
}

.logo {
    color: #075985;

    font-size: 1.35rem;

    font-weight: 900;

    letter-spacing: -0.5px;
}

.logo span {
    color: #0f172a;
}

.live-badge {
    background: #dcfce7;

    color: #166534;

    border:
        1px solid
        #22c55e;

    border-radius: 999px;

    padding: 5px 11px;

    font-size: 0.68rem;

    font-weight: 900;
}


/* WINNER */

.winner {
    text-align: center;

    padding: 24px 12px;

    background:
        linear-gradient(
            135deg,
            #fef08a,
            #fef9c3,
            #fff7b0
        );

    border:
        3px solid
        #ca8a04;

    border-radius: 18px;

    margin-bottom: 12px;

    box-shadow:
        0 12px 35px
        rgba(202,138,4,0.18);
}

.winner-label {
    color: #854d0e;

    font-size: 0.75rem;

    font-weight: 900;

    letter-spacing: 1.4px;
}

.winner-symbol {
    color: #0f172a;

    font-size:
        clamp(
            2.6rem,
            8vw,
            5rem
        );

    font-weight: 900;

    line-height: 1;

    margin-top: 7px;
}

.winner-price {
    color: #15803d;

    font-size: 1.55rem;

    font-weight: 900;

    margin-top: 10px;
}

.winner-meta {
    color: #475569;

    font-size: 0.75rem;

    font-weight: 700;

    margin-top: 5px;
}


/* PANELS */

.panel {
    background:
        rgba(186,230,253,0.78);

    border:
        1px solid
        #0284c7;

    border-radius: 14px;

    padding: 14px;

    margin-bottom: 12px;

    box-shadow:
        0 6px 18px
        rgba(2,132,199,0.08);
}

.panel-title {
    color: #075985;

    font-size: 0.78rem;

    font-weight: 900;

    letter-spacing: 0.9px;

    text-transform: uppercase;

    margin-bottom: 10px;
}


/* MATRIX */

.table-wrap {
    width: 100%;

    overflow-x: auto;

    border-radius: 10px;
}

.matrix {
    width: 100%;

    min-width: 720px;

    border-collapse: separate;

    border-spacing: 0;

    border:
        1px solid
        #0284c7;

    border-radius: 10px;

    overflow: hidden;

    font-size: 0.74rem;
}

.matrix th {
    background: #075985;

    color: #ffffff;

    padding: 9px;

    text-align: left;

    font-weight: 800;

    white-space: nowrap;
}

.matrix td {
    color: #0f172a;

    padding: 8px 9px;

    background:
        rgba(255,255,255,0.54);

    border-top:
        1px solid
        rgba(2,132,199,0.18);

    vertical-align: middle;
}

.pass {
    color: #15803d;

    font-weight: 900;
}

.fail {
    color: #b91c1c;

    font-weight: 900;
}

.unavailable {
    color: #64748b;

    font-weight: 800;
}


/* POSITION */

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

    border-radius: 15px;

    padding: 15px;

    margin-top: 12px;
}

.position-title {
    color: #075985;

    font-size: 0.78rem;

    font-weight: 900;

    letter-spacing: 1px;

    margin-bottom: 10px;
}

.position-grid {
    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 9px;
}

.position-item {
    background:
        rgba(255,255,255,0.58);

    border-radius: 10px;

    padding: 11px;
}

.position-label {
    color: #475569;

    font-size: 0.61rem;

    font-weight: 800;
}

.position-value {
    color: #0f172a;

    font-size: 1rem;

    font-weight: 900;

    margin-top: 4px;
}


/* SCORE */

.score-card {
    text-align: center;

    background:
        rgba(255,255,255,0.58);

    border:
        1px solid
        #0284c7;

    border-radius: 12px;

    padding: 12px;
}

.score-number {
    color: #075985;

    font-size: 1.7rem;

    font-weight: 900;
}

.score-label {
    color: #475569;

    font-size: 0.65rem;

    font-weight: 800;
}


/* STATUS */

.status-line {
    text-align: center;

    color: #475569;

    font-size: 0.67rem;

    font-weight: 800;

    margin-top: 10px;
}


/* MOBILE */

@media(max-width:768px) {

    .block-container {
        padding:
            7px 10px 20px !important;
    }

    .topbar {
        padding: 10px;
    }

    .logo {
        font-size: 1.05rem;
    }

    .winner {
        padding: 19px 10px;
    }

    .winner-symbol {
        font-size: 2.8rem;
    }

    .winner-price {
        font-size: 1.3rem;
    }

    .panel {
        padding: 10px;
    }

    .position-grid {
        grid-template-columns:
            repeat(2, 1fr);
    }

    .matrix {
        font-size: 0.65rem;
    }

    .matrix th,
    .matrix td {
        padding: 6px;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HELPER: API HEADERS
# ============================================================

def dhan_headers():

    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
    }


# ============================================================
# CREDENTIAL CHECK
# ============================================================

if not DHAN_ACCESS_TOKEN or not DHAN_CLIENT_ID:

    st.markdown(
        """
<div class="winner">

<div class="winner-label">
⚡ QUANTBREAKOUT
</div>

<div class="winner-symbol">
LIVE CONNECTION REQUIRED
</div>

<div class="winner-meta">
DhanHQ credentials have not been configured.
</div>

</div>
""",
        unsafe_allow_html=True,
    )

    st.error(
        "Add DHAN_ACCESS_TOKEN and DHAN_CLIENT_ID "
        "to Streamlit Secrets."
    )

    st.stop()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
<div class="topbar">

<div class="logo">
⚡ QUANT<span>breakout</span>
</div>

<div class="live-badge">
● DHAN LIVE
</div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# DYNAMIC INSTRUMENT MASTER
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_instrument_master():

    response = requests.get(
        INSTRUMENT_MASTER_URL,
        timeout=30,
    )

    response.raise_for_status()

    df = pd.read_csv(
        io.BytesIO(response.content),
        low_memory=False,
    )

    return df


def get_dynamic_nse_equities():

    df = load_instrument_master()

    required_columns = [
        "EXCH_ID",
        "SEGMENT",
        "INSTRUMENT",
        "SECURITY_ID",
        "SYMBOL_NAME",
        "DISPLAY_NAME",
    ]

    missing = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise RuntimeError(
            "Dhan instrument master changed. "
            f"Missing columns: {missing}"
        )

    result = df[
        (df["EXCH_ID"].astype(str).str.upper() == "NSE")
        &
        (df["SEGMENT"].astype(str).str.upper() == "E")
        &
        (
            df["INSTRUMENT"]
            .astype(str)
            .str.upper()
            == "EQUITY"
        )
    ].copy()

    result = result[
        [
            "SECURITY_ID",
            "SYMBOL_NAME",
            "DISPLAY_NAME",
        ]
    ]

    result.columns = [
        "security_id",
        "symbol",
        "name",
    ]

    result["security_id"] = (
        pd.to_numeric(
            result["security_id"],
            errors="coerce",
        )
    )

    result = result.dropna(
        subset=["security_id"]
    )

    result["security_id"] = (
        result["security_id"]
        .astype(int)
        .astype(str)
    )

    result["symbol"] = (
        result["symbol"]
        .astype(str)
        .str.strip()
    )

    result["name"] = (
        result["name"]
        .astype(str)
        .str.strip()
    )

    result = result[
        result["symbol"].ne("")
    ]

    result = result.drop_duplicates(
        subset=["security_id"]
    )

    return result.reset_index(
        drop=True
    )


# ============================================================
# CHUNK HELPER
# ============================================================

def chunks(items, size):

    for start in range(
        0,
        len(items),
        size,
    ):

        yield items[
            start:start + size
        ]


# ============================================================
# REAL-TIME DHAN QUOTE
# ============================================================

def fetch_live_quotes(
    security_ids,
):

    records = []

    batches = list(
        chunks(
            security_ids,
            QUOTE_BATCH_SIZE,
        )
    )

    for index, batch in enumerate(batches):

        payload = {
            "NSE_EQ": [
                int(x)
                for x in batch
            ]
        }

        response = requests.post(
            f"{DHAN_BASE_URL}/marketfeed/quote",
            headers=dhan_headers(),
            json=payload,
            timeout=20,
        )

        if response.status_code != 200:

            raise RuntimeError(
                "Dhan quote API error: "
                f"{response.status_code} "
                f"{response.text[:300]}"
            )

        body = response.json()

        data = body.get(
            "data",
            {},
        )

        nse = data.get(
            "NSE_EQ",
            {},
        )

        for security_id, quote in nse.items():

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

                    "average_price":
                        quote.get(
                            "average_price"
                        ),

                    "net_change":
                        quote.get(
                            "net_change"
                        ),

                    "day_high":
                        quote.get(
                            "ohlc",
                            {}
                        ).get(
                            "high"
                        ),

                    "day_low":
                        quote.get(
                            "ohlc",
                            {}
                        ).get(
                            "low"
                        ),

                    "day_open":
                        quote.get(
                            "ohlc",
                            {}
                        ).get(
                            "open"
                        ),

                    "previous_close":
                        quote.get(
                            "ohlc",
                            {}
                        ).get(
                            "close"
                        ),

                    "last_trade_time":
                        quote.get(
                            "last_trade_time"
                        ),
                }
            )

        # Dhan Quote API rate limit.
        if index < len(batches) - 1:
            time.sleep(1.05)

    if not records:

        return pd.DataFrame()

    result = pd.DataFrame(records)

    numeric_columns = [
        "last_price",
        "volume",
        "average_price",
        "net_change",
        "day_high",
        "day_low",
        "day_open",
        "previous_close",
    ]

    for column in numeric_columns:

        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    return result


# ============================================================
# REAL-TIME 1-MINUTE CANDLES
# ============================================================

def fetch_intraday_candles(
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
        f"{DHAN_BASE_URL}/charts/intraday",
        headers=dhan_headers(),
        json=payload,
        timeout=20,
    )

    if response.status_code != 200:

        return pd.DataFrame()

    body = response.json()

    if not body:

        return pd.DataFrame()

    length = len(
        body.get(
            "close",
            [],
        )
    )

    if length == 0:

        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "timestamp":
                body.get(
                    "timestamp",
                    [],
                ),

            "open":
                body.get(
                    "open",
                    [],
                ),

            "high":
                body.get(
                    "high",
                    [],
                ),

            "low":
                body.get(
                    "low",
                    [],
                ),

            "close":
                body.get(
                    "close",
                    [],
                ),

            "volume":
                body.get(
                    "volume",
                    [],
                ),
        }
    )

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )

    return df.reset_index(
        drop=True
    )


# ============================================================
# VWAP
# ============================================================

def calculate_vwap(df):

    if df.empty:
        return None

    typical_price = (
        df["high"]
        + df["low"]
        + df["close"]
    ) / 3.0

    volume = df["volume"]

    total_volume = volume.sum()

    if total_volume <= 0:
        return None

    return float(
        (
            typical_price
            * volume
        ).sum()
        / total_volume
    )


# ============================================================
# EMA
# ============================================================

def calculate_ema(
    df,
    period,
):

    if len(df) < period:

        return None

    value = (
        df["close"]
        .ewm(
            span=period,
            adjust=False,
        )
        .mean()
        .iloc[-1]
    )

    return float(value)


# ============================================================
# VOLUME SURGE
# ============================================================

def calculate_volume_surge(
    df,
):

    if len(df) < 21:

        return None

    current_volume = float(
        df["volume"].iloc[-1]
    )

    average_volume = float(
        df["volume"]
        .iloc[-21:-1]
        .mean()
    )

    if average_volume <= 0:

        return None

    return (
        current_volume
        / average_volume
    )


# ============================================================
# SUPERTREND
# ============================================================

def calculate_supertrend(
    df,
):

    if len(df) < 20:

        return None

    period = 10

    multiplier = 3.0

    previous_close = (
        df["close"].shift(1)
    )

    true_range = pd.concat(
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
        true_range
        .rolling(period)
        .mean()
    )

    hl2 = (
        df["high"]
        + df["low"]
    ) / 2.0

    upper_band = (
        hl2
        + multiplier * atr
    )

    lower_band = (
        hl2
        - multiplier * atr
    )

    close = df["close"]

    return bool(
        close.iloc[-1]
        > upper_band.iloc[-1]
    )


# ============================================================
# MOMENTUM ACCELERATION
# ============================================================

def calculate_momentum(
    df,
):

    if len(df) < 6:

        return None

    recent = (
        df["close"]
        .iloc[-1]
    )

    previous = (
        df["close"]
        .iloc[-6]
    )

    if previous <= 0:

        return None

    return float(
        (
            recent
            / previous
            - 1.0
        )
        * 100.0
    )


# ============================================================
# POSITION SIZER
# ============================================================

def calculate_position(
    live_price,
):

    if (
        live_price is None
        or live_price <= 0
    ):

        return None

    shares = math.floor(
        CAPITAL
        / live_price
    )

    risk_unit = (
        live_price
        * RISK_PERCENT
    )

    stop_loss = (
        live_price
        - (
            risk_unit
            * SL_MULTIPLIER
        )
    )

    take_profit = (
        live_price
        + (
            risk_unit
            * TP_MULTIPLIER
        )
    )

    return {
        "shares":
            shares,

        "risk_unit":
            risk_unit,

        "stop_loss":
            stop_loss,

        "take_profit":
            take_profit,
    }


# ============================================================
# MATRIX STATUS
# ============================================================

def verdict_html(
    verdict,
):

    if verdict is True:

        return (
            '<span class="pass">'
            "🟢 PASS"
            "</span>"
        )

    if verdict is False:

        return (
            '<span class="fail">'
            "🔴 FAIL"
            "</span>"
        )

    return (
        '<span class="unavailable">'
        "⚪ DATA UNAVAILABLE"
        "</span>"
    )


# ============================================================
# MATRIX RENDERER
# ============================================================

def render_matrix(
    symbol,
    name,
    rows,
):

    html = """
<div class="table-wrap">

<table class="matrix">

<thead>

<tr>

<th>
PARAMETERS FROM SYSTEM SCAN
</th>

<th>
STOCK CODE
</th>

<th>
STOCK NAME
</th>

<th>
VERDICT STATUS
</th>

<th>
LIVE METRIC VALUE
</th>

</tr>

</thead>

<tbody>
"""

    for row in rows:

        parameter = row["parameter"]

        metric = row["metric"]

        verdict = row["verdict"]

        html += f"""
<tr>

<td>
{parameter}
</td>

<td>
{symbol}
</td>

<td>
{name}
</td>

<td>
{verdict_html(verdict)}
</td>

<td>
{metric}
</td>

</tr>
"""

    html += """
</tbody>

</table>

</div>
"""

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


# ============================================================
# TECHNICAL EVALUATION
# ============================================================

def evaluate_stock(
    stock,
    candles,
):

    price = float(
        stock["last_price"]
    )

    volume = float(
        stock["volume"]
    )

    current_vwap = calculate_vwap(
        candles
    )

    ema9 = calculate_ema(
        candles,
        EMA_FAST,
    )

    ema21 = calculate_ema(
        candles,
        EMA_SLOW,
    )

    volume_surge = (
        calculate_volume_surge(
            candles
        )
    )

    supertrend = (
        calculate_supertrend(
            candles
        )
    )

    momentum = (
        calculate_momentum(
            candles
        )
    )

    rows = []


    # --------------------------------------------------------
    # 1. P/E
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Price-to-Earnings Ratio",

            "metric":
                "LIVE FUNDAMENTAL SOURCE REQUIRED",

            "verdict":
                None,
        }
    )


    # --------------------------------------------------------
    # 2. CMP
    # --------------------------------------------------------

    cmp_pass = (
        CMP_MIN
        <= price
        <= CMP_MAX
    )

    rows.append(
        {
            "parameter":
                "CMP Allocation Bounds",

            "metric":
                f"₹{price:,.2f}",

            "verdict":
                cmp_pass,
        }
    )


    # --------------------------------------------------------
    # 3. BETA
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Volatility Shield / Beta",

            "metric":
                "LIVE FUNDAMENTAL SOURCE REQUIRED",

            "verdict":
                None,
        }
    )


    # --------------------------------------------------------
    # 4. FREE-FLOAT MARKET CAP
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Free-Float Market Cap",

            "metric":
                "LIVE FUNDAMENTAL SOURCE REQUIRED",

            "verdict":
                None,
        }
    )


    # --------------------------------------------------------
    # 5. VOLUME
    # --------------------------------------------------------

    volume_pass = (
        volume
        >= VOLUME_MIN
    )

    rows.append(
        {
            "parameter":
                "Volume Liquidity Depth Floor",

            "metric":
                f"{volume:,.0f} shares",

            "verdict":
                volume_pass,
        }
    )


    # --------------------------------------------------------
    # 6. DEBT / EQUITY
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Debt-to-Equity",

            "metric":
                "LIVE FUNDAMENTAL SOURCE REQUIRED",

            "verdict":
                None,
        }
    )


    # --------------------------------------------------------
    # 7. VWAP
    # --------------------------------------------------------

    if current_vwap is None:

        vwap_metric = (
            "LIVE CANDLE DATA UNAVAILABLE"
        )

        vwap_pass = None

    else:

        vwap_metric = (
            f"₹{current_vwap:,.4f}"
        )

        vwap_pass = (
            price
            >= current_vwap
        )

    rows.append(
        {
            "parameter":
                "VWAP Support Anchoring",

            "metric":
                vwap_metric,

            "verdict":
                vwap_pass,
        }
    )


    # --------------------------------------------------------
    # 8. EMA 9 / 21
    # --------------------------------------------------------

    if (
        ema9 is None
        or ema21 is None
    ):

        ema_metric = (
            "LIVE CANDLE DATA UNAVAILABLE"
        )

        ema_pass = None

    else:

        ema_metric = (
            f"9 EMA ₹{ema9:,.2f} | "
            f"21 EMA ₹{ema21:,.2f}"
        )

        ema_pass = (
            ema9
            > ema21
        )

    rows.append(
        {
            "parameter":
                "Exponential Moving Average 9 / 21",

            "metric":
                ema_metric,

            "verdict":
                ema_pass,
        }
    )


    # --------------------------------------------------------
    # 9. SUPERTREND
    # --------------------------------------------------------

    if supertrend is None:

        supertrend_metric = (
            "LIVE CANDLE DATA UNAVAILABLE"
        )

    else:

        supertrend_metric = (
            "Bullish"
            if supertrend
            else
            "Bearish"
        )

    rows.append(
        {
            "parameter":
                "Supertrend Speed Engine",

            "metric":
                supertrend_metric,

            "verdict":
                supertrend,
        }
    )


    # --------------------------------------------------------
    # 10. VOLUME SURGE
    # --------------------------------------------------------

    if volume_surge is None:

        surge_metric = (
            "LIVE CANDLE DATA UNAVAILABLE"
        )

        surge_pass = None

    else:

        surge_metric = (
            f"{volume_surge:.2f}× "
            "previous 20-bar average"
        )

        surge_pass = (
            volume_surge
            >= VOLUME_SURGE_MULTIPLIER
        )

    rows.append(
        {
            "parameter":
                "Institutional Volume Mean Surge",

            "metric":
                surge_metric,

            "verdict":
                surge_pass,
        }
    )


    # --------------------------------------------------------
    # 11. MOMENTUM
    # --------------------------------------------------------

    if momentum is None:

        momentum_metric = (
            "LIVE CANDLE DATA UNAVAILABLE"
        )

        momentum_pass = None

    else:

        momentum_metric = (
            f"{momentum:+.3f}% "
            "over last 5 one-minute bars"
        )

        momentum_pass = (
            momentum > 0
        )

    rows.append(
        {
            "parameter":
                "Intraday Momentum Acceleration",

            "metric":
                momentum_metric,

            "verdict":
                momentum_pass,
        }
    )


    available = [
        row["verdict"]
        for row in rows
        if row["verdict"] is not None
    ]

    passes = sum(
        1
        for value in available
        if value is True
    )

    fails = sum(
        1
        for value in available
        if value is False
    )

    unavailable = (
        len(rows)
        - len(available)
    )

    score = (
        passes
        / len(rows)
    ) * 100.0

    return {
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

        "vwap":
            current_vwap,

        "ema9":
            ema9,

        "ema21":
            ema21,

        "volume_surge":
            volume_surge,

        "supertrend":
            supertrend,

        "momentum":
            momentum,
    }


# ============================================================
# LOAD DYNAMIC NSE UNIVERSE
# ============================================================

try:

    universe = (
        get_dynamic_nse_equities()
    )

except Exception as error:

    st.error(
        "Unable to load the live Dhan "
        "instrument universe."
    )

    st.code(
        str(error)
    )

    st.stop()


# ============================================================
# MANUAL CHECK
# ============================================================

st.markdown(
    """
<div class="panel">

<div class="panel-title">
🔍 Manual Check Override Field
</div>
""",
    unsafe_allow_html=True,
)

manual_symbol = st.text_input(
    "NSE symbol",
    placeholder=(
        "Type any NSE equity symbol "
        "from the live Dhan instrument master"
    ),
    label_visibility="collapsed",
)

manual_check = st.button(
    "⚡ CHECK LIVE STOCK",
    use_container_width=True,
)

st.markdown(
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# LIVE SCAN
# ============================================================

with st.spinner(
    "Connecting to Dhan live market server..."
):

    try:

        all_security_ids = (
            universe[
                "security_id"
            ]
            .tolist()
        )

        quotes = fetch_live_quotes(
            all_security_ids
        )

    except Exception as error:

        st.error(
            "Live market connection failed."
        )

        st.code(
            str(error)
        )

        st.stop()


if quotes.empty:

    st.warning(
        "Dhan returned no live market data."
    )

    st.stop()


# ============================================================
# JOIN LIVE DATA WITH DYNAMIC INSTRUMENT DATA
# ============================================================

market = universe.merge(
    quotes,
    on="security_id",
    how="inner",
)

market = market.dropna(
    subset=[
        "last_price",
        "volume",
    ]
)


# ============================================================
# MANUAL MODE
# ============================================================

if (
    manual_check
    and manual_symbol.strip()
):

    search = (
        manual_symbol
        .strip()
        .upper()
    )

    selected = market[
        market["symbol"]
        .astype(str)
        .str.upper()
        .eq(search)
    ]

    if selected.empty:

        st.error(
            "That symbol was not found "
            "in the current live NSE "
            "instrument universe."
        )

        st.stop()

    selected_stock = (
        selected.iloc[0]
    )

    with st.spinner(
        "Loading live 1-minute data..."
    ):

        candles = fetch_intraday_candles(
            selected_stock[
                "security_id"
            ]
        )

    if candles.empty:

        st.error(
            "Dhan returned no current "
            "1-minute candle data for "
            "this instrument."
        )

        st.stop()

    evaluation = evaluate_stock(
        selected_stock,
        candles,
    )

    winner = {
        "stock":
            selected_stock,

        "evaluation":
            evaluation,
    }

    scan_results = [
        winner
    ]


# ============================================================
# AUTOMATIC SCANNER
# ============================================================

else:

    # Dynamic price and liquidity filtering.
    # No stock names are hardcoded.

    candidates = market[
        (
            market["last_price"]
            >= CMP_MIN
        )
        &
        (
            market["last_price"]
            <= CMP_MAX
        )
        &
        (
            market["volume"]
            >= VOLUME_MIN
        )
    ].copy()

    if candidates.empty:

        st.warning(
            "No live NSE instruments currently "
            "meet the price and liquidity "
            "pre-filter."
        )

        st.stop()


    # Rank dynamically by current traded volume.
    candidates = (
        candidates
        .sort_values(
            "volume",
            ascending=False,
        )
        .head(
            MAX_TECHNICAL_CANDIDATES
        )
    )


    scan_results = []

    progress = st.progress(
        0,
        text=(
            "Evaluating live "
            "technical candidates..."
        ),
    )

    total = len(candidates)

    for position, (
        _,
        stock,
    ) in enumerate(
        candidates.iterrows(),
        start=1,
    ):

        try:

            candles = (
                fetch_intraday_candles(
                    stock[
                        "security_id"
                    ]
                )
            )

            if candles.empty:

                continue

            evaluation = (
                evaluate_stock(
                    stock,
                    candles,
                )
            )

            scan_results.append(
                {
                    "stock":
                        stock,

                    "evaluation":
                        evaluation,
                }
            )

        except Exception:

            continue

        progress.progress(
            position / total,
            text=(
                f"Evaluating live "
                f"candidate {position}/{total}"
            ),
        )

        # Stay below Dhan data API rate limits.
        time.sleep(0.22)

    progress.empty()


if not scan_results:

    st.warning(
        "No candidates returned usable "
        "live 1-minute data."
    )

    st.stop()


# ============================================================
# WINNER RANKING
# ============================================================

def ranking_key(item):

    stock = item["stock"]

    evaluation = item["evaluation"]

    return (
        evaluation["passes"],
        evaluation["score"],
        float(
            stock["volume"]
        ),
        float(
            stock["last_price"]
        ),
    )


scan_results.sort(
    key=ranking_key,
    reverse=True,
)

winner = scan_results[0]

winner_stock = (
    winner["stock"]
)

winner_evaluation = (
    winner["evaluation"]
)


# ============================================================
# WINNER DISPLAY
# ============================================================

st.markdown(
    f"""
<div class="winner">

<div class="winner-label">
⭐ REAL-TIME QUANT BREAKOUT WINNER
</div>

<div class="winner-symbol">
{winner_stock["symbol"]}
</div>

<div class="winner-price">
₹{float(winner_stock["last_price"]):,.2f}
</div>

<div class="winner-meta">
{winner_stock["name"]}
&nbsp; • &nbsp;
{winner_evaluation["passes"]}/11
live conditions passed
</div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# LIVE SUMMARY CARDS
# ============================================================

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.markdown(
        f"""
<div class="score-card">

<div class="score-number">
{winner_evaluation["passes"]}/11
</div>

<div class="score-label">
PASS CONDITIONS
</div>

</div>
""",
        unsafe_allow_html=True,
    )


with col2:

    st.markdown(
        f"""
<div class="score-card">

<div class="score-number">
{winner_evaluation["fails"]}
</div>

<div class="score-label">
FAIL CONDITIONS
</div>

</div>
""",
        unsafe_allow_html=True,
    )


with col3:

    st.markdown(
        f"""
<div class="score-card">

<div class="score-number">
{winner_evaluation["unavailable"]}
</div>

<div class="score-label">
DATA UNAVAILABLE
</div>

</div>
""",
        unsafe_allow_html=True,
    )


with col4:

    st.markdown(
        f"""
<div class="score-card">

<div class="score-number">
{winner_evaluation["score"]:.1f}%
</div>

<div class="score-label">
LIVE MATRIX SCORE
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
📊 11-Parameter Strategy Performance Grid
</div>
""",
    unsafe_allow_html=True,
)

render_matrix(
    winner_stock["symbol"],
    winner_stock["name"],
    winner_evaluation["rows"],
)

st.markdown(
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# LIVE MARKET DATA
# ============================================================

st.markdown(
    """
<div class="panel">

<div class="panel-title">
📡 Live Market Server Metrics
</div>
""",
    unsafe_allow_html=True,
)

metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:

    st.metric(
        "LIVE PRICE",
        f"₹{float(winner_stock['last_price']):,.2f}",
    )

with metric_col2:

    st.metric(
        "DAY VOLUME",
        f"{int(winner_stock['volume']):,}",
    )

with metric_col3:

    st.metric(
        "DAY CHANGE",
        (
            f"{float(winner_stock['net_change']):+.2f}"
            if pd.notna(
                winner_stock["net_change"]
            )
            else "—"
        ),
    )

st.markdown(
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# POSITION SIZER
# ============================================================

live_price = float(
    winner_stock["last_price"]
)

position = calculate_position(
    live_price
)

if position:

    st.markdown(
        f"""
<div class="position">

<div class="position-title">
🧮 ₹15,000 FIXED STRATEGY RISK BRACKET
</div>

<div class="position-grid">

<div class="position-item">

<div class="position-label">
TARGET POSITION
</div>

<div class="position-value">
BUY EXACTLY {position["shares"]} SHARES
</div>

</div>

<div class="position-item">

<div class="position-label">
SYSTEM RISK UNIT
</div>

<div class="position-value">
₹{position["risk_unit"]:,.2f}
</div>

</div>

<div class="position-item">

<div class="position-label">
🔒 AUTOMATED SL SAFETY FLOOR
</div>

<div class="position-value">
₹{position["stop_loss"]:,.2f}
</div>

</div>

<div class="position-item">

<div class="position-label">
🎯 AUTOMATED TAKE-PROFIT CEILING
</div>

<div class="position-value">
₹{position["take_profit"]:,.2f}
</div>

</div>

</div>

</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# DATA SOURCE / STATUS
# ============================================================

current_time = datetime.now().strftime(
    "%H:%M:%S"
)

st.markdown(
    f"""
<div class="status-line">

● LIVE MARKET SNAPSHOT FROM DHANHQ
&nbsp; • &nbsp;
DYNAMIC NSE INSTRUMENT MASTER
&nbsp; • &nbsp;
{len(universe):,} NSE EQUITY INSTRUMENTS
&nbsp; • &nbsp;
{len(market):,} LIVE QUOTES
&nbsp; • &nbsp;
{len(scan_results):,} TECHNICAL RESULTS
&nbsp; • &nbsp;
LAST CHECK {current_time}

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# REFRESH
# ============================================================

st.markdown(
    "<br>",
    unsafe_allow_html=True,
)

if st.button(
    "🔄 REFRESH LIVE MARKET DATA",
    use_container_width=True,
):

    st.cache_data.clear()

    st.rerun()
