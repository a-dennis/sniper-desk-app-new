"""
breakout_engine.py
-------------------
Opening Range Breakout + Retest + Anti-Chase logic, adapted from the
INTRADAY_TRADING_ENGINE_V2 spec. This is a SEPARATE, more selective check
from the main 5-signal scanner -- its whole purpose is to catch stocks
BEFORE you'd be chasing an already-exhausted move, which is exactly the
SAIL-style problem this was built to address.

Sequence it looks for, on 5-minute candles:
    Opening Range (9:15-9:30) established
        -> price closes beyond that range on a strong candle (breakout)
        -> price pulls back and HOLDS near the breakout level (retest)
        -> retest candle closes back in the breakout direction (entry trigger)

If price has already moved too far past where the retest entry would be,
the Chase Filter cancels the signal rather than telling you to buy an
extended move -- it puts it on a watchlist instead.

This does NOT yet include: market regime (NIFTY trend filter), sector/
relative-strength ranking, or the full scoring system from the original
spec -- those are a larger, separate build. This piece specifically
targets the "I entered right as it was exhausted" problem.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def calculate_atr(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = candles["high"], candles["low"], candles["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def get_opening_range(candles: pd.DataFrame):
    """Returns (or_high, or_low) from the 9:15-9:30 IST window on the most
    recent trading day present in `candles`. Returns (None, None) if that
    window isn't present (e.g. candle history starts later than 9:15)."""
    if candles.empty:
        return None, None
    idx = candles.index
    if idx.tz is None:
        idx = idx.tz_localize(IST)
    else:
        idx = idx.tz_convert(IST)
    last_date = idx.date.max()
    mask = (idx.date == last_date) & (idx.time >= dt.time(9, 15)) & (idx.time < dt.time(9, 30))
    window = candles.loc[mask]
    if window.empty:
        return None, None
    return float(window["high"].max()), float(window["low"].min())


def _candle_quality_long(row) -> bool:
    rng = row["high"] - row["low"]
    if rng <= 0:
        return False
    clv = (row["close"] - row["low"]) / rng
    body_ratio = abs(row["close"] - row["open"]) / rng
    return row["close"] > row["open"] and clv >= 0.70 and body_ratio >= 0.50


def _candle_quality_short(row) -> bool:
    rng = row["high"] - row["low"]
    if rng <= 0:
        return False
    clv = (row["high"] - row["close"]) / rng
    body_ratio = abs(row["close"] - row["open"]) / rng
    return row["close"] < row["open"] and clv >= 0.70 and body_ratio >= 0.50


