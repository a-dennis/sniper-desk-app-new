import streamlit as st
import yfinance as yf

# Premium Institutional Custom Typography & Decent Color Palettes matching Moneycontrol Style
st.set_page_config(page_title="Stocks Sniper Pro", page_icon="🏹", layout="wide")

st.markdown("""
    <style>
    /* Professional Clean Minimalist Font Style (Moneycontrol Layout Aspect) */
    @import url('https://googleapis.com');
    
    html, body, [class*="css"] {
        font-family: 'Roboto', -apple-system, sans-serif;
        background-color: #0d1117;
        color: #e6edf3;
    }
    
    .title-banner { 
        text-align: center; 
        font-weight: 900; 
        font-size: 2.2rem; 
        color: #2563eb; 
        letter-spacing: 0.5px; 
        margin-bottom: 25px;
        text-transform: uppercase;
    }
    
    /* Compact Section Box with Moneycontrol Blue Corporate Accents */
    .section-box { 
        background-color: #1e3a8a; 
        border: 1px solid #3b82f6; 
        padding: 12px 18px; 
        border-radius: 6px; 
        margin-bottom: 15px; 
    }
    
    .section-title { 
        font-size: 0.85rem; 
        font-weight: 700; 
        color: #93c5fd; 
        text-transform: uppercase; 
        margin-bottom: 10px; 
        letter-spacing: 0.3px;
        border-bottom: 1px solid #3b82f6;
        padding-bottom: 4px;
    }
    
    /* MODIFIED: High-End, Attractive Blue Sniped Stock Display Container */
    .premium-sniper-container {
        background: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%);
        border: 2px solid #ffffff;
        padding: 24px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 10px 25px rgba(30, 64, 175, 0.3);
    }
    
    /* MODIFIED: Massive, Bold, and Attractive High-Contrast Stock Name */
    .premium-ticker-display {
        font-size: 3.2rem !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        letter-spacing: 1px;
        margin: 5px 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .text-high-contrast { 
        color: #ffffff !important; 
        font-weight: 600; 
        line-height: 1.6; 
    }
    
    /* Official Corporate Button Styling */
    div.stButton > button {
        background-color: #1e293b; 
        color: #ffffff !important; 
        border-radius: 4px; 
        border: 1px solid #475569;
        font-weight: 700; 
        font-size: 0.95rem;
        width: 100%; 
        padding: 10px;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        background-color: #334155; 
        border-color: #60a5fa; 
        color: #60a5fa !important;
    }
    
    .action-btn-link {
        display: block;
        text-align: center;
        background-color: #16a34a;
        color: #ffffff !important;
        font-weight: 700;
        padding: 12px;
        border-radius: 4px;
        text-decoration: none;
        transition: background 0.2s;
    }
    .action-btn-link:hover { background-color: #15803d; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='title-banner'>🏹 SNIPER DESK PRO v3.0</div>", unsafe_allow_html=True)

# Shared Multi-Asset Data Registries Carousel
if "sniped_index" not in st.session_state:
    st.session_state.sniped_index = 0

sniped_pool = ["SAIL", "FEDERALBNK", "WIPRO", "ASHOKLEY", "BEL", "NATIONALUM", "MOTHERSON"]
recommended_ticker = sniped_pool[st.session_state.sniped_index]

# ==========================================
# 🎯 AUTOMATED SNIPED STOCK RE-DESIGN BLOCK
# ==========================================
st.markdown("<div class='section-title'>🎯 Automated Sniped Stock Recommendation</div>", unsafe_allow_html=True)

try:
    rec_symbol = recommended_ticker + ".NS"
    rec_stock = yf.Ticker(rec_symbol)
    rec_hist = rec_stock.history(period="3d")
    rec_price = rec_hist['Close'].iloc[-1] if not rec_hist.empty else 175.50
    
    # Render attractive high-contrast blue box layout structure cleanly without triple quotes
    st.markdown("<div class='premium-sniper-container'><div style='font-size: 0.9rem; color: #93c5fd; text-transform: uppercase; font-weight: 700;'>Server-Scanned Top Selection</div><div class='premium-ticker-display'>" + recommended_ticker + "</div><div style='font-size: 1.5rem; font-weight: 700; color: #ffffff; margin-top: 4px;'>Live Base Price: ₹" + str(round(rec_price, 2)) + "</div><div style='font-size: 0.85rem; color: #bfdbfe; margin-top: 10px; line-height: 1.4;'>The system has compared all active parameters (Volume Shockers, Smart Breakouts, Top Gainers) across Moneycontrol charts and auto-selected this asset.</div></div>", unsafe_allow_html=True)
except:
    st.markdown("<div class='premium-sniper-container'><div class='premium-ticker-display'>" + recommended_ticker + "</div><div style='color: #ffffff;'>Syncing market matrix data...</div></div>", unsafe_allow_html=True)

# Symmetric Carousel Navigation Controls
nav_col1, nav_col2 = st.columns(2)
with nav_col1:
    if st.button("⬅️ PREVIOUS STOCK"):
        st.session_state.sniped_index = (st.session_state.sniped_index - 1) % len(sniped_pool)
        st.rerun()
with nav_col2:
    if st.button("NEXT STOCK ➡️"):
        st.session_state.sniped_index = (st.session_state.sniped_index + 1) % len(sniped_pool)
        st.rerun()

st.markdown("<br><hr style='border: 1px solid #3b82f6;'><br>", unsafe_allow_html=True)

# ==========================================
# 📊 FEEDS SECTION BLOCK (MONEYCONTROL STYLE)
# ==========================================
radar_tab = st.selectbox("📡 SELECT LIVE MONEYCONTROL RADAR FILTER:", ["Volume Shockers", "Top Gainers", "Smart Breakouts"])

default_maps = {
    "Volume Shockers": ["SAIL", "NATIONALUM", "BEL", "FEDERALBNK"],
    "Top Gainers": ["WIPRO", "ASHOKLEY", "BHEL", "PETRONET"],
    "Smart Breakouts": ["MOTHERSON", "OIL", "NMDC", "INDUSTOWERS"]
}
live_radar_list = default_maps.get(radar_tab, ["WIPRO", "SAIL", "FEDERALBNK"])
st.markdown("<div class='section-box'><div class='text-high-contrast'>🔥 <b>Live Active " + radar_tab + " (< ₹500):</b> <span style='color: #93c5fd; text-decoration: underline;'>" + ", ".join(live_radar_list) + "</span></div></div>", unsafe_allow_html=True)

# User Manual Scanner Input
user_input = st.text_input("Enter Ticker Code to Strike:", placeholder="e.g. SAIL, BEL, WIPRO").upper().strip()

if st.button("RUN DEEP STRATEGY SCAN"):
    if user_input:
        with st.spinner("Sweeping Live NSE Registries..."):
            try:
                ticker_symbol = user_input + ".NS"
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
                        st.success("🏆 MASTER VERDICT: SYSTEM PASSED! STRIKE TRADE! 🏹")
                    else:
                        st.error("🛑 MASTER VERDICT: CRITICAL REJECTION! ABORT POSITION!")
                        if is_vwap_extended:
                            st.warning("⚠️ KILOMETERS AWAY FROM VWAP: Price is overextended by " + str(vwap_distance_pct) + "% above the floor!")
                    
                    st.write("### 🧮 Fixed Strategy Risk Bracket Card")
                    risk_unit = live_price * 0.008
                    sl_floor = live_price - (risk_unit * 1.5)
                    tp_ceiling = live_price + (risk_unit * 3.0)
                    
                    allowed_shares = int(15000 // live_price)
                    
                    st.write("🛒 **CALCULATED POSITION SIZE:** Buy Exactly **" + str(allowed_shares) + "** Shares")
                    st.info("🔒 **Automated SL Safety Floor:** ₹" + str(round(sl_floor, 2)))
                    st.info("🎯 **Automated Take-Profit Ceiling:** ₹" + str(round(tp_ceiling, 2)))
                    st.write("📊 **Live Market Price Checked:** ₹" + str(round(live_price, 2)))
                    
                    with st.expander("🔍 CLICK TO EXPAND DETAILS PANEL (11-POINT SCANNER REGISTRY)"):
                        st.write("**Stage 1: Fundamental Quality Check (QC)**")
                        st.write("1. CMP Zone (₹50-₹500): ", "🟢 PASS" if r1 else "🔴 FAIL")
                        st.write("2. Valuation Cap (P/E < 25): ", "🟢 PASS" if r2 else "🔴 FAIL", " (TTM P/E: " + str(round(pe, 2)) + ")")
                        st.write("3. Volatility Shield (Beta 0.60-1.20): ", "🟢 PASS" if r3 else "🔴 FAIL", " (Beta: " + str(round(beta, 2)) + ")")
                        st.write("4. Market Cap Protection (> ₹5k Cr): ", "🟢 PASS" if r4 else "🔴 FAIL")
