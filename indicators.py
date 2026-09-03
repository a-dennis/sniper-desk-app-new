"""
indicators.py
-------------
Real calculations for the intraday-technical rows of the 11-parameter matrix
(VWAP, EMA 9/21 cross, Supertrend, volume surge, momentum), computed from the
1-minute candles Kotak Neo returns.

The notepad's spec allows defaulting rows 8–11 to a hardcoded PASS "if your
data endpoint throttles this metric" — but since we have real 1-min OHLCV
from a broker feed (not a scraped/rate-limited source), these are computed
properly instead. Each function falls back to None (-> DATA UNAVAILABLE in
the UI) only when there genuinely isn't enough candle history yet, e.g. in
the first few minutes after market open.
"""

from __future__ import annotations

import pandas as pd


def vwap_check(df: pd.DataFrame, ltp: float) -> tuple[str, str]:
    if df.empty or len(df) < 1:
        return "unavailable", "Insufficient candle history"
    typical = (df["high"] + df["low"] + df["close"]) / 3
    vwap = (typical * df["volume"]).sum() / max(df["volume"].sum(), 1)
    verdict = "pass" if ltp >= vwap else "fail"
    return verdict, f"₹{vwap:.2f} (Price {'>' if ltp >= vwap else '<'} VWAP)"


def ema_cross_check(df: pd.DataFrame) -> tuple[str, str]:
    if len(df) < 21:
        return "unavailable", "Need 21+ 1-min candles"
    ema9 = df["close"].ewm(span=9, adjust=False).mean().iloc[-1]
    ema21 = df["close"].ewm(span=21, adjust=False).mean().iloc[-1]
    verdict = "pass" if ema9 > ema21 else "fail"
    return verdict, f"9 EMA: ₹{ema9:.2f} | 21 EMA: ₹{ema21:.2f} ({'>' if ema9 > ema21 else '<='})"


def supertrend_check(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple[str, str]:
    if len(df) < period + 1:
        return "unavailable", "Need more candle history"
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    hl2 = (high + low) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    trend = [True] * len(df)  # True = bullish
    for i in range(1, len(df)):
        if close.iloc[i] > upper.iloc[i - 1]:
            trend[i] = True
        elif close.iloc[i] < lower.iloc[i - 1]:
            trend[i] = False
        else:
            trend[i] = trend[i - 1]

    bullish = trend[-1]
    return ("pass" if bullish else "fail"), ("Bullish" if bullish else "Bearish")


def volume_surge_check(df: pd.DataFrame) -> tuple[str, str]:
    if len(df) < 21:
        return "unavailable", "Need 20+ prior 1-min bars"
    last_vol = df["volume"].iloc[-1]
    avg_prev20 = df["volume"].iloc[-21:-1].mean()
    if avg_prev20 <= 0:
        return "unavailable", "No volume baseline"
    ratio = last_vol / avg_prev20
    verdict = "pass" if ratio >= 2.0 else "fail"
    return verdict, f"{ratio:.2f}x (vs 20-bar avg)"


def fresh_vwap_cross_check(df: pd.DataFrame) -> tuple[bool, str]:
    """Detects a stock that crossed above VWAP within the last 2 bars (not
    one that's been sitting above VWAP for a while), with a volume surge on
    the bar it crossed -- catches the moment of a move starting, rather
    than a move that's already underway or exhausted.

    Checks the last 2 bars (not just the single most recent one) for the
    cross -- the scanner only refreshes every ~8-10 seconds, so requiring
    the cross to be on the literal single latest bar made this signal
    almost impossible to actually catch in practice.
    """
    if len(df) < 23:
        return False, "Need 22+ 1-min bars to check for a fresh cross"
    typical = (df["high"] + df["low"] + df["close"]) / 3
    cum_vol = df["volume"].cumsum()
    vwap_series = (typical * df["volume"]).cumsum() / cum_vol.replace(0, 1)

    avg_prev20 = df["volume"].iloc[-21:-1].mean()

    for offset in (1, 2):  # check the most recent bar, then one before it
        prev_close, prev_vwap = df["close"].iloc[-offset - 1], vwap_series.iloc[-offset - 1]
        curr_close, curr_vwap = df["close"].iloc[-offset], vwap_series.iloc[-offset]
        crossed_up = prev_close <= prev_vwap and curr_close > curr_vwap
        if not crossed_up:
            continue
        last_vol = df["volume"].iloc[-offset]
        ratio = (last_vol / avg_prev20) if avg_prev20 > 0 else 0
        if ratio >= 2.0:
            when = "this bar" if offset == 1 else "the previous bar"
            return True, f"Crossed above VWAP ({curr_vwap:.2f}) on {when} with {ratio:.2f}x volume surge"

    curr_close, curr_vwap = df["close"].iloc[-1], vwap_series.iloc[-1]
    return False, f"No fresh cross in the last 2 bars (price currently {'above' if curr_close > curr_vwap else 'below'} VWAP)"


def momentum_check(df: pd.DataFrame) -> tuple[str, str]:
    if len(df) < 6:
        return "unavailable", "Need 5+ prior 1-min bars"
    now_close = df["close"].iloc[-1]
    then_close = df["close"].iloc[-6]
    if then_close <= 0:
        return "unavailable", "Bad baseline price"
    pct = (now_close - then_close) / then_close * 100
    verdict = "pass" if pct > 0 else "fail"
    return verdict, f"{pct:+.2f}% (vs 5 bars ago)"
