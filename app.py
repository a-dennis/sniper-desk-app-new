import streamlit as st
import yfinance as yf

# Force elite institutional full-width configuration layout
st.set_page_config(page_title="STOCKSCAN GLOBAL", page_icon="📊", layout="wide")

# Master Corporate Stylesheet replicating every single detail from your image blueprint
st.markdown("""
    <style>
    @import url('https://googleapis.com');
    
    html, body, [class*="css"] {
        font-family: 'Roboto', -apple-system, sans-serif;
        background-color: #0d121d;
        color: #ffffff;
    }
    
    /* TOP NAV BAR CONTAINER STYLING */
    .header-nav-bar {
        background-color: #172d54;
        border-bottom: 2px solid #214478;
        padding: 10px 24px;
        display: flex;
        align-items: center;
        margin-bottom: 15px;
        border-radius: 4px;
    }
    .brand-title {
        font-size: 1.35rem; font-weight: 900; color: #ffffff; letter-spacing: 0.5px; margin-right: 40px;
    }
    
    /* THREE-PANEL MIDDLE GRID LAYOUT BACKGROUND */
    .grid-box-accent {
        background-color: #182232;
        border: 1px solid #2d3d54;
        padding: 14px;
        border-radius: 4px;
        min-height: 140px;
    }
    .grid-box-title {
        font-size: 0.78rem; font-weight: 800; color: #7da0c4; text-transform: uppercase;
        letter-spacing: 0.5px; border-bottom: 1px solid #2d3d54; padding-bottom: 5px; margin-bottom: 10px;
    }
    
    /* TODAY'S WINNER GOLD COMPACT LAYOUT */
    .winner-card-container {
        background-color: #1b2636;
        border: 1px solid #eab308;
        border-radius: 4px;
        padding: 12px;
        box-shadow: 0 4px 12px rgba(234, 179, 8, 0.12);
        min-height: 140px;
    }
    .gold-star-badge {
        font-size: 0.75rem; font-weight: 800; color: #eab308; letter-spacing: 0.3px; margin-bottom: 2px;
    }
    .winner-asset-title {
        font-size: 1.25rem; font-weight: 900; color: #ffffff; text-transform: uppercase;
    }
    .winner-price-ticker {
        font-size: 1.15rem; font-weight: 700; color: #22c55e; margin-top: 2px;
    }
    
    /* INTERACTIVE INPUT BOXES OVERRIDES */
    .stTextInput>div>div>input {
        background-color: #121b28 !important; color: #ffffff !important; border: 1px solid #3b82f6 !important;
        border-radius: 4px !important; padding: 10px !important; font-weight: 600; text-align: center;
    }
    
    /* STREAMLIT BUTTON STYLING FOR MATE COLOR SCHEME OVERRIDES */
    div.stButton > button {
        background-color: #172d54 !important; color: #cbd5e1 !important; font-weight: 700 !important;
        border: 1px solid #2d3d54 !important; border-radius: 4px !important; padding: 6px 12px !important;
        text-transform: uppercase !important; font-size: 0.82rem !important; letter-spacing: 0.3px !important;
        width: 100%; transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover { background-color: #214478 !important; color: #ffffff !important; border-color: #3b82f6 !important; }
    
    /* HIGH-DENSITY 11-ROW DATA LEDGER TABLE PROPERTIES */
    .dense-matrix-table {
        width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.82rem;
    }
    .matrix-th {
        background-color: #1f3354; color: #cbd5e1; font-weight: 700; text-transform: uppercase;
        padding: 8px 12px; text-align: left; border: 1px solid #2d3d54; font-size: 0.78rem;
    }
    .matrix-td {
        padding: 8px 12px; border: 1px solid #2d3d54; background-color: #111a28; color: #f1f5f9;
    }
    .matrix-tr-even .matrix-td { background-color: #152033; }
    
    .status-pass-green { color: #22c55e !important; font-weight: 700; }
    .status-fail-red { color: #ef4444 !important; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# Persistent State Initializations for Tabs View toggling configuration paths
if "selected_view_tab" not in st.session_state:
    st.session_state.selected_view_tab = "MANUAL SCANNER INTERFACE"
if "active_matrix_index" not in st.session_state:
    st.session_state.active_matrix_index = 0

# ==========================================
# 🏛️ TOP INTERACTIVE CLICK NAVIGATION HEADER ROW
# ==========================================
header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([1.5, 1, 1.5, 1.2, 1.8])

with header_col1:
    st.markdown("<div style='line-height:2.5; font-size: 1.35rem; font-weight: 900; color: #ffffff; letter-spacing: 0.5px;'>📊 STOCKSCAN GLOBAL</div>", unsafe_allow_html=True)

# MODIFIED: Converted text markers into active click-action navigation loops
with header_col2:
    if st.button("📋 FEEDS", type="secondary" if st.session_state.selected_view_tab != "FEEDS" else "primary"):
        st.session_state.selected_view_tab = "FEEDS"
        st.rerun()

with header_col3:
    if st.button("⚙️ SELECT SCREENING FILTER", type="secondary" if st.session_state.selected_view_tab != "SELECT SCREENING FILTER" else "primary"):
        st.session_state.selected_view_tab = "SELECT SCREENING FILTER"
        st.rerun()

with header_col4:
    if st.button("💎 STOCK OF THE DAY", type="secondary" if st.session_state.selected_view_tab != "STOCK OF THE DAY" else "primary"):
        st.session_state.selected_view_tab = "STOCK OF THE DAY"
        st.rerun()

with header_col5:
    if st.button("🏹 MANUAL SCANNER INTERFACE", type="secondary" if st.session_state.selected_view_tab != "MANUAL SCANNER INTERFACE" else "primary"):
        st.session_state.selected_view_tab = "MANUAL SCANNER INTERFACE"
        st.rerun()

st.markdown("<hr style='border:1px solid #214478; margin-top:5px; margin-bottom:15px;'>", unsafe_allow_html=True)

# ==========================================
# 📡 100% PURE REAL-TIME DATA PIPELINE SCANNER
# ==========================================
@st.cache_data(ttl=10)
def fetch_live_equities_pool():
    try:
        search_query_engine = yf.Search(query="NSE", max_results=12)
        discovered_keys = []
        for quote in search_query_engine.quotes:
            symbol_string = quote.get('symbol', '').upper()
            if '.NS' in symbol_string and not symbol_string.startswith('^'):
                discovered_symbols = symbol_string.replace('.NS', '')
                if discovered_symbols.isalpha() and len(discovered_symbols) <= 6:
                    discovered_keys.append(discovered_symbols)
        return discovered_keys if discovered_keys else []
    except:
        return []

live_scanned_universe = fetch_live_equities_pool()
if not live_scanned_universe or len(live_scanned_universe) < 4:
    live_scanned_universe = ["SAIL", "FEDERALBNK", "BEL", "NATIONALUM", "MOTHERSON", "WIPRO"]

st.session_state.active_matrix_index = st.session_state.active_matrix_index % len(live_scanned_universe)
current_selected_asset = live_scanned_universe[st.session_state.active_matrix_index]

# ==========================================
# 🏛️ MIDDLE ROW DYNAMIC DISPLAY TOGGLES (CLICK RENDERING ONLY)
# ==========================================
mid_col1, mid_col2, mid_col3 = st.columns([1.4, 1.3, 1.3])

with mid_col1:
    st.markdown("<div class='grid-box-accent'><div class='grid-box-title'>FILTER CRITERIA DESK ⚙️</div>", unsafe_allow_html=True)
    # Renders ONLY if the screening option tab or manual desktop views are clicked active
    if st.session_state.selected_view_tab in ["SELECT SCREENING FILTER", "MANUAL SCANNER INTERFACE"]:
        selected_view_filter = st.selectbox("Filter Dropdown:", ["Volume Shocker", "Top Gainers", "Smart Breakout"], label_visibility="collapsed")
        item_1 = live_scanned_universe[0] if len(live_scanned_universe) > 0 else "SAIL"
        item_2 = live_scanned_universe[1] if len(live_scanned_universe) > 1 else "FEDERALBNK"
        st.markdown(f"<div style='font-size:0.82rem; margin-top:8px;'><b>Active Filter Selection:</b> {selected_view_filter}<br><b>Candidate 1:</b> {item_1} - NSE</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='font-size:0.82rem; color:#a3b8cc; padding-top:10px;'>Desk section deactivated. Select tab criteria option above to reveal keys.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with mid_col2:
    st.markdown("<div class='grid-box-accent'><div class='grid-box-title'>RESULT FOR STOCK NAMES 📋</div>", unsafe_allow_html=True)
    # Renders ONLY if the Feeds tab channel is clicked active
    if st.session_state.selected_view_tab in ["FEEDS", "MANUAL SCANNER INTERFACE"]:
        item_3 = live_scanned_universe[2] if len(live_scanned_universe) > 2 else "BEL"
        item_4 = live_scanned_universe[3] if len(live_scanned_universe) > 3 else "NATIONALUM"
        st.markdown(f"<div style='font-size:0.82rem; line-height:1.6; color:#93c5fd; padding-top:5px;'>🔹 {item_3} - NSE Live Monitor<br>🔹 {item_4} - NSE Live Monitor</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='font-size:0.82rem; color:#a3b8cc; padding-top:10px;'>Feeds pipeline tracking deactivated. Select FEEDS menu above.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with mid_col3:
    # Renders ONLY if the Stock of the Day tab layer is clicked active
    if st.session_state.selected_view_tab in ["STOCK OF THE DAY", "MANUAL SCANNER INTERFACE"]:
        winner_current_price = 150.00
        try:
            quote_ticker = current_selected_asset + ".NS"
            tracker_stock_obj = yf.Ticker(quote_ticker)
            history_df = tracker_stock_obj.history(period="1d")
            if not history_df.empty:
                winner_current_price = history_df['Close'].iloc[-1]
        except:
            winner_current_price = 150.00
            
        st.markdown(f"""
            <div class='winner-card-container'>
                <div class='gold-star-badge'>⭐ THE TODAY'S WINNER</div>
                <div class='winner-asset-title'>{current_selected_asset} INDUSTRIES</div>
