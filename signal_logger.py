"""
signal_logger.py
-----------------
Appends a row to signal_log.csv every time the scanner's Tier-2 winner
evaluation runs, so you can look back later and check whether high-scoring
signals actually tended to move favorably (see backtest.py for a proper
historical version of that same question).

Same persistence caveat as portfolio.py: this file lives in the app's
working folder and normally survives reruns, but not guaranteed across a
Streamlit Cloud container restart/redeploy. Download it periodically via
the button in the app if you want to keep history long-term.
"""

from __future__ import annotations

import csv
import datetime as dt
import os

LOG_FILE = "signal_log.csv"
FIELDS = ["timestamp_ist", "symbol", "ltp", "volume", "technical_score", "matrix_score_pct"]


def log_signal(symbol: str, ltp: float, volume: int, technical_score: int, matrix_score_pct: float,
               ist_tz) -> None:
    is_new = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "timestamp_ist": dt.datetime.now(ist_tz).strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "ltp": round(ltp, 2),
            "volume": volume,
            "technical_score": technical_score,
            "matrix_score_pct": matrix_score_pct,
        })


def read_log_bytes() -> bytes:
    if not os.path.exists(LOG_FILE):
        return b""
    with open(LOG_FILE, "rb") as f:
        return f.read()
