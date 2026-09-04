"""
sector_data.py
---------------
Curated sector classification for our NSE/F&O stock lists. Yahoo Finance
doesn't reliably expose NSE sector classifications for free, so this is a
manually curated mapping covering the stocks in our shortlists. Not
exhaustive of all ~2,000 NSE stocks -- covers the actively-tracked/F&O
liquid names. Unmapped stocks fall back to "Other".
"""

from __future__ import annotations

SECTOR_MAP = {
    # Banking & Financial Services
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking", "KOTAKBANK": "Banking",
    "AXISBANK": "Banking", "INDUSINDBK": "Banking", "BANKBARODA": "Banking", "PNB": "Banking",
    "CANBK": "Banking", "FEDERALBNK": "Banking", "IDFCFIRSTB": "Banking", "BANDHANBNK": "Banking",
    "UNIONBANK": "Banking", "BAJFINANCE": "Financial Services", "BAJAJFINSV": "Financial Services",
    "HDFCLIFE": "Financial Services", "SBILIFE": "Financial Services", "ICICIPRULI": "Financial Services",
    "ICICIGI": "Financial Services", "SBICARD": "Financial Services", "MUTHOOTFIN": "Financial Services",
    "CHOLAFIN": "Financial Services", "LICHSGFIN": "Financial Services", "MANAPPURAM": "Financial Services",
    "PFC": "Financial Services", "RECLTD": "Financial Services", "MFSL": "Financial Services",
    "SHRIRAMFIN": "Financial Services", "M&MFIN": "Financial Services",
    # IT / Technology
    "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "WIPRO": "IT", "TECHM": "IT", "LTIM": "IT",
    "PERSISTENT": "IT", "COFORGE": "IT", "OFSS": "IT", "NAUKRI": "IT", "LTTS": "IT", "MPHASIS": "IT",
    # Auto
    "MARUTI": "Auto", "TATAMOTORS": "Auto", "M&M": "Auto", "BAJAJ-AUTO": "Auto", "EICHERMOT": "Auto",
    "HEROMOTOCO": "Auto", "TVSMOTOR": "Auto", "ESCORTS": "Auto", "BOSCHLTD": "Auto", "MOTHERSON": "Auto",
    "EXIDEIND": "Auto",
    # Pharma & Healthcare
    "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma", "DIVISLAB": "Pharma",
    "AUROPHARMA": "Pharma", "LUPIN": "Pharma", "TORNTPHARM": "Pharma", "BIOCON": "Pharma",
    "GLENMARK": "Pharma", "APOLLOHOSP": "Pharma", "SYNGENE": "Pharma",
    # Metals & Mining
    "TATASTEEL": "Metals", "JSWSTEEL": "Metals", "HINDALCO": "Metals", "SAIL": "Metals",
    "NATIONALUM": "Metals", "VEDANTA": "Metals", "JINDALSTEL": "Metals", "NMDC": "Metals",
    "HINDCOPPER": "Metals", "COALINDIA": "Metals",
    # Energy & Oil/Gas
    "RELIANCE": "Energy", "ONGC": "Energy", "BPCL": "Energy", "IOC": "Energy", "GAIL": "Energy",
    "HINDPETRO": "Energy", "PETRONET": "Energy", "IGL": "Energy", "ADANIGREEN": "Energy",
    "ADANIENSOL": "Energy", "TATAPOWER": "Energy", "NTPC": "Energy", "POWERGRID": "Energy",
    # FMCG
    "ITC": "FMCG", "HINDUNILVR": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG", "DABUR": "FMCG",
    "MARICO": "FMCG", "GODREJCP": "FMCG", "TATACONSUM": "FMCG", "COLPAL": "FMCG", "UBL": "FMCG",
    "JUBLFOOD": "FMCG",
    # Infra, Cement, Construction
    "LT": "Infrastructure", "ULTRACEMCO": "Cement", "GRASIM": "Cement", "AMBUJACEM": "Cement",
    "SHREECEM": "Cement", "JKCEMENT": "Cement", "DLF": "Realty", "GODREJPROP": "Realty",
    "OBEROIRLTY": "Realty", "LODHA": "Realty", "GMRINFRA": "Infrastructure", "CONCOR": "Infrastructure",
    # Telecom & Media
    "BHARTIARTL": "Telecom", "IDEA": "Telecom", "INDUSTOWER": "Telecom", "SUNTV": "Media",
    "ZEEL": "Media",
    # Defence, Aerospace, Capital Goods
    "BEL": "Defence", "HAL": "Defence", "SIEMENS": "Capital Goods", "ABB": "Capital Goods",
    "CUMMINSIND": "Capital Goods", "HAVELLS": "Capital Goods", "VOLTAS": "Capital Goods",
    "POLYCAB": "Capital Goods", "DIXON": "Capital Goods", "WHIRLPOOL": "Capital Goods",
    # Chemicals & Paints
    "PIDILITIND": "Chemicals", "SRF": "Chemicals", "UPL": "Chemicals", "TATACHEM": "Chemicals",
    "DEEPAKNTR": "Chemicals", "PIIND": "Chemicals", "ASIANPAINT": "Paints", "BERGEPAINT": "Paints",
    # Consumer Discretionary / Retail / Travel
    "TITAN": "Consumer Discretionary", "TRENT": "Consumer Discretionary", "PAGEIND": "Consumer Discretionary",
    "INDIGO": "Aviation", "INDHOTEL": "Hospitality", "IRCTC": "Travel", "ZOMATO": "Internet",
    # Adani Group / Ports / Shipbuilding
    "ADANIENT": "Conglomerate", "ADANIPORTS": "Infrastructure", "MAZDOCK": "Defence",
    "GRSE": "Defence", "BDL": "Defence",
    # Diversified / Other large caps
    "TATAELXSI": "IT", "TATAMTRDVR": "Auto",
}


def get_sector(symbol: str) -> str:
    return SECTOR_MAP.get(symbol, "Other")
