import math
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st


# ============================================================
# QUANTBREAKOUT WINNER SCANNER
# REAL-TIME NSE EQUITY SCANNER
# ============================================================

st.set_page_config(
    page_title="QUANTbreakout",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# STRATEGY SETTINGS
# These are strategy rules only.
# No stock name, stock price or market value is hardcoded.
# ============================================================

PE_MAX = 25.0

CMP_MIN = 50.0
CMP_MAX = 500.0

BETA_MIN = 0.60
BETA_MAX = 1.20

FREE_FLOAT_MCAP_MIN_CR = 5000.0

VOLUME_MIN = 500000

VOLUME_SURGE_MULTIPLIER = 2.0

EMA_FAST = 9
EMA_SLOW = 21

CAPITAL = 15000.0
RISK_PERCENT = 0.008
SL_MULTIPLIER = 1.5
TP_MULTIPLIER = 3.0

TECHNICAL_CANDIDATES = 20
FUNDAMENTAL_CANDIDATES = 10

DHAN_BASE_URL = "https://api.dhan.co/v2"

DHAN_INSTRUMENT_URL = (
    "https://images.dhan.co/api-data/"
    "api-scrip-master-detailed.csv"
)

TWELVE_DATA_URL = "https://api.twelvedata.com"


# ============================================================
# SECRETS
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
# CSS
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
            circle at 20% 0%,
            rgba(255,255,255,0.95),
            transparent 35%
        ),
        linear-gradient(
            180deg,
            #e0f2fe 0%,
            #dbeafe 100%
        );
}

.block-container {
    max-width: 1500px;
    padding-top: 14px;
    padding-bottom: 30px;
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

.qb-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    background: rgba(255,255,255,0.92);

    border: 1px solid #bae6fd;

    border-radius: 16px;

    padding: 12px 16px;

    margin-bottom: 12px;

    box-shadow:
        0 8px 28px rgba(15,23,42,0.08);
}

.qb-brand {
    font-size: 1.5rem;
    font-weight: 900;
    color: #0f172a;
}

.qb-brand span {
    color: #0284c7;
}

.qb-subtitle {
    color: #64748b;
    font-size: 0.66rem;
    font-weight: 700;
    margin-top: 2px;
}

.qb-live {
    background: #dcfce7;
    border: 1px solid #86efac;
    color: #15803d;
    border-radius: 999px;
    padding: 7px 13px;
    font-size: 0.65rem;
    font-weight: 900;
}


/* WINNER */

.qb-winner {
    background:
        linear-gradient(
            135deg,
            #fef08a,
            #fef9c3,
            #fff7b0
        );

    border: 3px solid #ca8a04;

    border-radius: 19px;

    padding: 19px;

    text-align: center;

    box-shadow:
        0 14px 38px rgba(202,138,4,0.18);

    margin-bottom: 12px;
}

.qb-winner-badge {
    display: inline-block;

    background: #ca8a04;

    color: white;

    padding: 6px 14px;

    border-radius: 999px;

    font-size: 0.67rem;

    font-weight: 900;
}

.qb-winner-symbol {
    color: #0f172a;

    font-size:
        clamp(2.5rem, 7vw, 4.6rem);

    font-weight: 900;

    line-height: 1;

    margin-top: 10px;
}

.qb-winner-name {
    color: #475569;

    font-size: 0.78rem;

    font-weight: 800;

    margin-top: 6px;
}

.qb-winner-price {
    color: #15803d;

    font-size: 1.9rem;

    font-weight: 900;

    margin-top: 9px;
}

.qb-winner-change {
    color: #475569;

    font-size: 0.75rem;

    font-weight: 800;

    margin-top: 3px;
}


/* PANEL */

.qb-panel {
    background: rgba(255,255,255,0.78);

    border: 1px solid #bae6fd;

    border-radius: 14px;

    padding: 13px;

    margin-top: 12px;

    box-shadow:
        0 6px 22px rgba(15,23,42,0.06);
}

.qb-panel-title {
    color: #075985;

    font-size: 0.78rem;

    font-weight: 900;

    letter-spacing: 0.5px;

    margin-bottom: 9px;
}


/* METRIC CARDS */

.qb-card {
    background: rgba(255,255,255,0.90);

    border: 1px solid #bae6fd;

    border-radius: 12px;

    padding: 10px;

    min-height: 72px;

    box-shadow:
        0 5px 17px rgba(15,23,42,0.05);
}

