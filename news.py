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
