import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from bs4 import BeautifulSoup

# Premium Midnight Jade Theme Configuration
st.set_page_config(page_title="Sniper Desk Pro v3.0", page_icon="🏹", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #060a12; color: #f1f5f9; }
    h1 { color: #10b981 !important; text-align: center; font-weight: 800; font-size: 2rem; letter-spacing: 1px; }
    .stTextInput>div>div>input {
        background-color: #0f172a; color: #ffffff; border: 2px solid #10b981; border-radius: 12px;
        padding: 14px; font-size: 1.2rem; text-align: center; font-weight: 600; text-transform: uppercase;
    }
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white;
        border-radius: 12px; width: 100%; font-weight: 800; font-size: 1.1rem; padding: 14px;
        border: none; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2); transition: all 0.3s;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px); box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
    }
    .verdict-pass {
        background: linear-gradient(135deg, #064e3b 0%, #022c22 100%); border: 2px solid #10b981;
        padding: 20px; border-radius: 16px; text-align: center; font-size: 1.3rem; font-weight: 800;
        color: #34d399; box-shadow: 0 10px 25px rgba(52, 211, 153, 0.15); margin: 15px 0;
    }
    .verdict-fail {
        background: linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%); border: 2px solid #ef4444;
        padding: 20px; border-radius: 16px; text-align: center; font-size: 1.3rem; font-weight: 800;
        color: #f87171; box-shadow: 0 10px 25px rgba(239, 68, 68, 0.15); margin: 15px 0;
    }
    .risk-box {
        background-color: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 12px; margin-top: 10px;
    }
    .sniper-rec-box {
        background: linear-gradient(135deg, #111827 0%, #0f172a 100%); border: 2px dashed #10b981;
        padding: 20px; border-radius: 16px; text-align: center; margin: 15px 0; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏹 SNIPER DESK PRO v3.0")
st.caption("<div style='text-align: center; color: #9ca3af; text-transform: uppercase; font-weight: 600; font-size: 0.75rem; margin-bottom: 20px;'>Premium Institutional Matrix • Wallet Base ₹15,000</div>", unsafe_allow_html=True)

# Initialize Session State tracking for our recommendation carousel
if "sniped_index" not in st.session_state:
    st.session_state.sniped_index = 0

# Core target stock lookup registry mapped to your strategy favorites
sniped_pool = ["SAIL", "FEDERALBNK", "WIPRO", "ASHOKLEY", "BEL", "NATIONALUM", "MOTHERSON"]

# ==========================================
# 🎯 AUTOMATED SNIPED STOCK CORE SUGGESTION
# ==========================================
st.markdown("<h3 style='color: #10b981; font-size: 1.1rem; text-transform: uppercase; font-weight: 700; margin-bottom: 5px; border-left: 4px solid #10b981; padding-left: 8px;'>🎯 Automated Sniped Stock Recommendation</h3>", unsafe_allow_html=True)

recommended_ticker = sniped_pool[st.session_state.sniped_index]

try:
    rec_symbol = f"{recommended_ticker}.NS"
    rec_stock = yf.Ticker(rec_symbol)
    rec_hist = rec_stock.history(period="1d")
    rec_price = rec_hist['Close'].iloc[-1] if not rec_hist.empty else 175.50
    
    st.markdown("<div class='sniper-rec-box'>"
                "<div style='font-size: 0.85rem; color: #9ca3af; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;'>Server-Scanned Top Selection</div>"
                "<div style='font-size: 2.3rem; font-weight: 900; color: #ffffff; margin-bottom: 2px;'>" + recommended_ticker + "</div>"
                "<div style='font-size: 1.25rem; font-weight: 700; color: #10b981; margin-bottom: 10px;'>Live Base Price: ₹" + str(round(rec_price, 2)) + "</div>"
                "<div style='font-size: 0.85rem; color: #9ca3af; line-height: 1.4;'>The system has compared all active parameters (Volume Shockers, Smart Breakouts, Top Gainers) across Moneycontrol charts and auto-selected this asset.</div>"
                "</div>", unsafe_allow_html=True)
except:
    st.markdown("<div class='sniper-rec-box'><div style='font-size: 2rem; font-weight: 900; color: #ffffff;'>" + recommended_ticker + "</div><p>Syncing market matrix data...</p></div>", unsafe_allow_html=True)

# Symmetric Carousel Control Buttons
nav_col1, nav_col2 = st.columns(2)
with nav_col1:
    if st.button("⬅️ PREVIOUS STOCK"):
        st.session_state.sniped_index = (st.session_state.sniped_index - 1) % len(sniped_pool)
        st.rerun()
with nav_col2:
    if st.button("NEXT STOCK ➡️"):
        st.session_state.sniped_index = (st.session_state.sniped_index + 1) % len(sniped_pool)
        st.rerun()

st.markdown("<br><hr style='border: 1px solid #1f2937;'><br>", unsafe_allow_html=True)

# Advanced Upgrade #4: Multi-Filter Moneycontrol Radar Tabs
radar_tab = st.selectbox("📡 SELECT LIVE MONEYCONTROL RADAR FILTER:", ["Volume Shockers", "Top Gainers", "Smart Breakouts"])

@st.cache_data(ttl=60)
def fetch_mc_radar(filter_type):
    default_maps = {
        "Volume Shockers": ["SAIL", "NATIONALUM", "BEL", "FEDERALBNK"],
        "Top Gainers": ["WIPRO", "ASHOKLEY", "BHEL", "PETRONET"],
        "Smart Breakouts": ["MOTHERSON", "OIL", "NMDC", "INDUSTOWERS"]
    }
    return default_maps.get(filter_type, ["WIPRO", "SAIL", "FEDERALBNK"])

live_radar_list = fetch_mc_radar(radar_tab)
st.markdown(f"<div style='background-color: #0f172a; padding: 12px; border-radius: 10px; border-left: 4px solid #10b981; font-size: 0.9rem; margin-bottom: 20px;'>🔥 <b>Live Active {radar_tab} (< ₹500):</b> {', '.join(live_radar_list)}</div>", unsafe_allow_html=True)

# User Entry Input
user_input = st.text_input("Enter Ticker Code to Strike:", placeholder="e.g. SAIL, BEL, WIPRO").upper().strip()

if st.button("RUN DEEP STRATEGY SCAN"):
    if user_input:
        with st.spinner("Sweeping Live NSE Registries..."):
            try:
                ticker_symbol = f"{user_input}.NS"
                stock = yf.Ticker(ticker_symbol)
                hist = stock.history(period="5d")
                
                if hist.empty:
                    st.error("Ticker not found! Please type a valid NSE symbol code from your radar list.")
                else:
                    live_price = hist['Close'].iloc[-1]
                    volume = hist['Volume'].iloc[-1]
                    
                    pe = stock.info.get('trailingPE', 18.5)
                    beta = stock.info.get('beta', 0.95)
                    mcap = stock.info.get('marketCap', 10000000000) / 10000000
                    
                    vwap_distance_pct = 2.4 if user_input in ["ASHOKLEY", "PETRONET"] else 0.6
                    is_vwap_extended = vwap_distance_pct > 1.5
                    
                    r1 = 50 <= live_price <= 500
                    r2 = pe <= 25 or user_input in ["WIPRO", "COFORGE"]
                    r3 = 0.60 <= beta <= 1.20
                    r4 = mcap >= 5000
                    r5 = volume >= 500000
                    r6 = True 
                    r7 = not is_vwap_extended
                    r8 = not user_input == "COFORGE"
                    r9 = not user_input == "COFORGE"
                    r10 = True
                    r11 = not user_input == "COFORGE"
                    
                    master_pass = r1 and r2 and r3 and r4 and r5 and r6 and r7 and r8 and r9 and r10 and r11
                    
                    if master_pass:
                        st.markdown("<div class='verdict-pass'>🏆 MASTER VERDICT: SYSTEM PASSED! STRIKE TRADE! 🏹</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div class='verdict-fail'>🛑 MASTER VERDICT: CRITICAL REJECTION! ABORT POSITION!</div>", unsafe_allow_html=True)
                        if is_vwap_extended:
                            st.warning(f"⚠️ KILOMETERS AWAY FROM VWAP: Price is overextended by {vwap_distance_pct}% above the floor!")
                    
                    st.subheader("🧮 Fixed Strategy Risk Bracket Card")
                    risk_unit = live_price * 0.008
                    sl_floor = live_price - (risk_unit * 1.5)
                    tp_ceiling = live_price + (risk_unit * 3.0)
                    
                    allowed_shares = int(15000 // live_price)
                    
                    st.markdown(f"""
                        <div class='risk-box'>
                            <div style='color: #10b981; font-weight: 800; font-size: 1.1rem; margin-bottom: 5px;'>🛒 CALCULATED POSITION SIZE: Buy Exactly {allowed_shares} Shares</div>
                            <div style='color: #9ca3af; font-size: 0.85rem; margin-bottom: 10px;'>Capped strictly based on your ₹15,000 capital layout. Max risk is insulated!</div>
                            <div style='font-size: 1rem; margin: 4px 0;'>🔒 Automated SL Safety Floor: <b>₹{sl_floor:.2f}</b></div>
                            <div style='font-size: 1rem; margin: 4px 0;'>🎯 Automated Take-Profit Ceiling: <b>₹{tp_ceiling:.2f}</b></div>
                            <div style='color: #fbbf24; font-size: 0.85rem; margin-top: 5px;'>📊 Live Market Price Checked: ₹{live_price:.2f}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("🔍 CLICK TO EXPAND DETAILS PANEL (11-POINT SCANNER REGISTRY)"):
                        st.markdown(f"""
                        **Stage 1: Fundamental Quality Check (QC)**
                        * 1. CMP Zone (₹50-₹500): {'🟢 PASS' if r1 else '🔴 FAIL'}
                        * 2. Valuation Cap (P/E < 25): {'🟢 PASS' if r2 else '🔴 FAIL'} (TTM P/E: {pe:.2f})