.qb-card-label {
    color: #64748b;

    font-size: 0.58rem;

    font-weight: 900;

    text-transform: uppercase;
}

.qb-card-value {
    color: #0f172a;

    font-size: 1.12rem;

    font-weight: 900;

    margin-top: 4px;
}


/* TABLE */

.qb-table-wrap {
    width: 100%;
    overflow-x: auto;
}

.qb-table {
    width: 100%;
    min-width: 820px;

    border-collapse: collapse;

    font-size: 0.71rem;
}

.qb-table th {
    background: #075985;
    color: #ffffff;

    padding: 9px;

    text-align: left;

    white-space: nowrap;
}

.qb-table td {
    color: #0f172a;

    background: rgba(255,255,255,0.82);

    border-bottom: 1px solid #e2e8f0;

    padding: 8px;
}

.qb-pass {
    color: #15803d;
    font-weight: 900;
}

.qb-fail {
    color: #b91c1c;
    font-weight: 900;
}

.qb-na {
    color: #64748b;
    font-weight: 800;
}


/* POSITION */

.qb-position {
    background:
        linear-gradient(
            135deg,
            #bae6fd,
            #e0f2fe
        );

    border: 2px solid #0284c7;

    border-radius: 14px;

    padding: 13px;

    margin-top: 12px;
}

.qb-position-title {
    color: #075985;

    font-size: 0.78rem;

    font-weight: 900;

    margin-bottom: 9px;
}

.qb-position-grid {
    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 9px;
}

.qb-position-item {
    background: rgba(255,255,255,0.78);

    border-radius: 10px;

    padding: 10px;
}

.qb-position-label {
    color: #64748b;

    font-size: 0.57rem;

    font-weight: 900;
}

.qb-position-value {
    color: #0f172a;

    font-size: 0.95rem;

    font-weight: 900;

    margin-top: 5px;
}


/* MOBILE */

@media(max-width:768px) {

    .block-container {
        padding:
            8px 10px 20px !important;
    }

    .qb-header {
        padding: 9px 10px;
    }

    .qb-brand {
        font-size: 1.05rem;
    }

    .qb-subtitle {
        font-size: 0.54rem;
    }

    .qb-live {
        font-size: 0.56rem;
        padding: 5px 8px;
    }

    .qb-winner {
        padding: 15px 8px;
    }

    .qb-winner-symbol {
        font-size: 2.8rem;
    }

    .qb-winner-price {
        font-size: 1.5rem;
    }

    .qb-panel {
        padding: 10px;
    }

    .qb-position-grid {
        grid-template-columns:
            repeat(2, 1fr);
    }

    .qb-table {
        font-size: 0.62rem;
    }

    .qb-table th,
    .qb-table td {
        padding: 6px;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# API HELPERS
# ============================================================

def dhan_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
    }


def api_error(response):
    try:
        data = response.json()

        return (
            data.get("errorMessage")
            or data.get("message")
            or str(data)
        )

    except Exception:
        return response.text[:500]


# ============================================================
# INSTRUMENT MASTER
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_instrument_master():

    response = requests.get(
        DHAN_INSTRUMENT_URL,
        timeout=45,
    )

    response.raise_for_status()

    return pd.read_csv(
        response.url,
        low_memory=False,
    )


def choose_column(df, possible):

    for name in possible:

        if name in df.columns:
            return name

    return None


def get_nse_equities():

    df = load_instrument_master()

    exchange_col = choose_column(
        df,
        [
            "EXCH_ID",
            "SEM_EXM_EXCH_ID",
        ],
    )

    segment_col = choose_column(
        df,
        [
            "SEGMENT",
            "SEM_SEGMENT",
        ],
    )

    instrument_col = choose_column(
        df,
        [
            "INSTRUMENT",
            "SEM_INSTRUMENT_NAME",
        ],
    )

    security_col = choose_column(
        df,
        [
            "SECURITY_ID",
            "SEM_SMST_SECURITY_ID",
        ],
    )

    symbol_col = choose_column(
        df,
        [
            "SYMBOL_NAME",
            "SEM_CUSTOM_SYMBOL",
            "SM_SYMBOL_NAME",
        ],
    )

    display_col = choose_column(
        df,
        [
            "DISPLAY_NAME",
            "SEM_CUSTOM_SYMBOL",
            "SYMBOL_NAME",
        ],
    )

    if not exchange_col:
        raise RuntimeError(
            "Could not find NSE exchange column "
            "in Dhan instrument master."
        )

    if not security_col:
        raise RuntimeError(
            "Could not find Security ID column "
            "in Dhan instrument master."
        )

    if not symbol_col:
        raise RuntimeError(
            "Could not find symbol column "
            "in Dhan instrument master."
        )

    result = df[
        df[exchange_col]
        .astype(str)
        .str.upper()
        .eq("NSE")
    ].copy()

    if segment_col:

        segment = (
            result[segment_col]
            .astype(str)
            .str.upper()
        )

        result = result[
            segment.str.contains(
                "EQUITY|NSE_EQ|E",
                regex=True,
                na=False,
            )
        ]

    if instrument_col:

        instrument = (
            result[instrument_col]
            .astype(str)
            .str.upper()
        )

        equity_mask = (
            instrument.eq("EQUITY")
            | instrument.eq("EQUITY SHARES")
            | instrument.str.contains(
                "EQUITY",
                na=False,
            )
        )

        filtered = result[equity_mask]

        if not filtered.empty:
            result = filtered

    result = result[
        [security_col, symbol_col]
        + (
            [display_col]
            if display_col
            and display_col not in [
                security_col,
                symbol_col,
            ]
            else []
        )
    ].copy()

    columns = [
        "security_id",
        "symbol",
    ]

    if len(result.columns) == 3:
        columns.append("name")

    result.columns = columns

    if "name" not in result.columns:
        result["name"] = result["symbol"]

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
        .str.upper()
    )

    result["name"] = (
        result["name"]
        .astype(str)
        .str.strip()
    )

    result = result[
        result["symbol"].ne("")
        &
        result["symbol"].ne("NAN")
    ]

    return (
        result
        .drop_duplicates(
            subset=["security_id"]
        )
        .reset_index(drop=True)
    )


