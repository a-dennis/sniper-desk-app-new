"""
backtest.py
-----------
Standalone historical backtest for the scanner's 5-signal technical score
(VWAP, EMA 9/21 cross, Supertrend, volume surge, momentum).

WHAT IT DOES
For each symbol you give it, pulls the last several days of real 1-minute
candles from Yahoo Finance, replays them bar-by-bar, computes the same
5-signal technical score used live in app.py at EVERY historical bar (using
only data available up to that point -- no lookahead bias), then checks
what the price actually did over the next N minutes. It aggregates results
by score bucket (0-3 / 4 / 5) so you can see whether higher scores actually
preceded better forward returns, historically, on these specific stocks.

WHAT IT DOES NOT DO
- It does not simulate real trading costs, slippage, or order execution.
- Yahoo's free 1-minute data only goes back about 7-8 days, so this is a
  short-window sanity check, not a rigorous multi-month backtest.
- Past performance says nothing certain about future performance. Treat the
  output as one data point to inform your judgement, not a verdict.

USAGE
    pip install yfinance pandas --break-system-packages
    python backtest.py RELIANCE TCS INFY HDFCBANK SBIN

If you don't pass any symbols, it defaults to a small liquid basket.
"""

from __future__ import annotations

import sys

import pandas as pd
import yfinance as yf

DEFAULT_SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "TATASTEEL"]
LOOKAHEAD_MINUTES = [15, 30, 60]
MIN_WARMUP_BARS = 21  # matches the EMA-21 / volume-surge-20 requirements in indicators.py


def vwap_pass(day_df: pd.DataFrame, i: int) -> bool:
    window = day_df.iloc[:i + 1]
    if window.empty:
        return False
    typical = (window["High"] + window["Low"] + window["Close"]) / 3
    vwap = (typical * window["Volume"]).sum() / max(window["Volume"].sum(), 1)
    return day_df["Close"].iloc[i] >= vwap


def ema_cross_pass(day_df: pd.DataFrame, i: int) -> bool:
    if i < MIN_WARMUP_BARS:
        return False
    window = day_df["Close"].iloc[:i + 1]
    ema9 = window.ewm(span=9, adjust=False).mean().iloc[-1]
    ema21 = window.ewm(span=21, adjust=False).mean().iloc[-1]
    return ema9 > ema21


def supertrend_pass(day_df: pd.DataFrame, i: int, period: int = 10, multiplier: float = 3.0) -> bool:
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


def volume_surge_pass(day_df: pd.DataFrame, i: int) -> bool:
    if i < MIN_WARMUP_BARS:
        return False
    last_vol = day_df["Volume"].iloc[i]
    avg_prev20 = day_df["Volume"].iloc[max(0, i - 20):i].mean()
    if avg_prev20 <= 0:
        return False
    return (last_vol / avg_prev20) >= 2.0


def momentum_pass(day_df: pd.DataFrame, i: int) -> bool:
    if i < 6:
        return False
    now_close = day_df["Close"].iloc[i]
    then_close = day_df["Close"].iloc[i - 5]
    if then_close <= 0:
        return False
    return now_close > then_close


def technical_score_at(day_df: pd.DataFrame, i: int) -> int:
    checks = [vwap_pass, ema_cross_pass, supertrend_pass, volume_surge_pass, momentum_pass]
    return sum(1 for check in checks if check(day_df, i))


def backtest_symbol(symbol: str) -> list[dict]:
    results = []
    try:
        df = yf.Ticker(f"{symbol}.NS").history(period="7d", interval="1m")
    except Exception as e:
        print(f"  [{symbol}] could not fetch data: {e}")
        return results
    if df.empty:
        print(f"  [{symbol}] no data returned")
        return results

    df["date"] = df.index.date
    for date, day_df in df.groupby("date"):
        day_df = day_df.reset_index(drop=True)
        n = len(day_df)
        if n < MIN_WARMUP_BARS + max(LOOKAHEAD_MINUTES) + 1:
            continue  # not enough bars this day for warmup + all lookahead horizons
        for i in range(MIN_WARMUP_BARS, n - max(LOOKAHEAD_MINUTES)):
            score = technical_score_at(day_df, i)
            entry_price = day_df["Close"].iloc[i]
            row = {"symbol": symbol, "date": str(date), "bar": i, "score": score, "entry_price": entry_price}
            for mins in LOOKAHEAD_MINUTES:
                future_price = day_df["Close"].iloc[i + mins]
                row[f"return_{mins}m_pct"] = (future_price - entry_price) / entry_price * 100
            results.append(row)
    return results


def summarize(results: list[dict]) -> None:
    if not results:
        print("No results to summarize -- check your symbols/data.")
        return
    df = pd.DataFrame(results)

    def bucket(score):
        if score == 5:
            return "5/5"
        if score == 4:
            return "4/5"
        return "0-3/5"

    df["bucket"] = df["score"].apply(bucket)

    print("\n" + "=" * 70)
    print("BACKTEST SUMMARY -- historical technical score vs forward returns")
    print("=" * 70)
    for mins in LOOKAHEAD_MINUTES:
        col = f"return_{mins}m_pct"
        print(f"\n--- Forward {mins} minutes ---")
        summary = df.groupby("bucket")[col].agg(
            count="count", win_rate=lambda x: (x > 0).mean() * 100,
            avg_return="mean", median_return="median",
        ).reindex(["0-3/5", "4/5", "5/5"])
        print(summary.round(2).to_string())

    print("\nNote: 'count' under 30 or so per bucket means treat that row's stats as noisy, not conclusive.")
    df.to_csv("backtest_results_raw.csv", index=False)
    print("\nFull per-bar results saved to backtest_results_raw.csv for your own inspection.")


if __name__ == "__main__":
    symbols = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_SYMBOLS
    print(f"Backtesting {len(symbols)} symbol(s) over the last ~7 days of 1-minute data: {', '.join(symbols)}")
    all_results = []
    for sym in symbols:
        print(f"Processing {sym}...")
        all_results.extend(backtest_symbol(sym))
    summarize(all_results)
