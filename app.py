import io
import math
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh


# ============================================================
# QUANTBREAKOUT
# REAL-TIME NSE BREAKOUT SCANNER
# ============================================================

st.set_page_config(
    page_title="QUANTbreakout",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# USER STRATEGY RULES
# These are strategy rules, not market data.
# ============================================================

PE_MAX = 25.0

CMP_MIN = 50.0
CMP_MAX = 500.0

BETA_MIN = 0.60
BETA_MAX = 1.20

FREE_FLOAT_MCAP_MIN_CR = 5000.0

VOLUME_MIN = 500_000

VOLUME_SURGE_MULTIPLIER = 2.0

CAPITAL = 15000.0
RISK_PERCENT = 0.008
SL_MULTIPLIER = 1.5
TP_MULTIPLIER = 3.0

EMA_FAST = 9
EMA_SLOW = 21

# Technical candidates evaluated after live quote filtering.
TECHNICAL_CANDIDATES = 20

# Fundamental statistics are expensive API calls,
# so only the strongest technical candidates are checked.
FUNDAMENTAL_CANDIDATES = 12

QUOTE_BATCH_SIZE = 1000

DHAN_BASE_URL = "https://api.dhan.co/v2"

DHAN_INSTRUMENT_URL = (
    "https://images.dhan.co/api-data/"
    "api-scrip-master-detailed.csv"
)

TWELVE_DATA_URL = "https://api.twelvedata.com"


# ============================================================
# STREAMLIT SECRETS
# ============================================================

DHAN_CLIENT_ID = st.secrets.get(
    "DHAN_CLIENT_ID",
    ""
)

DHAN_ACCESS_TOKEN = st.secrets.get(
    "DHAN_ACCESS_TOKEN",
    ""
)

TWELVE_DATA_API_KEY = st.secrets.get(
    "TWELVE_DATA_API_KEY",
    ""
)


# ============================================================
# AUTO REFRESH
# 15 seconds
# ============================================================

st_autorefresh(
    interval=15_000,
    key="quantbreakout_refresh",
)


# ============================================================
# CSS
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
            circle at 20% 0%,
            rgba(255,255,255,0.95),
            transparent 32%
        ),
        linear-gradient(
            180deg,
            #e0f2fe 0%,
            #dbeafe 100%
        );
}

.block-container {
    max-width: 1500px;
    padding-top: 18px;
    padding-bottom: 35px;
}

header {
    visibility: hidden;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}


/* HEADER */

.top-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    padding: 12px 16px;

    background: rgba(255,255,255,0.88);

    border: 1px solid #bae6fd;

    border-radius: 15px;

    box-shadow:
        0 7px 25px
        rgba(15,23,42,0.08);

    margin-bottom: 12px;
}

.brand {
    font-size: 1.45rem;
    font-weight: 900;
    color: #0f172a;
}

.brand-icon {
    color: #0284c7;
}

.subtitle {
    color: #475569;
    font-size: 0.68rem;
    font-weight: 700;
    margin-top: 2px;
}

.live-pill {
    background: #dcfce7;
    color: #15803d;

    border: 1px solid #86efac;

    border-radius: 999px;

    padding: 6px 12px;

    font-size: 0.68rem;
    font-weight: 900;
}


/* STAT CARDS */

.stat-card {
    background: rgba(255,255,255,0.90);

    border:
        1px solid
        #bae6fd;

    border-radius: 12px;

    padding: 11px;

    min-height: 75px;

    box-shadow:
        0 5px 18px
        rgba(15,23,42,0.06);
}

.stat-title {
    color: #64748b;
    font-size: 0.61rem;
    font-weight: 800;
    text-transform: uppercase;
}

.stat-value {
    color: #0f172a;
    font-size: 1.15rem;
    font-weight: 900;
    margin-top: 4px;
}

.stat-green {
    color: #15803d;
}


/* WINNER */

.winner {
    background:
        linear-gradient(
            135deg,
            #fef08a,
            #fef9c3,
            #fff7b0
        );

    border:
        2px solid
        #ca8a04;

    border-radius: 18px;

    padding: 20px 15px;

    text-align: center;

    box-shadow:
        0 12px 35px
        rgba(202,138,4,0.18);
}

