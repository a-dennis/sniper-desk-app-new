"""
news.py
-------
Pulls real financial news headlines via Google News' public RSS feed --
no API key or signup needed. Returns headline + source + link only (never
full article text), so this is safe to display directly: it's exactly what
a news aggregator or RSS reader does.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import requests
import streamlit as st


POSITIVE_WORDS = [
    "surge", "surges", "rally", "rallies", "jump", "jumps", "soar", "soars", "gain", "gains",
    "profit", "profits", "beat", "beats", "upgrade", "upgraded", "record high", "outperform",
    "buy rating", "bullish", "growth", "strong", "rises", "rise", "up ", "positive", "boost",
    "expansion", "wins", "win", "recovery", "rebound",
]
NEGATIVE_WORDS = [
    "fall", "falls", "falling", "drop", "drops", "plunge", "plunges", "slump", "slumps", "loss",
    "losses", "downgrade", "downgraded", "sell rating", "bearish", "weak", "decline", "declines",
    "crash", "crashes", "probe", "fraud", "scam", "lawsuit", "penalty", "fine", "layoff", "layoffs",
    "cut", "cuts", "miss", "misses", "concern", "concerns", "warning", "slowdown",
]


def classify_sentiment(title: str) -> str:
    t = title.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in t)
    neg = sum(1 for w in NEGATIVE_WORDS if w in t)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def aggregate_sentiment(items: list[dict]) -> dict:
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for n in items:
        counts[classify_sentiment(n["title"])] += 1
    if counts["positive"] > counts["negative"]:
        overall = "Mostly Positive"
    elif counts["negative"] > counts["positive"]:
        overall = "Mostly Negative"
    else:
        overall = "Mixed / Neutral"
    return {"overall": overall, **counts}


@st.cache_data(ttl=15 * 60, show_spinner=False)
def fetch_news(query: str, max_items: int = 5) -> list[dict]:
    """Returns [{"title":..., "source":..., "link":..., "published":...}, ...]"""
    url = "https://news.google.com/rss/search"
    params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title", default="")
            link = item.findtext("link", default="")
            pub_date = item.findtext("pubDate", default="")
            source_el = item.find("source")
            source = source_el.text if source_el is not None else ""
            items.append({"title": title, "source": source, "link": link, "published": pub_date})
        return items
    except Exception:
        return []
