"""
ai_insight.py
--------------
An AI reasoning layer using Google's current Gemini API SDK (google-genai,
the official replacement for the now-deprecated google-generativeai
package -- the old package's model names were returning 404s against the
current API, which is exactly why this was rewritten).

Free tier: Flash models, no credit card needed, generous daily limits.

IMPORTANT: this does NOT let Gemini invent its own signals or pull its own
data. It's fed exactly the same real numbers our own scanner already
computed (the 5 technical checks, the live price/volume, and the actual
news headlines we fetched) and asked to reason over THAT -- so the output
is commentary on our real data, not an independent black-box opinion.

Called on-demand (button-triggered) rather than automatically, both to
respect Gemini's free-tier rate limits and because there's no value in
re-running this every 10-second scan cycle.

Requires GEMINI_API_KEY in Streamlit secrets -- get one free, no credit
card, at https://aistudio.google.com/apikey
"""

from __future__ import annotations

import streamlit as st

try:
    from google import genai
except ImportError:
    genai = None

# Tried in order -- Google renames/retires model aliases periodically, so
# we fall through to whichever is actually available for this API key
# rather than hardcoding one name that might not exist yet.
CANDIDATE_MODELS = ["gemini-3.6-flash", "gemini-3.6-flash-001", "gemini-3.6-flash"]


def _call_gemini(prompt: str) -> dict:
    """Shared low-level call used by every AI feature in this file."""
    if genai is None:
        return {"success": False, "error": "google-genai package not installed.", "text": None}
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return {"success": False, "error": "GEMINI_API_KEY not found in Streamlit secrets.", "text": None}

    client = genai.Client(api_key=api_key)
    last_error = None
    for model_name in CANDIDATE_MODELS:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            return {"success": True, "text": response.text.strip(), "error": None, "model_used": model_name}
        except Exception as e:
            last_error = str(e)
            continue
    return {"success": False, "error": f"All model attempts failed. Last error: {last_error}", "text": None}


def _build_prompt(symbol: str, ltp: float, change_pct: float, technical_score: int,
                   rows: list, news_items: list, breakout_setup: dict = None,
                   backtest_result: dict = None) -> str:
    signal_lines = "\n".join(f"- {name}: {verdict.upper()} ({detail})" for name, verdict, detail in rows)
    news_lines = "\n".join(f"- {n['title']} (source: {n['source']})" for n in news_items[:5]) or "No recent headlines found."

    extra_context = ""
    if breakout_setup:
        extra_context += f"\nBREAKOUT SETUP STATE: {breakout_setup.get('state', 'N/A')} -- {breakout_setup.get('detail', '')}\n"
    if backtest_result and backtest_result.get("verdict") in ("PASS", "FAIL"):
        extra_context += (f"\n7-DAY BACKTEST: {backtest_result['verdict']} -- {backtest_result.get('win_rate', 'N/A')}% "
                          f"win rate over {backtest_result.get('sample_count', 'N/A')} historical signals\n")

    return f"""You are analyzing a stock for a retail intraday trader using a rule-based scanner. \
Base your analysis ONLY on the real data below -- do not invent facts, price targets, or information \
not present here.

STOCK: {symbol}
Current Price: Rs {ltp:.2f} ({change_pct:+.2f}% today)
Technical Score: {technical_score}/5
{extra_context}
TECHNICAL SIGNALS (from our own scanner):
{signal_lines}

RECENT NEWS HEADLINES:
{news_lines}

Write a concise analysis in exactly this format, plain text, no markdown symbols:

TECHNICAL READ: (1-2 sentences on what the signals above genuinely suggest, and any tension between them)
NEWS READ: (1-2 sentences on whether the news context supports, contradicts, or is irrelevant to the technical picture)
OVERALL TAKE: (1-2 sentences combining both -- and the breakout/backtest context if provided -- be honest if they conflict)
CONFIDENCE: (one word: Low, Moderate, or High -- based on how well technicals, news, and any breakout/backtest data agree, not on your own market prediction)

This is not financial advice -- do not tell the user to buy or sell, only describe what the data shows."""