.winner-badge {
    display: inline-block;

    background: #ca8a04;

    color: white;

    border-radius: 999px;

    padding: 6px 13px;

    font-size: 0.67rem;

    font-weight: 900;
}

.winner-symbol {
    color: #0f172a;

    font-size:
        clamp(
            2.7rem,
            7vw,
            4.5rem
        );

    font-weight: 900;

    line-height: 1;

    margin-top: 8px;
}

.winner-name {
    color: #475569;

    font-size: 0.78rem;

    font-weight: 800;

    margin-top: 7px;
}

.winner-price {
    color: #15803d;

    font-size: 1.8rem;

    font-weight: 900;

    margin-top: 9px;
}

.winner-change {
    font-size: 0.8rem;

    font-weight: 900;

    margin-top: 4px;
}


/* PANELS */

.panel {
    background:
        rgba(255,255,255,0.72);

    border:
        1px solid
        #bae6fd;

    border-radius: 14px;

    padding: 14px;

    margin-top: 12px;

    box-shadow:
        0 6px 20px
        rgba(15,23,42,0.06);
}

.panel-title {
    color: #0c4a6e;

    font-size: 0.78rem;

    font-weight: 900;

    letter-spacing: 0.7px;

    margin-bottom: 11px;
}


/* MATRIX */

.matrix-wrap {
    width: 100%;

    overflow-x: auto;

    border-radius: 10px;
}

.matrix {
    width: 100%;

    min-width: 780px;

    border-collapse: collapse;

    font-size: 0.72rem;
}

.matrix th {
    background: #075985;

    color: #ffffff;

    padding: 9px;

    text-align: left;

    white-space: nowrap;
}

