"""
trade_journal.py
-----------------
A simple trade journal: log COMPLETED trades (entry, exit, P&L, notes) so
you can review your own track record over time. Different from
portfolio.py, which tracks CURRENT open holdings -- this is a historical
log of trades you've already closed out.

Same persistence caveat as portfolio.py/signal_logger.py: stored as a CSV
in the app's working folder, survives normal use but not guaranteed across
a Streamlit Cloud container restart. Use the download button to keep your
own backup.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

JOURNAL_FILE = "trade_journal.csv"
COLUMNS = ["date", "symbol", "direction", "entry_price", "exit_price", "quantity", "pnl", "pnl_pct", "notes"]


def load_journal() -> pd.DataFrame:
    if os.path.exists(JOURNAL_FILE):
        try:
            return pd.read_csv(JOURNAL_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=COLUMNS)


def save_journal(df: pd.DataFrame) -> None:
    df.to_csv(JOURNAL_FILE, index=False)


def render_trade_journal() -> None:
    st.markdown("#### 📓 Trade Journal")
    st.caption("Log trades after you close them out -- builds your own real track record over time.")
    df = load_journal()

    with st.form("add_trade_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        symbol = c1.text_input("Symbol").strip().upper()
        direction = c2.selectbox("Direction", ["LONG", "SHORT"])
        qty = c3.number_input("Quantity", min_value=1, step=1, value=1)
        c4, c5, c6 = st.columns(3)
        entry_price = c4.number_input("Entry Price (Rs)", min_value=0.01, step=0.05, value=100.0)
        exit_price = c5.number_input("Exit Price (Rs)", min_value=0.01, step=0.05, value=100.0)
        date = c6.date_input("Trade Date")
        notes = st.text_area("Notes (what worked, what didn't, lessons)", height=80)
        submitted = st.form_submit_button("Add Trade")
        if submitted and symbol:
            if direction == "LONG":
                pnl = (exit_price - entry_price) * qty
            else:
                pnl = (entry_price - exit_price) * qty
            pnl_pct = (pnl / (entry_price * qty) * 100) if entry_price and qty else 0
            new_row = pd.DataFrame([{
                "date": str(date), "symbol": symbol, "direction": direction,
                "entry_price": entry_price, "exit_price": exit_price, "quantity": qty,
                "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2), "notes": notes,
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_journal(df)
            st.success(f"Logged {direction} {symbol}: {'profit' if pnl >= 0 else 'loss'} of Rs {abs(pnl):.2f}")
            st.rerun()

    if df.empty:
        st.caption("No trades logged yet.")
        return

    total_trades = len(df)
    wins = (df["pnl"] > 0).sum()
    losses = (df["pnl"] <= 0).sum()
    win_rate = (wins / total_trades * 100) if total_trades else 0
    total_pnl = df["pnl"].sum()
    avg_pnl = df["pnl"].mean()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Trades", total_trades)
    m2.metric("Win Rate", f"{win_rate:.1f}%", f"{wins}W / {losses}L")
    m3.metric("Total P&L", f"Rs {total_pnl:+,.2f}")
    m4.metric("Avg P&L / Trade", f"Rs {avg_pnl:+,.2f}")

    display_df = df.copy()
    display_df["pnl"] = display_df["pnl"].apply(lambda x: f"Rs {x:+,.2f}")
    display_df["pnl_pct"] = display_df["pnl_pct"].apply(lambda x: f"{x:+.2f}%")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download trade_journal.csv (backup)", csv_bytes, file_name="trade_journal.csv", mime="text/csv")
