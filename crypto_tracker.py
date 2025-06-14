import streamlit as st
import json
import os

# File to persist data
DATA_FILE = "portfolio_data.json"

# Load portfolio from file
def load_portfolio():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Save portfolio to file
def save_portfolio(portfolio):
    with open(DATA_FILE, "w") as f:
        json.dump(portfolio, f)

# Initialize session state
if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_portfolio()
if "selected_rows" not in st.session_state:
    st.session_state.selected_rows = set()
if "edit_row" not in st.session_state:
    st.session_state.edit_row = None
if "edit_original_value" not in st.session_state:
    st.session_state.edit_original_value = None

# Add coin form
st.title("Crypto Portfolio Tracker")
st.subheader("Add New Holding")
with st.form("add_coin_form"):
    symbol = st.text_input("Ticker (e.g., BTC)").upper().strip()
    amount = st.number_input("Amount", min_value=0.0, format="%.8f")
    submitted = st.form_submit_button("Add")
    if submitted and symbol:
        st.session_state.portfolio[symbol] = amount
        save_portfolio(st.session_state.portfolio)
        st.success(f"Added {symbol} with amount {amount}")

st.divider()
st.subheader("Your Current Holdings")

# Only show delete if something selected
if st.session_state.selected_rows:
    if st.button("Delete Selected", type="primary"):
        for symbol in list(st.session_state.selected_rows):
            del st.session_state.portfolio[symbol]
            st.session_state.selected_rows.remove(symbol)
        save_portfolio(st.session_state.portfolio)
        st.success("Selected holdings deleted.")

# Render table headers
header_cols = st.columns([1, 2, 2, 2, 2])
header_cols[0].write(" ")
header_cols[1].write("**Ticker**")
header_cols[2].write("**Amount**")
header_cols[3].write("**Price**")
header_cols[4].write("**Value**")

total_value = 0.0

for symbol, amount in st.session_state.portfolio.items():
    # Simulate price
    price = 100000 + hash(symbol) % 10000
    value = price * amount
    total_value += value

    cols = st.columns([1, 2, 2, 2, 2])

    # --- First column: Checkbox + Edit ---
    with cols[0]:
        row = st.columns([1, 1])
        checkbox_key = f"checkbox_{symbol}"
        if checkbox_key not in st.session_state:
            st.session_state[checkbox_key] = False
        new_state = row[0].checkbox("", key=checkbox_key)
        if new_state:
            st.session_state.selected_rows.add(symbol)
        else:
            st.session_state.selected_rows.discard(symbol)

        if row[1].button("✏️", key=f"edit_{symbol}"):
            st.session_state.edit_row = symbol
            st.session_state.edit_original_value = amount

    # --- Edit Mode ---
    if st.session_state.edit_row == symbol:
        new_amount = cols[2].number_input("Edit amount", value=amount, key=f"edit_input_{symbol}", format="%.8f")

        # Ticker, price, value (read-only)
        cols[1].write(symbol)
        cols[3].write(f"${price:,.2f}")
        cols[4].write(f"${price * new_amount:,.2f}")

        action_cols = st.columns([1, 1])
        if new_amount != st.session_state.edit_original_value:
            if action_cols[0].button("Save", key=f"save_{symbol}"):
                st.session_state.portfolio[symbol] = new_amount
                save_portfolio(st.session_state.portfolio)
                st.session_state.edit_row = None
                st.success(f"{symbol} updated.")
        if action_cols[1].button("Discard", key=f"discard_{symbol}"):
            st.session_state.edit_row = None
    else:
        # Normal row
        cols[1].write(symbol)
        cols[2].write(f"{amount:,.8f}")
        cols[3].write(f"${price:,.2f}")
        cols[4].write(f"${value:,.2f}")

st.divider()
st.subheader("Portfolio Summary")
st.write(f"**Total Portfolio Value:** ${total_value:,.2f}")