.matrix td {
    color: #0f172a;

    background: rgba(255,255,255,0.72);

    border-bottom:
        1px solid
        #e2e8f0;

    padding: 8px;

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

.na {
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

    border-radius: 14px;

    padding: 14px;

    margin-top: 12px;
}

.position-title {
    color: #075985;

    font-size: 0.78rem;

    font-weight: 900;

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
        rgba(255,255,255,0.72);

    border-radius: 10px;

    padding: 11px;
}

.position-label {
    color: #64748b;

    font-size: 0.6rem;

    font-weight: 800;
}

.position-value {
    color: #0f172a;

    font-size: 1rem;

    font-weight: 900;

    margin-top: 5px;
}


/* FOOTER */

.footer-bar {
    margin-top: 13px;

    background:
        rgba(255,255,255,0.58);

    border-radius: 10px;

    padding: 9px;

    color: #475569;

    font-size: 0.63rem;

    font-weight: 700;

    text-align: center;
}


/* MOBILE */

@media(max-width:768px) {

    .block-container {
        padding:
            8px 10px 20px !important;
    }

    .top-header {
        padding: 9px;
    }

    .brand {
        font-size: 1.05rem;
    }

    .subtitle {
        font-size: 0.58rem;
    }

    .winner {
        padding: 17px 9px;
    }

    .winner-symbol {
        font-size: 2.8rem;
    }

    .winner-price {
        font-size: 1.4rem;
    }

    .panel {
        padding: 10px;
    }

    .position-grid {
        grid-template-columns:
            repeat(2, 1fr);
    }

    .matrix {
        font-size: 0.64rem;
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
# CREDENTIAL CHECK
# ============================================================

if not DHAN_CLIENT_ID or not DHAN_ACCESS_TOKEN:

    st.markdown(
        """
<div class="winner">

<div class="winner-badge">
⚡ QUANTBREAKOUT
</div>

<div class="winner-symbol">
LIVE CONNECTION REQUIRED
</div>

<div class="winner-name">
DhanHQ credentials are not configured.
</div>

</div>
""",
        unsafe_allow_html=True,
    )

    st.warning(
        "Add DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN "
        "to Streamlit Secrets."
    )

    st.stop()


# ============================================================
# API HEADERS
# ============================================================

def dhan_headers():

    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
    }


# ============================================================
# LOAD DHAN INSTRUMENT MASTER
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_instrument_master():

    response = requests.get(
        DHAN_INSTRUMENT_URL,
        timeout=40,
    )

    response.raise_for_status()

    return pd.read_csv(
        io.BytesIO(response.content),
        low_memory=False,
    )


def get_nse_equities():

    df = load_instrument_master()

    required = [
        "EXCH_ID",
        "SEGMENT",
        "INSTRUMENT",
        "SECURITY_ID",
        "SYMBOL_NAME",
        "DISPLAY_NAME",
    ]

    missing = [
        x
        for x in required
        if x not in df.columns
    ]

    if missing:
        raise RuntimeError(
            f"Instrument master missing columns: {missing}"
        )

    result = df[
        (
            df["EXCH_ID"]
            .astype(str)
            .str.upper()
            == "NSE"
        )
        &
        (
            df["SEGMENT"]
            .astype(str)
            .str.upper()
            == "E"
        )
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

    result["security_id"] = pd.to_numeric(
        result["security_id"],
        errors="coerce",
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

    return result.drop_duplicates(
        "security_id"
    ).reset_index(drop=True)


# ============================================================
# CHUNK LIST
# ============================================================

def chunks(values, size):

    for i in range(
        0,
        len(values),
        size,
    ):

        yield values[
            i:i + size
        ]


# ============================================================
# LIVE DHAN QUOTES
# ============================================================

def fetch_quotes(security_ids):

    records = []

    batches = list(
        chunks(
            security_ids,
            QUOTE_BATCH_SIZE,
        )
    )

    for batch_number, batch in enumerate(
        batches
    ):

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
            timeout=25,
        )

        if response.status_code != 200:

            raise RuntimeError(
                f"Dhan quote error "
                f"{response.status_code}: "
                f"{response.text[:400]}"
            )

        body = response.json()

        nse = (
            body
            .get("data", {})
            .get("NSE_EQ", {})
        )

        for security_id, item in nse.items():

            ohlc = item.get(
                "ohlc",
                {},
            )

            records.append(
                {
                    "security_id":
                        str(security_id),

                    "last_price":
                        item.get(
                            "last_price"
                        ),

                    "volume":
                        item.get(
                            "volume"
                        ),

                    "average_price":
                        item.get(
                            "average_price"
                        ),

                    "net_change":
                        item.get(
                            "net_change"
                        ),

                    "day_open":
                        ohlc.get(
                            "open"
                        ),

                    "day_high":
                        ohlc.get(
                            "high"
                        ),

                    "day_low":
                        ohlc.get(
                            "low"
                        ),

                    "previous_close":
                        ohlc.get(
                            "close"
                        ),
                }
            )

        if batch_number < len(batches) - 1:

            time.sleep(1.05)

    if not records:

        return pd.DataFrame()

    result = pd.DataFrame(
        records
    )

    numeric = [
        "last_price",
        "volume",
        "average_price",
        "net_change",
        "day_open",
        "day_high",
        "day_low",
        "previous_close",
    ]

    for column in numeric:

        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    return result


# ============================================================
# LIVE 1-MINUTE CANDLES
# ============================================================

def fetch_intraday(
    security_id
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
        timeout=25,
    )

    if response.status_code != 200:

        return pd.DataFrame()

    body = response.json()

    closes = body.get(
        "close",
        [],
    )

    if not closes:

        return pd.DataFrame()

    result = pd.DataFrame(
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

        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    return result.dropna().reset_index(
        drop=True
    )


# ============================================================
# TWELVE DATA FUNDAMENTALS
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def fetch_fundamentals(
    symbol,
):

    if not TWELVE_DATA_API_KEY:

        return {
            "available":
                False
        }

    try:

        response = requests.get(
            f"{TWELVE_DATA_URL}/statistics",
            params={
                "symbol":
                    symbol,

                "exchange":
                    "NSE",

                "apikey":
                    TWELVE_DATA_API_KEY,
            },
            timeout=20,
        )

        if response.status_code != 200:

            return {
                "available":
                    False
            }

        data = response.json()

        if (
            "statistics"
            not in data
        ):

            return {
                "available":
                    False
            }

        stats = data.get(
            "statistics",
            {}
        )

        valuations = stats.get(
            "valuations_metrics",
            {}
        )

        balance = stats.get(
            "balance_sheet",
            {}
        )

        stock_stats = stats.get(
            "stock_statistics",
            {}
        )

        price_summary = stats.get(
            "stock_price_summary",
            {}
        )

        return {
            "available":
                True,

            "pe":
                valuations.get(
                    "trailing_pe"
                ),

            "float_shares":
                stock_stats.get(
                    "float_shares"
                ),

            "beta":
                price_summary.get(
                    "beta"
                ),

            "debt_equity":
                balance.get(
                    "total_debt_to_equity_mrq"
                ),
        }

    except Exception:

        return {
            "available":
                False
        }


# ============================================================
# TECHNICAL CALCULATIONS
# ============================================================

def calculate_vwap(
    candles
):

    if candles.empty:

        return None

    typical_price = (
        candles["high"]
        + candles["low"]
        + candles["close"]
    ) / 3.0

    volume = candles["volume"]

    if volume.sum() <= 0:

        return None

    return float(
        (
            typical_price
            * volume
        ).sum()
        / volume.sum()
    )


def calculate_ema(
    candles,
    period,
):

    if len(candles) < period:

        return None

    return float(
        candles["close"]
        .ewm(
            span=period,
            adjust=False,
        )
        .mean()
        .iloc[-1]
    )


def calculate_volume_ratio(
    candles
):

    if len(candles) < 21:

        return None

    average = (
        candles["volume"]
        .iloc[-21:-1]
        .mean()
    )

    if average <= 0:

        return None

    return float(
        candles["volume"].iloc[-1]
        / average
    )


def calculate_supertrend(
    candles
):

    if len(candles) < 20:

        return None

    period = 10
    multiplier = 3.0

    previous_close = (
        candles["close"]
        .shift(1)
    )

    tr = pd.concat(
        [
            candles["high"]
            - candles["low"],

            (
                candles["high"]
                - previous_close
            ).abs(),

            (
                candles["low"]
                - previous_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = (
        tr
        .rolling(period)
        .mean()
    )

    hl2 = (
        candles["high"]
        + candles["low"]
    ) / 2

    upper = (
        hl2
        + multiplier * atr
    )

    lower = (
        hl2
        - multiplier * atr
    )

    close = candles["close"]

    # Simplified trend test:
    # current close above lower band and
    # above previous close.
    return bool(
        close.iloc[-1]
        > lower.iloc[-1]
        and
        close.iloc[-1]
        >= close.iloc[-2]
    )


def calculate_momentum(
    candles
):

    if len(candles) < 6:

        return None

    previous = float(
        candles["close"].iloc[-6]
    )

    current = float(
        candles["close"].iloc[-1]
    )

    if previous <= 0:

        return None

    return (
        (current / previous) - 1
    ) * 100


# ============================================================
# POSITION SIZER
# ============================================================

def position_size(
    price
):

    shares = math.floor(
        CAPITAL / price
    )

    risk_unit = (
        price * RISK_PERCENT
    )

    sl = (
        price
        - risk_unit * SL_MULTIPLIER
    )

    tp = (
        price
        + risk_unit * TP_MULTIPLIER
    )

    return (
        shares,
        risk_unit,
        sl,
        tp,
    )


# ============================================================
# VERDICT
# ============================================================

def status_html(
    value
):

    if value is True:

        return (
            '<span class="pass">'
            '🟢 PASS'
            '</span>'
        )

    if value is False:

        return (
            '<span class="fail">'
            '🔴 FAIL'
            '</span>'
        )

    return (
        '<span class="na">'
        '⚪ DATA UNAVAILABLE'
        '</span>'
    )


# ============================================================
# EVALUATE ONE STOCK
# ============================================================

def evaluate_stock(
    stock,
    candles,
    fundamentals,
):

    price = float(
        stock["last_price"]
    )

    volume = float(
        stock["volume"]
    )

    vwap = calculate_vwap(
        candles
    )

    ema9 = calculate_ema(
        candles,
        9
    )

    ema21 = calculate_ema(
        candles,
        21
    )

    volume_ratio = (
        calculate_volume_ratio(
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

    pe = fundamentals.get(
        "pe"
    )

    beta = fundamentals.get(
        "beta"
    )

    float_shares = fundamentals.get(
        "float_shares"
    )

    debt_equity = fundamentals.get(
        "debt_equity"
    )


    # --------------------------------------------------------
    # FREE FLOAT MARKET CAP
    # ₹ Crores
    # --------------------------------------------------------

    if (
        float_shares is not None
        and
        pd.notna(float_shares)
    ):

        free_float_mcap_cr = (
            price
            * float(float_shares)
            / 10_000_000
        )

    else:

        free_float_mcap_cr = None


    rows = []


    # 1 P/E

    if pe is None:

        rows.append(
            {
                "parameter":
                    "Price-to-Earnings Ratio ≤ 25",

                "verdict":
                    None,

                "metric":
                    "Fundamental data unavailable",
            }
        )

    else:

        rows.append(
            {
                "parameter":
                    "Price-to-Earnings Ratio ≤ 25",

                "verdict":
                    float(pe) <= PE_MAX,

                "metric":
                    f"{float(pe):.2f}",
            }
        )


    # 2 CMP

    rows.append(
        {
            "parameter":
                "CMP between ₹50 and ₹500",

            "verdict":
                CMP_MIN
                <= price
                <= CMP_MAX,

            "metric":
                f"₹{price:,.2f}",
        }
    )


    # 3 Beta

    if beta is None:

        rows.append(
            {
                "parameter":
                    "Beta between 0.60 and 1.20",

                "verdict":
                    None,

                "metric":
                    "Fundamental data unavailable",
            }
        )

    else:

        rows.append(
            {
                "parameter":
                    "Beta between 0.60 and 1.20",

                "verdict":
                    BETA_MIN
                    <= float(beta)
                    <= BETA_MAX,

                "metric":
                    f"{float(beta):.2f}",
            }
        )


    # 4 Free float market cap

    if free_float_mcap_cr is None:

        rows.append(
            {
                "parameter":
                    "Free-Float Market Cap ≥ ₹5,000 Cr",

                "verdict":
                    None,

                "metric":
                    "Float data unavailable",
            }
        )

    else:

        rows.append(
            {
                "parameter":
                    "Free-Float Market Cap ≥ ₹5,000 Cr",

                "verdict":
                    free_float_mcap_cr
                    >= FREE_FLOAT_MCAP_MIN_CR,

                "metric":
                    (
                        f"₹{free_float_mcap_cr:,.0f} Cr"
                    ),
            }
        )


    # 5 Volume

    rows.append(
        {
            "parameter":
                "Traded Volume ≥ 5 Lakh",

            "verdict":
                volume >= VOLUME_MIN,

            "metric":
                f"{volume:,.0f} shares",
        }
    )


    # 6 Debt / Equity

    if debt_equity is None:

        rows.append(
            {
                "parameter":
                    "Debt-to-Equity",

                "verdict":
                    None,

                "metric":
                    "Fundamental data unavailable",
            }
        )

    else:

        # User's original strategy did not specify
        # a numerical D/E threshold.
        # Therefore display the real value but
        # do not invent a pass/fail threshold.

        rows.append(
            {
                "parameter":
                    "Debt-to-Equity",

                "verdict":
                    None,

                "metric":
                    f"{float(debt_equity):.2f}"
                    " — threshold required",
            }
        )


    # 7 VWAP

    if vwap is None:

        rows.append(
            {
                "parameter":
                    "Price above VWAP",

                "verdict":
                    None,

                "metric":
                    "Candle data unavailable",
            }
        )

    else:

        rows.append(
            {
                "parameter":
                    "Price above VWAP",

                "verdict":
                    price >= vwap,

                "metric":
                    (
                        f"Price ₹{price:,.2f} | "
                        f"VWAP ₹{vwap:,.4f}"
                    ),
            }
        )


    # 8 EMA

    if (
        ema9 is None
        or ema21 is None
    ):

        rows.append(
            {
                "parameter":
                    "EMA 9 above EMA 21",

                "verdict":
                    None,

                "metric":
                    "Candle data unavailable",
            }
        )

    else:

        rows.append(
            {
                "parameter":
                    "EMA 9 above EMA 21",

                "verdict":
                    ema9 > ema21,

                "metric":
                    (
                        f"9 EMA ₹{ema9:,.2f} | "
                        f"21 EMA ₹{ema21:,.2f}"
                    ),
            }
        )


    # 9 Supertrend

    rows.append(
        {
            "parameter":
                "Supertrend bullish",

            "verdict":
                supertrend,

            "metric":
                (
                    "Bullish"
                    if supertrend
                    else
                    "Bearish"
                    if supertrend is not None
                    else
                    "Unavailable"
                ),
        }
    )


    # 10 Volume surge

    if volume_ratio is None:

        rows.append(
            {
                "parameter":
                    "Volume ≥ 2× 20-bar average",

                "verdict":
                    None,

                "metric":
                    "Candle data unavailable",
            }
        )

    else:

        rows.append(
            {
                "parameter":
                    "Volume ≥ 2× 20-bar average",

                "verdict":
                    volume_ratio
                    >= VOLUME_SURGE_MULTIPLIER,

                "metric":
                    f"{volume_ratio:.2f}× average",
            }
        )


    # 11 Momentum

    if momentum is None:

        rows.append(
            {
                "parameter":
                    "Positive intraday momentum",

                "verdict":
                    None,

                "metric":
                    "Candle data unavailable",
            }
        )

    else:

        rows.append(
            {
                "parameter":
                    "Positive intraday momentum",

                "verdict":
                    momentum > 0,

                "metric":
                    f"{momentum:+.3f}% / 5 bars",
            }
        )


    passes = sum(
        x["verdict"] is True
        for x in rows
    )

    fails = sum(
        x["verdict"] is False
        for x in rows
    )

    unavailable = sum(
        x["verdict"] is None
        for x in rows
    )

    score = (
        passes / len(rows)
    ) * 100

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
    }


# ============================================================
# LOAD UNIVERSE
# ============================================================

try:

    universe = (
        get_nse_equities()
    )

except Exception as error:

    st.error(
        "Unable to load Dhan's NSE instrument master."
    )

    st.code(
        str(error)
    )

    st.stop()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
<div class="top-header">

<div>

<div class="brand">
<span class="brand-icon">⚡</span>
QUANTBREAKOUT
</div>

<div class="subtitle">
Real-Time NSE Scanner • DhanHQ Market Data
</div>

</div>

<div class="live-pill">
● LIVE ENGINE
</div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# LIVE QUOTES
# ============================================================

try:

    quotes = fetch_quotes(
        universe["security_id"].tolist()
    )

except Exception as error:

    st.error(
        "Dhan live market connection failed."
    )

    st.code(
        str(error)
    )

    st.stop()


if quotes.empty:

    st.warning(
        "Dhan returned no live quote data."
    )

    st.stop()


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
# LIVE PRE-FILTER
# ============================================================

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
        "No live NSE stock currently meets "
        "the ₹50–₹500 price and 5-lakh "
        "volume pre-filter."
    )

    st.stop()


# Highest live volume first.
candidates = (
    candidates
    .sort_values(
        "volume",
        ascending=False,
    )
    .head(
        TECHNICAL_CANDIDATES
    )
)


# ============================================================
# TECHNICAL SCAN
# ============================================================

technical_results = []

progress = st.progress(
    0,
    text="Scanning live 1-minute candles..."
)

total = len(candidates)

for number, (
    _,
    stock,
) in enumerate(
    candidates.iterrows(),
    start=1,
):

    try:

        candles = fetch_intraday(
            stock["security_id"]
        )

        if candles.empty:

            continue

        vwap = calculate_vwap(
            candles
        )

        ema9 = calculate_ema(
            candles,
            9
        )

        ema21 = calculate_ema(
            candles,
            21
        )

        volume_ratio = (
            calculate_volume_ratio(
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

        technical_score = 0

        technical_score += (
            1
            if vwap is not None
            and float(stock["last_price"])
            >= vwap
            else 0
        )

        technical_score += (
            1
            if ema9 is not None
            and ema21 is not None
            and ema9 > ema21
            else 0
        )

        technical_score += (
            1
            if supertrend is True
            else 0
        )

        technical_score += (
            1
            if volume_ratio is not None
            and volume_ratio >= 2
            else 0
        )

        technical_score += (
            1
            if momentum is not None
            and momentum > 0
            else 0
        )

        technical_results.append(
            {
                "stock":
                    stock,

                "candles":
                    candles,

                "technical_score":
                    technical_score,
            }
        )

    except Exception:
        pass

    progress.progress(
        number / total,
        text=(
            f"Live technical scan "
            f"{number}/{total}"
        ),
    )

    time.sleep(0.22)

progress.empty()


if not technical_results:

    st.warning(
        "No live technical candle data "
        "was returned."
    )

    st.stop()


# ============================================================
# RANK TECHNICAL RESULTS
# ============================================================

technical_results.sort(
    key=lambda item: (
        item["technical_score"],
        float(
            item["stock"]["volume"]
        ),
    ),
    reverse=True,
)


# ============================================================
# FUNDAMENTAL EVALUATION
# ============================================================

final_results = []

fundamental_pool = technical_results[
    :FUNDAMENTAL_CANDIDATES
]


for item in fundamental_pool:

    stock = item["stock"]

    candles = item["candles"]

    fundamentals = (
        fetch_fundamentals(
            stock["symbol"]
        )
    )

    evaluation = evaluate_stock(
        stock,
        candles,
        fundamentals,
    )

    final_results.append(
        {
            "stock":
                stock,

            "evaluation":
                evaluation,

            "candles":
                candles,
        }
    )


if not final_results:

    st.stop()


# ============================================================
# WINNER
# ============================================================

final_results.sort(
    key=lambda item: (
        item["evaluation"]["passes"],
        -item["evaluation"]["fails"],
        item["evaluation"]["score"],
        float(
            item["stock"]["volume"]
        ),
    ),
    reverse=True,
)

winner = final_results[0]

winner_stock = winner["stock"]

winner_eval = winner["evaluation"]


# ============================================================
# TOP STATISTICS
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

with c1:

    st.markdown(
        f"""
<div class="stat-card">
<div class="stat-title">
Market Status
</div>
<div class="stat-value stat-green">
● LIVE
</div>
</div>
""",
        unsafe_allow_html=True,
    )

with c2:

    st.markdown(
        f"""
<div class="stat-card">
<div class="stat-title">
Last Updated
</div>
<div class="stat-value">
{datetime.now().strftime("%H:%M:%S")}
</div>
</div>
""",
        unsafe_allow_html=True,
    )

with c3:

    st.markdown(
        f"""
<div class="stat-card">
<div class="stat-title">
NSE Universe
</div>
<div class="stat-value">
{len(universe):,}
</div>
</div>
""",
        unsafe_allow_html=True,
    )

with c4:

    st.markdown(
        f"""
<div class="stat-card">
<div class="stat-title">
Live Quotes
</div>
<div class="stat-value">
{len(market):,}
</div>
</div>
""",
        unsafe_allow_html=True,
    )

with c5:

    st.markdown(
        f"""
<div class="stat-card">
<div class="stat-title">
Technical Candidates
</div>
<div class="stat-value">
{len(technical_results)}
</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# WINNER CARD
# ============================================================

price = float(
    winner_stock["last_price"]
)

change = winner_stock["net_change"]

change_text = (
    f"{float(change):+.2f}"
    if pd.notna(change)
    else "—"
)

st.markdown(
    f"""
<div class="winner">

<div class="winner-badge">
⭐ REAL-TIME QUANT BREAKOUT WINNER
</div>

<div class="winner-symbol">
{winner_stock["symbol"]}
</div>

<div class="winner-name">
{winner_stock["name"]}
</div>

<div class="winner-price">
₹{price:,.2f}
</div>

<div class="winner-change">
Live Change: {change_text}
</div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SUMMARY
# ============================================================

s1, s2, s3, s4 = st.columns(4)

with s1:

    st.metric(
        "PASS CONDITIONS",
        f'{winner_eval["passes"]} / 11',
    )

with s2:

    st.metric(
        "FAIL CONDITIONS",
        f'{winner_eval["fails"]} / 11',
    )

with s3:

    st.metric(
        "DATA UNAVAILABLE",
        f'{winner_eval["unavailable"]} / 11',
    )

with s4:

    st.metric(
        "MATRIX SCORE",
        f'{winner_eval["score"]:.1f}%',
    )


# ============================================================
# MATRIX
# ============================================================

matrix_html = """
<div class="panel">

<div class="panel-title">
📊 11-PARAMETER STRATEGY MATRIX
</div>

<div class="matrix-wrap">

<table class="matrix">

<thead>

<tr>
<th>#</th>
<th>PARAMETERS FROM SYSTEM SCAN</th>
<th>STOCK CODE</th>
<th>STOCK NAME</th>
<th>VERDICT STATUS</th>
<th>LIVE METRIC VALUE</th>
</tr>

</thead>

<tbody>
"""

for index, row in enumerate(
    winner_eval["rows"],
    start=1,
):

    matrix_html += f"""
<tr>

<td>
{index}
</td>

<td>
{row["parameter"]}
</td>

<td>
{winner_stock["symbol"]}
</td>

<td>
{winner_stock["name"]}
</td>

<td>
{status_html(row["verdict"])}
</td>

<td>
{row["metric"]}
</td>

</tr>
"""

matrix_html += """
</tbody>
</table>
</div>
</div>
"""

st.markdown(
    matrix_html,
    unsafe_allow_html=True,
)


# ============================================================
# POSITION SIZER
# ============================================================

shares, risk_unit, sl, tp = (
    position_size(price)
)

st.markdown(
    f"""
<div class="position">

<div class="position-title">
🧮 POSITION SIZING — ₹15,000 CAPITAL
</div>

<div class="position-grid">

<div class="position-item">

<div class="position-label">
TARGET POSITION
</div>

<div class="position-value">
BUY EXACTLY {shares} SHARES
</div>

</div>

<div class="position-item">

<div class="position-label">
SYSTEM RISK UNIT
</div>

<div class="position-value">
₹{risk_unit:,.2f}
</div>

</div>

<div class="position-item">

<div class="position-label">
🔒 AUTOMATED STOP LOSS
</div>

<div class="position-value">
₹{sl:,.2f}
</div>

</div>

<div class="position-item">

<div class="position-label">
🎯 AUTOMATED TAKE PROFIT
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
# MANUAL CHECK
# ============================================================

st.markdown(
    """
<div class="panel">

<div class="panel-title">
🔍 MANUAL CHECK OVERRIDE
</div>
""",
    unsafe_allow_html=True,
)

manual_symbol = st.text_input(
    "Enter NSE symbol",
    placeholder="Enter any NSE equity symbol",
    label_visibility="collapsed",
)

if manual_symbol:

    symbol = (
        manual_symbol
        .strip()
        .upper()
    )

    found = market[
        market["symbol"]
        .astype(str)
        .str.upper()
        .eq(symbol)
    ]

    if found.empty:

        st.warning(
            "Symbol is not present in the "
            "current Dhan NSE instrument master."
        )

    else:

        manual_stock = (
            found.iloc[0]
        )

        with st.spinner(
            "Loading live manual-check data..."
        ):

            manual_candles = (
                fetch_intraday(
                    manual_stock[
                        "security_id"
                    ]
                )
            )

            manual_fundamentals = (
                fetch_fundamentals(
                    manual_stock[
                        "symbol"
                    ]
                )
            )

        if not manual_candles.empty:

            manual_eval = (
                evaluate_stock(
                    manual_stock,
                    manual_candles,
                    manual_fundamentals,
                )
            )

            st.success(
                f"Live check completed for {symbol}"
            )

            manual_html = """
<div class="matrix-wrap">
<table class="matrix">
<thead>
<tr>
<th>#</th>
<th>PARAMETER</th>
<th>VERDICT</th>
<th>LIVE VALUE</th>
</tr>
</thead>
<tbody>
"""

            for i, row in enumerate(
                manual_eval["rows"],
                start=1,
            ):

                manual_html += f"""
<tr>
<td>{i}</td>
<td>{row["parameter"]}</td>
<td>{status_html(row["verdict"])}</td>
<td>{row["metric"]}</td>
</tr>
"""

            manual_html += """
</tbody>
</table>
</div>
"""

            st.markdown(
                manual_html,
                unsafe_allow_html=True,
            )

st.markdown(
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    f"""
<div class="footer-bar">

📡 DATA: DhanHQ Live Market Data
&nbsp;&nbsp; • &nbsp;&nbsp;

📊 FUNDAMENTALS: Twelve Data NSE Statistics
&nbsp;&nbsp; • &nbsp;&nbsp;

🔄 AUTO REFRESH: 15 seconds
&nbsp;&nbsp; • &nbsp;&nbsp;

🕒 SERVER TIME:
{datetime.now().strftime("%d-%m-%Y %H:%M:%S")}

</div>
""",
    unsafe_allow_html=True,
)
