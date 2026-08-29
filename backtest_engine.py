"""
backtest_engine.py
-------------------
Core historical backtest logic, shared between backtest.py (the standalone
CLI script) and the "Backtest" button in app.py. Given a symbol, replays
its recent 1-minute candles bar-by-bar, computes the same 5-signal
technical score used live, and checks what actually happened to the price
afterward -- using only data available at each point in time (no lookahead
bias).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

MIN_WARMUP_BARS = 21


def _vwap_pass(day_df, i):
    window = day_df.iloc[:i + 1]
    if window.empty:
        return False
    typical = (window["High"] + window["Low"] + window["Close"]) / 3
    vwap = (typical * window["Volume"]).sum() / max(window["Volume"].sum(), 1)
    return day_df["Close"].iloc[i] >= vwap


def _ema_cross_pass(day_df, i):
    if i < MIN_WARMUP_BARS:
        return False
    window = day_df["Close"].iloc[:i + 1]
    ema9 = window.ewm(span=9, adjust=False).mean().iloc[-1]
    ema21 = window.ewm(span=21, adjust=False).mean().iloc[-1]
    return ema9 > ema21


def _supertrend_pass(day_df, i, period=10, multiplier=3.0):
    if i < period + 1:
        return False
    window = day_df.iloc[:i + 1]
    high, low, close = window["High"], window["Low"], window["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    hl2 = (high + low) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    trend = True
    for j in range(1, len(window)):
        if close.iloc[j] > upper.iloc[j - 1]:
            trend = True
        elif close.iloc[j] < lower.iloc[j - 1]:
            trend = False
    return trend


def _volume_surge_pass(day_df, i):
    if i < MIN_WARMUP_BARS:
        return False
    last_vol = day_df["Volume"].iloc[i]
    avg_prev20 = day_df["Volume"].iloc[max(0, i - 20):i].mean()
    if avg_prev20 <= 0:
        return False
    return (last_vol / avg_prev20) >= 2.0


def _momentum_pass(day_df, i):
    if i < 6:
        return False
    now_close = day_df["Close"].iloc[i]
    then_close = day_df["Close"].iloc[i - 5]
    if then_close <= 0:
        return False
    return now_close > then_close


def _technical_score_at(day_df, i):
    checks = [_vwap_pass, _ema_cross_pass, _supertrend_pass, _volume_surge_pass, _momentum_pass]
    return sum(1 for check in checks if check(day_df, i))


@st.cache_data(ttl=60 * 60, show_spinner=False)
def run_symbol_backtest(symbol: str, lookahead_minutes: int = 15, min_score: int = 4) -> dict:
    """Backtests one symbol over the last ~7 days of real 1-minute data.

    Returns a dict with a "verdict" of PASS, FAIL, or INSUFFICIENT_DATA:
      - PASS: at least 10 historical bars hit `min_score`+, and price was
        higher `lookahead_minutes` later more than half the time.
      - FAIL: same sample size, but win rate was 50% or below.
      - INSUFFICIENT_DATA: fewer than 10 qualifying historical bars found
        (Yahoo's free 1-minute history only covers about a week, so thinly
        traded stocks or ones that rarely hit the score bar may not have
        enough history to say anything reliable).
    """
    try:
        df = yf.Ticker(f"{symbol}.NS").history(period="7d", interval="1m")
    except Exception as e:
        return {"symbol": symbol, "verdict": "INSUFFICIENT_DATA", "detail": f"Could not fetch data: {e}"}

    if df.empty:
        return {"symbol": symbol, "verdict": "INSUFFICIENT_DATA", "detail": "No historical data returned"}

    df["date"] = df.index.date
    returns = []
    for date, day_df in df.groupby("date"):
        day_df = day_df.reset_index(drop=True)
        n = len(day_df)
        if n < MIN_WARMUP_BARS + lookahead_minutes + 1:
            continue
        for i in range(MIN_WARMUP_BARS, n - lookahead_minutes):
            score = _technical_score_at(day_df, i)
            if score < min_score:
                continue
            entry = day_df["Close"].iloc[i]
            future = day_df["Close"].iloc[i + lookahead_minutes]
            returns.append((future - entry) / entry * 100)

    if len(returns) < 10:
        return {
            "symbol": symbol, "verdict": "INSUFFICIENT_DATA", "sample_count": len(returns),
            "detail": f"Only {len(returns)} historical {min_score}+/5 signals found in the last 7 days -- too few to judge reliably.",
        }

    win_rate = sum(1 for r in returns if r > 0) / len(returns) * 100
    avg_return = sum(returns) / len(returns)
    verdict = "PASS" if win_rate > 50 else "FAIL"
    return {
        "symbol": symbol, "verdict": verdict, "sample_count": len(returns),
        "win_rate": round(win_rate, 1), "avg_return": round(avg_return, 3),
        "lookahead_minutes": lookahead_minutes, "min_score": min_score,
        "detail": f"{len(returns)} historical {min_score}+/5 signals in the last 7 days: "
                  f"{win_rate:.1f}% were higher {lookahead_minutes} min later (avg {avg_return:+.2f}%).",
    }
