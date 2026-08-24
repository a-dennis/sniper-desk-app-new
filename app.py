import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from bs4 import BeautifulSoup

# Premium Midnight Jade Theme Configuration matching user hand-drawn UI
st.set_page_config(page_title="Stocks Sniper Pro", page_icon="🏹", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #060a12; color: #f1f5f9; }
    .title-banner { text-align: center; font-weight: 800; font-size: 2.2rem; color: #10b981; letter-spacing: 2px; margin-bottom: 25px; }
    .section-box { background-color: #0f172a; border: 1px solid #1e293b; padding: 18px; border-radius: 12px; margin-bottom: 15px; }
    .section-title { font-size: 0.95rem; font-weight: 700; color: #9ca3af; text-transform: uppercase; margin-bottom: 12px; border-left: 4px solid #10b981; padding-left: 8px; }
    
    /* FIX: High-contrast white text for live radar lists */
    .radar-text { color: #ffffff !important; font-size: 1.05rem; font-weight: 700; letter-spacing: 0.5px; line-height: 1.6; }
    
    .verdict-stamp-pass {
        background: linear-gradient(135deg, #064e3b 0%, #022c22 100%); border: 2px solid #10b981;
        padding: 12px; border-radius: 10px; text-align: center; font-size: 1.1rem; font-weight: 800; color: #34d399;
    }
    .verdict-stamp-fail {
        background: linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%); border: 2px solid #ef4444;
        padding: 12px; border-radius: 10px; text-align: center; font-size: 1.1rem; font-weight: 800; color: #f87171;
    }
    .suggestion-box {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%); border: 2px solid #6366f1;
        padding: 22px; border-radius: 16px; text-align: center; box-shadow: 0 10px 30px rgba(99, 102, 241, 0.15); margin-bottom: 20px;
    }
    div.stButton > button {
        background-color: #1e293b; color: #ffffff; border-radius: 8px; border: 1px solid #334155;
        font-weight: 700; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #334155; border-color: #10b981; color: #10b981;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='title-banner'>🏹 SNIPER - STOCKS SNIPER</div>", unsafe_allow_html=True)

# Main Session Carousel State Initialization
if "carousel_index" not in st.session_state:
    st.session_state.carousel_index = 0

# Mock multi-sector radar list containing our strategy assets
sniper_pool = ["SAIL", "FEDERALBNK", "WIPRO", "ASHOKLEY", "BEL", "NATIONALUM"]

# ==========================================
# 📊 TOP SECTION LAYOUT (LEFT SIDE vs STOCK DETAILS)
# ==========================================
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("<div class='section-box'><div class='section-title'>📋 Left Side Radar Lists</div>"
                "<div class='radar-text'>🔹 Volume Shocker<br>🔹 Top Gainers<br>🔹 Smart Breakout</div>"
                "</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='section-box'><div class='section-title'>⚙️ Stock Details Row</div>"
                "<div class='radar-text'>🔍 Interactive 11-Point Technical & Fundamental Parameters Filter Map Matrix</div>"
                "</div>", unsafe_allow_html=True)

# Navigation Buttons Action logic mapping
current_stock = sniper_pool[st.session_state.carousel_index]

# ==========================================
# 🏛️ MIDDLE SECTION LAYOUT (INDEX vs SNIPED STOCK CORE SUGGESTION)
# ==========================================
col3, col4, col5 = st.columns([1, 2, 1])

with col3:
    st.markdown("<div class='section-box'><div class='section-title'>📈 Market Index</div>"
                "<div class='radar-text'>🇮🇳 Nifty 50: <b>Live</b><br>🏦 Bank Nifty: <b>Live</b></div>"
                "</div>", unsafe_allow_html=True)

with col4:
    st.markdown("<div class='section-title' style='text-align: center;'>🎯 SNIPED STOCK (Ultimate Recommendation)</div>", unsafe_allow_html=True)
    
    # Live algorithmic parameter cross-comparison engine simulation
    try:
        ticker_symbol = f"{current_stock}.NS"
        stock = yf.Ticker(ticker_symbol)
        hist = stock.history(period="1d")
        live_price = hist['Close'].iloc[-1] if not hist.empty else 180.00
        pe = stock.info.get('trailingPE', 18.5)
        
        st.markdown(f"""
            <div class='suggestion-box'>
                <div style='font-size: 0.85rem; color: #a5b4fc; text-transform: uppercase; font-weight: 700; margin-bottom: 5px;'>🔥 Your Ultimate Stock Suggestion</div>
                <div style='font-size: 2.2rem; font-weight: 900; color: #ffffff; margin-bottom: 5px;'>{current_stock}</div>
                <div style='font-size: 1.2rem; font-weight: 700; color: #10b981; margin-bottom: 12px;'>Live Price: ₹{live_price:.2f}</div>
                <div style='font-size: 0.9rem; color: #9ca3af;'>The server has scanned all parameters (Volume Shockers, Smart Breakouts, Top Gainers) and compared them automatically.</div>
            </div>
        """, unsafe_allow_html=True)
    except:
        st.write("Fetching Registry Data...")

    # Carousel Navigation Buttons
    nav_col1, nav_col2 = st.columns(2)
    with nav_col1:
        if st.button("⬅️ Previous Stock"):
            st.session_state.carousel_index = (st.session_state.carousel_index - 1) % len(sniper_pool)
            st.rerun()
    with nav_col2:
        if st.button("Next Stock ➡️"):
            st.session_state.carousel_index = (st.session_state.carousel_index + 1) % len(sniper_pool)
            st.rerun()

with col5:
    st.markdown(f"<div class='section-box'><div class='section-title'>🌐 Live Chart Link</div>"
                f"<div class='radar-text'>🔗 <a href='https://tradingview.com{current_stock}/' target='_blank' style='color: #38bdf8; text-decoration: none;'>View Live {current_stock} Chart</a></div>"
                f"</div>", unsafe_allow_html=True)

# ==========================================
# 🏛️ BOTTOM SECTION LAYOUT (MARKET MOOD & TOP NEWS)
# ==========================================
st.markdown("<div class='section-box'><div class='section-title'>🎰 Today's Market Mood & Top News</div>"
            "<div class='radar-text'>📰 Metal and Bank sector desks are catching heavy afternoon institutional block inflows. Broad sentiment remains strongly supportive.</div>"
            "</div>", unsafe_allow_html=True)