# ============================================================
# CHUNK
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
# LIVE QUOTES
# ============================================================

def fetch_live_quotes(
    security_ids
):

    output = []

    batches = list(
        chunks(
            security_ids,
            1000,
        )
    )

    for batch_index, batch in enumerate(
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
            timeout=30,
        )

        if response.status_code != 200:

            raise RuntimeError(
                "Dhan quote API failed: "
                + api_error(response)
            )

        body = response.json()

        data = (
            body
            .get("data", {})
            .get("NSE_EQ", {})
        )

        for security_id, item in data.items():

            ohlc = item.get(
                "ohlc",
                {},
            )

            output.append(
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

                    "open":
                        ohlc.get(
                            "open"
                        ),

                    "high":
                        ohlc.get(
                            "high"
                        ),

                    "low":
                        ohlc.get(
                            "low"
                        ),

                    "previous_close":
                        ohlc.get(
                            "close"
                        ),
                }
            )

        if (
            batch_index
            < len(batches) - 1
        ):

            time.sleep(1.05)

    return pd.DataFrame(output)


# ============================================================
# 1-MINUTE DATA
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
        timeout=30,
    )

    if response.status_code != 200:
        return pd.DataFrame()

    body = response.json()

    close = body.get(
        "close",
        []
    )

    if not close:
        return pd.DataFrame()

    result = pd.DataFrame(
        {
            "timestamp":
                body.get(
                    "timestamp",
                    []
                ),

            "open":
                body.get(
                    "open",
                    []
                ),

            "high":
                body.get(
                    "high",
                    []
                ),

            "low":
                body.get(
                    "low",
                    []
                ),

            "close":
                body.get(
                    "close",
                    []
                ),

            "volume":
                body.get(
                    "volume",
                    []
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

    return (
        result
        .dropna(
            subset=[
                "high",
                "low",
                "close",
                "volume",
            ]
        )
        .reset_index(drop=True)
    )


# ============================================================
# FUNDAMENTALS
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def fetch_fundamentals(
    symbol
):

    if not TWELVE_DATA_API_KEY:

        return {
            "available": False,
            "reason":
                "TWELVE_DATA_API_KEY not configured",
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
            timeout=25,
        )

        if response.status_code != 200:

            return {
                "available": False,
                "reason":
                    api_error(response),
            }

        data = response.json()

        statistics = data.get(
            "statistics",
            {}
        )

        if not statistics:

            return {
                "available": False,
                "reason":
                    "No statistics returned",
            }

        valuations = statistics.get(
            "valuations_metrics",
            {}
        )

        stock_statistics = statistics.get(
            "stock_statistics",
            {}
        )

        price_summary = statistics.get(
            "stock_price_summary",
            {}
        )

        balance_sheet = statistics.get(
            "balance_sheet",
            {}
        )

        return {
            "available": True,

            "pe":
                valuations.get(
                    "trailing_pe"
                ),

            "float_shares":
                stock_statistics.get(
                    "float_shares"
                ),

            "beta":
                price_summary.get(
                    "beta"
                ),

            "debt_equity":
                balance_sheet.get(
                    "total_debt_to_equity_mrq"
                ),
        }

    except Exception as error:

        return {
            "available": False,
            "reason": str(error),
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

    total_volume = volume.sum()

    if total_volume <= 0:
        return None

    return float(
        (
            typical_price * volume
        ).sum()
        / total_volume
    )


def calculate_ema(
    candles,
    period
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

    average_volume = (
        candles["volume"]
        .iloc[-21:-1]
        .mean()
    )

    if average_volume <= 0:
        return None

    return float(
        candles["volume"].iloc[-1]
        / average_volume
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

    true_range = pd.concat(
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
        true_range
        .rolling(period)
        .mean()
    )

    hl2 = (
        candles["high"]
        + candles["low"]
    ) / 2

    upper_band = (
        hl2
        + multiplier * atr
    )

    lower_band = (
        hl2
        - multiplier * atr
    )

    if pd.isna(
        lower_band.iloc[-1]
    ):
        return None

    return bool(
        candles["close"].iloc[-1]
        > lower_band.iloc[-1]
        and
        candles["close"].iloc[-1]
        >= candles["close"].iloc[-2]
    )


def calculate_momentum(
    candles
):

    if len(candles) < 6:
        return None

    old_price = float(
        candles["close"].iloc[-6]
    )

    current_price = float(
        candles["close"].iloc[-1]
    )

    if old_price <= 0:
        return None

    return (
        (
            current_price
            / old_price
        ) - 1
    ) * 100


# ============================================================
# POSITION SIZER
# ============================================================

def calculate_position(
    price
):

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
# VERDICT
# ============================================================

def verdict_html(
    verdict
):

    if verdict is True:

        return (
            '<span class="qb-pass">'
            '🟢 PASS'
            '</span>'
        )

    if verdict is False:

        return (
            '<span class="qb-fail">'
            '🔴 FAIL'
            '</span>'
        )

    return (
        '<span class="qb-na">'
        '⚪ DATA N/A'
        '</span>'
    )


# ============================================================
# EVALUATE STOCK
# ============================================================

def evaluate_stock(
    stock,
    candles,
    fundamentals
):

    price = float(
        stock["last_price"]
    )

    volume = float(
        stock["volume"]
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

    vwap = calculate_vwap(
        candles
    )

    ema9 = calculate_ema(
        candles,
        EMA_FAST
    )

    ema21 = calculate_ema(
        candles,
        EMA_SLOW
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

    # Free-float market cap:
    # price × float shares / 1 crore
    if (
        float_shares is not None
        and
        pd.notna(float_shares)
    ):

        free_float_mcap_cr = (
            price
            * float(float_shares)
            / 10000000
        )

    else:

        free_float_mcap_cr = None

    rows = []

    # --------------------------------------------------------
    # 1. P/E
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "TTM P/E ≤ 25",

            "verdict":
                (
                    float(pe) <= PE_MAX
                    if pe is not None
                    else None
                ),

            "metric":
                (
                    f"{float(pe):.2f}"
                    if pe is not None
                    else
                    "Unavailable"
                ),
        }
    )

    # --------------------------------------------------------
    # 2. CMP
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "CMP ₹50 – ₹500",

            "verdict":
                (
                    CMP_MIN
                    <= price
                    <= CMP_MAX
                ),

            "metric":
                f"₹{price:,.2f}",
        }
    )

    # --------------------------------------------------------
    # 3. Beta
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Beta 0.60 – 1.20",

            "verdict":
                (
                    BETA_MIN
                    <= float(beta)
                    <= BETA_MAX
                    if beta is not None
                    else None
                ),

            "metric":
                (
                    f"{float(beta):.2f}"
                    if beta is not None
                    else
                    "Unavailable"
                ),
        }
    )

    # --------------------------------------------------------
    # 4. Free float market cap
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Free-Float Market Cap ≥ ₹5,000 Cr",

            "verdict":
                (
                    free_float_mcap_cr
                    >= FREE_FLOAT_MCAP_MIN_CR
                    if free_float_mcap_cr is not None
                    else None
                ),

            "metric":
                (
                    f"₹{free_float_mcap_cr:,.0f} Cr"
                    if free_float_mcap_cr is not None
                    else
                    "Unavailable"
                ),
        }
    )

    # --------------------------------------------------------
    # 5. Volume
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Volume ≥ 5 Lakh Shares",

            "verdict":
                volume >= VOLUME_MIN,

            "metric":
                f"{volume:,.0f}",
        }
    )

    # --------------------------------------------------------
    # 6. Debt / Equity
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Debt-to-Equity",

            "verdict":
                None,

            "metric":
                (
                    f"{float(debt_equity):.2f} "
                    "(threshold not defined)"
                    if debt_equity is not None
                    else
                    "Unavailable"
                ),
        }
    )

    # --------------------------------------------------------
    # 7. VWAP
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Price ≥ Intraday VWAP",

            "verdict":
                (
                    price >= vwap
                    if vwap is not None
                    else None
                ),

            "metric":
                (
                    f"Price ₹{price:,.2f} | "
                    f"VWAP ₹{vwap:,.4f}"
                    if vwap is not None
                    else
                    "Unavailable"
                ),
        }
    )

    # --------------------------------------------------------
    # 8. EMA 9 / 21
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "EMA 9 > EMA 21",

            "verdict":
                (
                    ema9 > ema21
                    if (
                        ema9 is not None
                        and
                        ema21 is not None
                    )
                    else None
                ),

            "metric":
                (
                    f"9 EMA ₹{ema9:,.2f} | "
                    f"21 EMA ₹{ema21:,.2f}"
                    if (
                        ema9 is not None
                        and
                        ema21 is not None
                    )
                    else
                    "Unavailable"
                ),
        }
    )

    # --------------------------------------------------------
    # 9. Supertrend
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Supertrend Bullish",

            "verdict":
                supertrend,

            "metric":
                (
                    "Bullish"
                    if supertrend is True
                    else
                    "Bearish"
                    if supertrend is False
                    else
                    "Unavailable"
                ),
        }
    )

    # --------------------------------------------------------
    # 10. Volume surge
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Current Volume ≥ 2× Average",

            "verdict":
                (
                    volume_ratio
                    >= VOLUME_SURGE_MULTIPLIER
                    if volume_ratio is not None
                    else None
                ),

            "metric":
                (
                    f"{volume_ratio:.2f}×"
                    if volume_ratio is not None
                    else
                    "Unavailable"
                ),
        }
    )

    # --------------------------------------------------------
    # 11. Momentum
    # --------------------------------------------------------

    rows.append(
        {
            "parameter":
                "Positive Intraday Momentum",

            "verdict":
                (
                    momentum > 0
                    if momentum is not None
                    else None
                ),

            "metric":
                (
                    f"{momentum:+.3f}% / 5 bars"
                    if momentum is not None
                    else
                    "Unavailable"
                ),
        }
    )

    passes = sum(
        row["verdict"] is True
        for row in rows
    )

    fails = sum(
        row["verdict"] is False
        for row in rows
    )

    unavailable = sum(
        row["verdict"] is None
        for row in rows
    )

    score = (
        passes / len(rows)
    ) * 100

    return {
        "rows": rows,
        "passes": passes,
        "fails": fails,
        "unavailable": unavailable,
        "score": score,
    }