def detect_setup(candles: pd.DataFrame) -> dict:
    """Scans the session's candles in order and returns the current setup
    state for LONG and SHORT. Returns a dict:
        state: "NO_SETUP" | "WATCHING_RETEST" | "READY_TO_ENTER" | "TOO_LATE_CHASE"
        direction: "LONG" | "SHORT" | None
        entry_price, stop_loss, target, detail
    """
    result = {"state": "NO_SETUP", "direction": None, "entry_price": None,
              "stop_loss": None, "target": None, "detail": "Not enough data yet."}

    if candles is None or len(candles) < 20:
        have = 0 if candles is None else len(candles)
        result["detail"] = (f"Only {have} five-minute candle(s) available so far today -- need at least 20 "
                             f"(~100 minutes of trading) before the opening range and any breakout/retest "
                             f"pattern can be evaluated. This is expected early in the session, not an error.")
        return result

    atr = calculate_atr(candles)
    or_high, or_low = get_opening_range(candles)
    if or_high is None:
        result["detail"] = "Opening range (9:15-9:30) not found in the available candle history."
        return result

    # Only look at candles after the opening range window
    idx = candles.index
    idx_ist = idx.tz_localize(IST) if idx.tz is None else idx.tz_convert(IST)
    post_or_mask = idx_ist.time >= dt.time(9, 30)
    post_or = candles.loc[post_or_mask].copy()
    post_or["atr"] = atr.loc[post_or_mask]
    if post_or.empty or post_or["atr"].isna().all():
        result["detail"] = "Not enough post-opening-range candles yet to evaluate."
        return result

    breakout_direction = None
    breakout_level = None
    breakout_idx = None

    for i in range(len(post_or)):
        row = post_or.iloc[i]
        if pd.isna(row["atr"]):
            continue
        if row["close"] > or_high and _candle_quality_long(row):
            breakout_direction, breakout_level, breakout_idx = "LONG", or_high, i
            break
        if row["close"] < or_low and _candle_quality_short(row):
            breakout_direction, breakout_level, breakout_idx = "SHORT", or_low, i
            break

    if breakout_direction is None:
        result["detail"] = "No opening-range breakout candle found yet this session."
        return result

    current_price = float(candles["close"].iloc[-1])
    current_atr = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None
    if current_atr is None or current_atr <= 0:
        result["detail"] = "ATR unavailable, can't evaluate retest/chase distance."
        return result

    # Look for a retest AFTER the breakout candle
    after_breakout = post_or.iloc[breakout_idx + 1:]
    retest_entry = None
    for i in range(len(after_breakout)):
        row = after_breakout.iloc[i]
        if breakout_direction == "LONG":
            if row["low"] <= breakout_level + 0.20 * current_atr and row["close"] >= breakout_level and row["close"] > row["open"]:
                retest_entry = float(row["high"])
                break
        else:
            if row["high"] >= breakout_level - 0.20 * current_atr and row["close"] <= breakout_level and row["close"] < row["open"]:
                retest_entry = float(row["low"])
                break

    if retest_entry is None:
        result.update({
            "state": "WATCHING_RETEST", "direction": breakout_direction,
            "detail": f"{breakout_direction} breakout confirmed at {breakout_level:.2f}. "
                      f"Waiting for a retest (pullback that holds) before treating it as a valid entry -- "
                      f"buying right now would be chasing the breakout candle itself.",
        })
        return result

    # Chase filter: how far has price already moved past the retest entry?
    if breakout_direction == "LONG":
        chase_distance = (current_price - retest_entry) / current_atr
    else:
        chase_distance = (retest_entry - current_price) / current_atr

    if chase_distance > 0.50:
        result.update({
            "state": "TOO_LATE_CHASE", "direction": breakout_direction,
            "entry_price": retest_entry,
            "detail": f"A valid {breakout_direction} retest entry existed at {retest_entry:.2f}, but price has "
                      f"already moved {chase_distance:.2f} ATR beyond it -- entering now would be chasing. "
                      f"This setup is being skipped, not signaled.",
        })
        return result

    # Stops and target
    lookback = candles.tail(20)
    if breakout_direction == "LONG":
        structure_sl = min(lookback["low"].min(), retest_entry) - 0.20 * current_atr
        atr_sl = retest_entry - 1.00 * current_atr
        stop_loss = min(structure_sl, atr_sl)
        target = float(lookback["high"].max())  # simple swing-high proxy for "next resistance"
        if target <= retest_entry:
            target = retest_entry + 2 * (retest_entry - stop_loss)  # fallback: 2R
    else:
        structure_sl = max(lookback["high"].max(), retest_entry) + 0.20 * current_atr
        atr_sl = retest_entry + 1.00 * current_atr
        stop_loss = max(structure_sl, atr_sl)
        target = float(lookback["low"].min())
        if target >= retest_entry:
            target = retest_entry - 2 * (stop_loss - retest_entry)

    result.update({
        "state": "READY_TO_ENTER", "direction": breakout_direction,
        "entry_price": retest_entry, "stop_loss": float(stop_loss), "target": float(target),
        "detail": f"Valid {breakout_direction} retest completed at {retest_entry:.2f}, and price hasn't moved "
                  f"too far past it yet ({chase_distance:.2f} ATR). This is the setup type designed to avoid "
                  f"the 'entered right as it got exhausted' problem.",
    })
    return result


def position_size_for_setup(capital: float, entry: float, stop_loss: float, risk_percent: float = 0.5) -> dict:
    """Risk-based position sizing: risk a fixed % of capital per trade,
    rather than a fixed rupee-per-share formula. Returns quantity and the
    real risk-per-share/total-risk amounts."""
    risk_per_share = abs(entry - stop_loss)
    if risk_per_share <= 0:
        return {"quantity": 0, "risk_per_share": 0, "max_risk": 0}
    max_risk = capital * (risk_percent / 100)
    quantity = int(max_risk // risk_per_share)
    return {"quantity": quantity, "risk_per_share": risk_per_share, "max_risk": max_risk}
