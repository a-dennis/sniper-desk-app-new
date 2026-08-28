"""
portfolio.py
------------
A simple manual portfolio tracker. You add a row each time you actually buy
a stock (symbol, quantity, buy price, date); the app shows live P&L against
current prices.

STORAGE NOTE: entries are saved to portfolio.csv in the app's working
folder. This survives page refreshes and reruns, but Streamlit Cloud can
occasionally recycle/restart the underlying container (e.g. after a period
of inactivity or a redeploy), which would reset this file. Use the
"Download portfolio.csv" button after adding trades if you want a backup
copy on your own computer -- that's the only fully reliable persistence
here without adding a real database.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

PORTFOLIO_FILE = "portfolio.csv"
COLUMNS = ["symbol", "quantity", "buy_price", "date"]


def load_portfolio() -> pd.DataFrame:
    if os.path.exists(PORTFOLIO_FILE):
        try:
            return pd.read_csv(PORTFOLIO_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=COLUMNS)


def save_portfolio(df: pd.DataFrame) -> None:
    df.to_csv(PORTFOLIO_FILE, index=False)


def render_portfolio_section(get_live_quotes_fn, Instrument) -> None:
    st.markdown("#### My Portfolio")
    df = load_portfolio()

    with st.form("add_holding_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        symbol = c1.text_input("Symbol", placeholder="e.g. RELIANCE").strip().upper()
        qty = c2.number_input("Quantity", min_value=1, step=1, value=1)
        buy_price = c3.number_input("Buy Price (Rs)", min_value=0.01, step=0.05, value=100.0)
        date = c4.date_input("Buy Date")
        submitted = st.form_submit_button("Add to Portfolio")
        if submitted and symbol:
            new_row = pd.DataFrame([{
                "symbol": symbol, "quantity": qty, "buy_price": buy_price, "date": str(date),
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_portfolio(df)
            st.success(f"Added {qty} x {symbol} @ Rs {buy_price:.2f}")
            st.rerun()

    if df.empty:
        st.caption("No holdings added yet -- use the form above after you buy a stock.")
        return

    instruments = [Instrument(trading_symbol=s) for s in df["symbol"].unique()]
    quotes = get_live_quotes_fn(instruments)

    display_rows = []
    total_invested = 0.0
    total_current = 0.0
    for _, row in df.iterrows():
        ltp = quotes.get(row["symbol"], {}).get("ltp", row["buy_price"])
        invested = row["quantity"] * row["buy_price"]
        current_value = row["quantity"] * ltp
        pnl = current_value - invested
        pnl_pct = (pnl / invested * 100) if invested else 0.0
        total_invested += invested
        total_current += current_value
        display_rows.append({
            "Symbol": row["symbol"],
            "Qty": row["quantity"],
            "Buy Price": f"Rs {row['buy_price']:.2f}",
            "LTP": f"Rs {ltp:.2f}",
            "P&L": f"Rs {pnl:+.2f}",
            "P&L %": f"{pnl_pct:+.2f}%",
            "Date": row["date"],
        })

    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0.0
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Invested", f"Rs {total_invested:,.2f}")
    m2.metric("Current Value", f"Rs {total_current:,.2f}")
    m3.metric("Total P&L", f"Rs {total_pnl:+,.2f}", f"{total_pnl_pct:+.2f}%")

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download portfolio.csv (backup)", csv_bytes, file_name="portfolio.csv", mime="text/csv")

    remove_symbol = st.selectbox("Remove a holding", ["-- select --"] + df["symbol"].tolist(), key="remove_holding")
    if remove_symbol != "-- select --":
        if st.button(f"Confirm remove {remove_symbol}"):
            idx = df[df["symbol"] == remove_symbol].index[0]
            df = df.drop(idx).reset_index(drop=True)
            save_portfolio(df)
            st.rerun()