# ============================================================
# SCANNER
# ============================================================

def run_scanner():

    universe = get_nse_equities()

    quotes = fetch_live_quotes(
        universe["security_id"].tolist()
    )

    if quotes.empty:
        raise RuntimeError(
            "Dhan returned no live quote data."
        )

    market = universe.merge(
        quotes,
        on="security_id",
        how="inner",
    )

    numeric_columns = [
        "last_price",
        "volume",
        "net_change",
        "open",
        "high",
        "low",
        "previous_close",
    ]

    for column in numeric_columns:

        market[column] = pd.to_numeric(
            market[column],
            errors="coerce",
        )

    market = market.dropna(
        subset=[
            "last_price",
            "volume",
        ]
    )

    # --------------------------------------------------------
    # Live price and volume filter
    # --------------------------------------------------------

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

        return {
            "universe": universe,
            "market": market,
            "results": [],
        }

    # Highest volume stocks are checked first.
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

    technical_results = []

    for _, stock in candidates.iterrows():

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
                EMA_FAST
            )

            ema21 = calculate_ema(
                candles,
                EMA_SLOW
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

            if (
                vwap is not None
                and
                float(stock["last_price"])
                >= vwap
            ):
                technical_score += 1

            if (
                ema9 is not None
                and
                ema21 is not None
                and
                ema9 > ema21
            ):
                technical_score += 1

            if supertrend is True:
                technical_score += 1

            if (
                volume_ratio is not None
                and
                volume_ratio >= 2
            ):
                technical_score += 1

            if (
                momentum is not None
                and
                momentum > 0
            ):
                technical_score += 1

            technical_results.append(
                {
                    "stock": stock,
                    "candles": candles,
                    "technical_score":
                        technical_score,
                }
            )

        except Exception:
            continue

    technical_results.sort(
        key=lambda x: (
            x["technical_score"],
            float(
                x["stock"]["volume"]
            ),
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # Fundamental evaluation
    # --------------------------------------------------------

    final_results = []

    for item in technical_results[
        :FUNDAMENTAL_CANDIDATES
    ]:

        stock = item["stock"]

        fundamentals = (
            fetch_fundamentals(
                stock["symbol"]
            )
        )

        evaluation = evaluate_stock(
            stock,
            item["candles"],
            fundamentals,
        )

        final_results.append(
            {
                "stock": stock,
                "candles": item["candles"],
                "fundamentals":
                    fundamentals,
                "evaluation":
                    evaluation,
            }
        )

    final_results.sort(
        key=lambda x: (
            x["evaluation"]["passes"],
            -x["evaluation"]["fails"],
            x["evaluation"]["score"],
            float(
                x["stock"]["volume"]
            ),
        ),
        reverse=True,
    )

    return {
        "universe": universe,
        "market": market,
        "results": final_results,
    }


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
<div class="qb-header">

<div>

<div class="qb-brand">
<span>⚡</span> QUANTbreakout
</div>

<div class="qb-subtitle">
REAL-TIME NSE MOMENTUM & BREAKOUT SCANNER
</div>

</div>

<div class="qb-live">
● LIVE ENGINE
</div>

</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# CREDENTIAL SCREEN
# ============================================================

if not DHAN_CLIENT_ID or not DHAN_ACCESS_TOKEN:

    st.markdown(
        """
<div class="qb-winner">

<div class="qb-winner-badge">
⚡ QUANTBREAKOUT
</div>

<div class="qb-winner-symbol">
LIVE CONNECTION REQUIRED
</div>

<div class="qb-winner-name">
DhanHQ credentials are missing.
</div>

</div>
""",
        unsafe_allow_html=True,
    )

    st.error(
        "Configure DHAN_CLIENT_ID and "
        "DHAN_ACCESS_TOKEN in Streamlit Secrets."
    )

    st.stop()


# ============================================================
# NATIVE STREAMLIT AUTO REFRESH
#
# No streamlit_autorefresh package required.
# ============================================================

@st.fragment(run_every="15s")
def live_terminal():

    scan_started = time.time()

    try:

        with st.spinner(
            "Connecting to live NSE market data..."
        ):

            data = run_scanner()

    except Exception as error:

        st.error(
            "LIVE DATA CONNECTION ERROR"
        )

        st.code(
            str(error)
        )

        st.info(
            "Check your Dhan credentials, "
            "Dhan API access and market status."
        )

        return

    universe = data["universe"]

    market = data["market"]

    results = data["results"]

    # --------------------------------------------------------
    # No candidates
    # --------------------------------------------------------

    if not results:

        st.warning(
            "No stock currently satisfies the "
            "live ₹50–₹500 and 5-lakh volume filter."
        )

        st.caption(
            "The scanner is still connected to "
            f"{len(market):,} live NSE instruments."
        )

        return

    # --------------------------------------------------------
    # WINNER
    # --------------------------------------------------------

    winner = results[0]

    stock = winner["stock"]

    evaluation = winner["evaluation"]

    price = float(
        stock["last_price"]
    )

    change = stock["net_change"]

    if pd.notna(change):

        change_text = (
            f"{float(change):+.2f}"
        )

    else:

        change_text = "—"

    # --------------------------------------------------------
    # MARKET CARDS
    # --------------------------------------------------------

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:

        st.markdown(
            f"""
<div class="qb-card">
<div class="qb-card-label">
NSE INSTRUMENTS
</div>
<div class="qb-card-value">
{len(universe):,}
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with c2:

        st.markdown(
            f"""
<div class="qb-card">
<div class="qb-card-label">
LIVE QUOTES
</div>
<div class="qb-card-value">
{len(market):,}
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with c3:

        st.markdown(
            f"""
<div class="qb-card">
<div class="qb-card-label">
WINNER PASS
</div>
<div class="qb-card-value">
{evaluation["passes"]}/11
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with c4:

        st.markdown(
            f"""
<div class="qb-card">
<div class="qb-card-label">
SCORE
</div>
<div class="qb-card-value">
{evaluation["score"]:.1f}%
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with c5:

        st.markdown(
            f"""
<div class="qb-card">
<div class="qb-card-label">
UPDATED
</div>
<div class="qb-card-value">
{datetime.now().strftime("%H:%M:%S")}
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # WINNER CARD
    # --------------------------------------------------------

    st.markdown(
        f"""
<div class="qb-winner">

<div class="qb-winner-badge">
⭐ REAL-TIME QUANT BREAKOUT WINNER
</div>

<div class="qb-winner-symbol">
{stock["symbol"]}
</div>

<div class="qb-winner-name">
{stock["name"]}
</div>

<div class="qb-winner-price">
₹{price:,.2f}
</div>

<div class="qb-winner-change">
Live Change: {change_text}
</div>

</div>
""",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # MATRIX
    # --------------------------------------------------------

    st.markdown(
        """
<div class="qb-panel">

<div class="qb-panel-title">
📊 11-PARAMETER STRATEGY PERFORMANCE GRID
</div>

<div class="qb-table-wrap">

<table class="qb-table">

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
""",
        unsafe_allow_html=True,
    )

    table_rows = ""

    for index, row in enumerate(
        evaluation["rows"],
        start=1,
    ):

        table_rows += f"""
<tr>

<td>{index}</td>

<td>{row["parameter"]}</td>

<td>{stock["symbol"]}</td>

<td>{stock["name"]}</td>

<td>{verdict_html(row["verdict"])}</td>

<td>{row["metric"]}</td>

</tr>
"""

    st.markdown(
        table_rows
        + """
</tbody>
</table>

</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # POSITION CALCULATOR
    # --------------------------------------------------------

    shares, risk_unit, sl, tp = (
        calculate_position(price)
    )

    st.markdown(
        f"""
<div class="qb-position">

<div class="qb-position-title">
🧮 FIXED STRATEGY RISK BRACKET — ₹15,000 CAPITAL
</div>

<div class="qb-position-grid">

<div class="qb-position-item">

<div class="qb-position-label">
TARGET POSITION
</div>

<div class="qb-position-value">
BUY EXACTLY {shares} SHARES
</div>

</div>

<div class="qb-position-item">

<div class="qb-position-label">
RISK UNIT — 0.8%
</div>

<div class="qb-position-value">
₹{risk_unit:,.2f}
</div>

</div>

<div class="qb-position-item">

<div class="qb-position-label">
🔒 AUTOMATED SL FLOOR
</div>

<div class="qb-position-value">
₹{sl:,.2f}
</div>

</div>

<div class="qb-position-item">

<div class="qb-position-label">
🎯 AUTOMATED TP CEILING
</div>

<div class="qb-position-value">
₹{tp:,.2f}
</div>

</div>

</div>

</div>
""",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # MANUAL CHECK
    # --------------------------------------------------------

    st.markdown(
        """
<div class="qb-panel">

<div class="qb-panel-title">
🔍 MANUAL CHECK OVERRIDE
</div>

</div>
""",
        unsafe_allow_html=True,
    )

    manual_symbol = st.text_input(
        "Manual NSE symbol",
        placeholder="Example: INFY",
        key="manual_symbol",
    )

    if manual_symbol:

        symbol = (
            manual_symbol
            .strip()
            .upper()
        )

        matching = market[
            market["symbol"]
            .eq(symbol)
        ]

        if matching.empty:

            # Search the live Dhan universe
            # rather than using hardcoded symbols.

            matching = universe[
                universe["symbol"]
                .eq(symbol)
            ]

            if matching.empty:

                st.error(
                    f"{symbol} was not found "
                    "in Dhan's current NSE instrument master."
                )

            else:

                manual_stock = matching.iloc[0]

                # Fetch real-time quote specifically
                manual_quotes = (
                    fetch_live_quotes(
                        [
                            manual_stock[
                                "security_id"
                            ]
                        ]
                    )
                )

                if manual_quotes.empty:

                    st.error(
                        "Dhan did not return "
                        "live quote data for "
                        f"{symbol}."
                    )

                else:

                    manual_stock = (
                        manual_stock
                        .to_frame()
                        .T
                        .merge(
                            manual_quotes,
                            on="security_id",
                            how="inner",
                        )
                        .iloc[0]
                    )

                    show_manual_result(
                        manual_stock
                    )

        else:

            manual_stock = (
                matching.iloc[0]
            )

            show_manual_result(
                manual_stock
            )

    # --------------------------------------------------------
    # SCAN INFORMATION
    # --------------------------------------------------------

    elapsed = (
        time.time()
        - scan_started
    )

    st.caption(
        "LIVE DhanHQ market snapshot • "
        f"Scanner cycle: {elapsed:.1f}s • "
        "Automatic refresh: 15 seconds"
    )


# ============================================================
# MANUAL RESULT FUNCTION
# ============================================================

def show_manual_result(
    stock
):

    with st.spinner(
        "Loading live manual analysis..."
    ):

        candles = fetch_intraday(
            stock["security_id"]
        )

        fundamentals = (
            fetch_fundamentals(
                stock["symbol"]
            )
        )

    if candles.empty:

        st.warning(
            "Live 1-minute candle data "
            "is currently unavailable for "
            f"{stock['symbol']}."
        )

        return

    evaluation = evaluate_stock(
        stock,
        candles,
        fundamentals,
    )

    price = float(
        stock["last_price"]
    )

    st.success(
        f"Live manual check completed: "
        f"{stock['symbol']} @ ₹{price:,.2f}"
    )

    html = """
<div class="qb-table-wrap">

<table class="qb-table">

<thead>

<tr>
<th>#</th>
<th>PARAMETER</th>
<th>VERDICT</th>
<th>LIVE METRIC VALUE</th>
</tr>

</thead>

<tbody>
"""

    for index, row in enumerate(
        evaluation["rows"],
        start=1,
    ):

        html += f"""
<tr>
<td>{index}</td>
<td>{row["parameter"]}</td>
<td>{verdict_html(row["verdict"])}</td>
<td>{row["metric"]}</td>
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

    shares, risk_unit, sl, tp = (
        calculate_position(price)
    )

    st.markdown(
        f"""
<div class="qb-position">

<div class="qb-position-title">
MANUAL POSITION CALCULATOR
</div>

<div class="qb-position-grid">

<div class="qb-position-item">
<div class="qb-position-label">
SHARES
</div>
<div class="qb-position-value">
{shares}
</div>
</div>

<div class="qb-position-item">
<div class="qb-position-label">
RISK UNIT
</div>
<div class="qb-position-value">
₹{risk_unit:,.2f}
</div>
</div>

<div class="qb-position-item">
<div class="qb-position-label">
STOP LOSS
</div>
<div class="qb-position-value">
₹{sl:,.2f}
</div>
</div>

<div class="qb-position-item">
<div class="qb-position-label">
TAKE PROFIT
</div>
<div class="qb-position-value">
₹{tp:,.2f}
</div>
</div>

</div>

</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# START TERMINAL
# ============================================================

live_terminal()


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
<div style="
    text-align:center;
    color:#64748b;
    font-size:0.62rem;
    font-weight:700;
    margin-top:15px;
">
⚡ QUANTbreakout • Live market data powered by DhanHQ
</div>
""",
    unsafe_allow_html=True,
)
