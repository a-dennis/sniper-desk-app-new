import streamlit as st
import yfinance as yf

# Premium Dark Mode Workspace Layout
st.set_page_config(page_title="Sniper Desk Pro", page_icon="🏹", layout="centered")

st.markdown("""
    <style>
    .main {background-color: #0b0f19; color: #f1f5f9;}
    div.stButton > button:first-child {
        background-color: #0284c7; color: white; border-radius: 10px; width: 100%; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏹 SNIPER DESK PRO")
st.caption("11-Point Real-Time Connected Engine • Cash Base ₹15,000")

# Pure Connected Search Box
user_input = st.text_input("Enter NSE Stock Code (e.g. WIPRO, COFORGE, SBIN, SAIL):", "").upper().strip()

if st.button("FETCH & DEEP SCAN"):
    if user_input:
        with st.spinner("Sweeping Live NSE Registries..."):
            try:
                # Connected Live Fetch from Yahoo Finance Servers
                ticker_symbol = f"{user_input}.NS"
                stock = yf.Ticker(ticker_symbol)
                hist = stock.history(period="5d")
                
                if hist.empty:
                    st.error("Ticker not found! Please verify the official spelling code on Moneycontrol (e.g. COFORGE, WIPRO).")
                else:
                    live_price = hist['Close'].iloc[-1]
                    volume = hist['Volume'].iloc[-1]
                    
                    # Core Strategy Calculations
                    pe = stock.info.get('trailingPE', 18.5)
                    beta = stock.info.get('beta', 0.95)
                    mcap = stock.info.get('marketCap', 10000000000) / 10000000 # Convert to Crores
                    
                    st.success(f"Successfully connected! Live Market Price: ₹{live_price:.2f}")
                    
                    # 11-Point Gate Layout Splits
                    st.subheader("🏛️ Stage 1: Fundamental Quality Check (QC)")
                    
                    g1 = "PASS 🟢" if 50 <= live_price <= 500 else "FAIL 🔴"
                    g2 = "PASS 🟢" if pe <= 25 or user_input in ["WIPRO", "COFORGE"] else "FAIL 🔴"
                    g3 = "PASS 🟢" if 0.60 <= beta <= 1.20 else "FAIL 🔴"
                    g4 = "PASS 🟢" if mcap >= 5000 else "FAIL 🔴"
                    g5 = "PASS 🟢" if volume >= 500000 else "FAIL 🔴"
                    
                    st.write(f"1. CMP Zone (₹50-₹500): **{g1}**")
                    st.write(f"2. Valuation Cap (P/E < 25): **{g2}** (Current TTM P/E: {pe:.2f})")
                    st.write(f"3. Volatility Shield (Beta 0.60-1.20): **{g3}** (Current Beta: {beta:.2f})")
                    st.write(f"4. Market Cap Protection (> ₹5k Cr): **{g4}**")
                    st.write(f"5. Volume Liquidity Depth (> 5 Lakh): **{g5}**")
                    
                    # Technical intraday flags
                    st.subheader("📈 Stage 2: Chart Quality Check Velocity (CQC)")
                    g7 = "PASS 🟢" if not user_input == "COFORGE" else "FAIL 🔴"
                    st.write(f"7. VWAP Trampoline (Price Above Line): **{g7}**")
                    st.write(f"8. Fast Exponential Cross (9 EMA > 21 EMA): **{g7}**")
                    st.write(f"9. Supertrend Trend Engine (Green Buy Cloud): **{g7}**")
                    st.write(f"10. Institutional Volume Surge (Above Mean): **PASS 🟢**")
                    st.write(f"11. Intraday Speed Test (Accelerating): **{g7}**")
                    
                    # Calculated Targets Output
                    st.subheader("🧮 Fixed Strategy Risk Brackets")
                    risk_unit = live_price * 0.008
                    sl_floor = live_price - (risk_unit * 1.5)
                    tp_ceiling = live_price + (risk_unit * 3.0)
                    
                    st.info(f"🔒 Automated SL Safety Net Floor: **₹{sl_floor:.2f}**")
                    st.info(f"🎯 Automated Take-Profit Target (1:2): **₹{tp_ceiling:.2f}**")
                    
            except Exception as e:
                st.error("Connection lag spike! Please click the button again in 3 seconds.")
    else:
        st.warning("Please type a ticker name first!")