@st.cache_data(ttl=15 * 60, show_spinner=False)
def get_ai_insight(symbol: str, ltp: float, change_pct: float, technical_score: int,
                    rows: list, news_items: list, breakout_setup: dict = None,
                    backtest_result: dict = None) -> dict:
    """Returns {"success": bool, "text": str or None, "error": str or None,
    "sections": dict (parsed TECHNICAL READ / NEWS READ / OVERALL TAKE / CONFIDENCE)}."""
    prompt = _build_prompt(symbol, ltp, change_pct, technical_score, rows, news_items, breakout_setup, backtest_result)
    result = _call_gemini(prompt)
    if not result["success"]:
        return {"success": False, "error": result["error"], "sections": {}}

    text = result["text"]
    sections = {}
    for line in text.split("\n"):
        for key in ("TECHNICAL READ", "NEWS READ", "OVERALL TAKE", "CONFIDENCE"):
            if line.upper().startswith(key + ":"):
                sections[key] = line.split(":", 1)[1].strip()
    return {"success": True, "text": text, "error": None, "sections": sections, "model_used": result.get("model_used")}


@st.cache_data(ttl=15 * 60, show_spinner=False)
def get_market_pulse(segment: str, regime: str, top_stocks: list, general_news: list) -> dict:
    """Daily overview: synthesizes the market regime, today's Top 10
    qualifying stocks, and general market news into one summary paragraph
    -- a different, broader use of AI than the single-stock insight above."""
    stock_lines = "\n".join(
        f"- {s['symbol']}: {s['technical_score']}/5, {s['change_pct']:+.2f}% today" for s in top_stocks[:10]
    ) or "No qualifying stocks right now."
    news_lines = "\n".join(f"- {n['title']}" for n in general_news[:5]) or "No recent market headlines found."

    prompt = f"""You are summarizing today's market scan for a retail intraday trader. Base this ONLY on the \
real data below -- do not invent facts or predictions.

SEGMENT: {segment}
MARKET REGIME: {regime}

TOP SCANNED STOCKS TODAY (real scanner output):
{stock_lines}

GENERAL MARKET NEWS:
{news_lines}

Write a 3-4 sentence "Market Pulse" summary in plain text (no markdown): describe what today's scan results \
and regime genuinely suggest about the overall trading environment, and whether the top stocks appear \
concentrated in a particular theme/sector or spread out. Do not give buy/sell advice -- describe the \
conditions only."""

    return _call_gemini(prompt)


@st.cache_data(ttl=30 * 60, show_spinner=False)
def get_journal_coaching(journal_csv_snapshot: str) -> dict:
    """Analyzes the user's OWN logged trade history (from trade_journal.py)
    for real patterns -- e.g. win rate by direction, common notes themes.
    Takes a CSV string snapshot (not a DataFrame) so caching works cleanly."""
    if not journal_csv_snapshot.strip():
        return {"success": False, "error": "No trade journal entries yet.", "text": None}

    prompt = f"""You are a trading coach reviewing a retail trader's own logged trade history. Base this \
analysis ONLY on the real data below -- do not invent trades or numbers not present here.

TRADE JOURNAL (CSV, one row per closed trade):
{journal_csv_snapshot}

Write a concise coaching summary in plain text (no markdown), covering:
1. Overall win rate and total P&L from this data
2. Any real pattern you can see (e.g. performs better on LONG vs SHORT, a symbol that recurs with losses, \
common themes in the notes column if present)
3. One honest, specific observation worth reflecting on -- not generic advice like "always use a stop loss"

Keep it under 150 words. Do not give specific trading advice for future trades -- only reflect on the \
historical pattern shown."""

    return _call_gemini(prompt)
