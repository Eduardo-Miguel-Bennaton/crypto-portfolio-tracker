import streamlit as st
import json
import os
import plotly.graph_objects as go

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
if "delete_button_pressed" not in st.session_state:
    st.session_state.delete_button_pressed = False

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
        # Clear selected rows after adding, to prevent unexpected behavior
        st.session_state.selected_rows = set()
        st.rerun() # Rerun to update the table and checkboxes

st.divider()
st.subheader("Your Current Holdings")

# Calculate data for display and chart
holdings_data = []
total_value = 0.0

for symbol, amount in st.session_state.portfolio.items():
    # Simulate price
    price = 100000 + hash(symbol) % 10000
    value = price * amount
    total_value += value
    holdings_data.append({"symbol": symbol, "amount": amount, "price": price, "value": value})

# Only show delete if something selected
if st.session_state.selected_rows:
    if st.button("Delete Selected", type="primary"):
        st.session_state.delete_button_pressed = True
        symbols_to_delete = list(st.session_state.selected_rows)
        for symbol in symbols_to_delete:
            if symbol in st.session_state.portfolio: # Ensure symbol still exists before deleting
                del st.session_state.portfolio[symbol]
        st.session_state.selected_rows.clear() # Clear selected rows after deletion
        save_portfolio(st.session_state.portfolio)
        st.success("Selected holdings deleted.")
        st.session_state.delete_button_pressed = False # Reset the flag
        st.rerun() # Rerun to update the UI after deletion

# Render table headers
header_cols = st.columns([1, 2, 2, 2, 2])
header_cols[0].write(" ")
header_cols[1].write("**Ticker**")
header_cols[2].write("**Amount**")
header_cols[3].write("**Price**")
header_cols[4].write("**Value**")

for item in holdings_data:
    symbol = item["symbol"]
    amount = item["amount"]
    price = item["price"]
    value = item["value"]

    cols = st.columns([1, 2, 2, 2, 2])

    # --- First column: Checkbox + Edit ---
    with cols[0]:
        row_controls = st.columns([1, 1])
        checkbox_key = f"checkbox_{symbol}"
        
        # Initialize checkbox state based on selected_rows
        initial_checkbox_state = symbol in st.session_state.selected_rows
        
        new_checkbox_state = row_controls[0].checkbox("", value=initial_checkbox_state, key=checkbox_key)
        
        # Update selected_rows based on checkbox state
        if new_checkbox_state:
            st.session_state.selected_rows.add(symbol)
        else:
            st.session_state.selected_rows.discard(symbol)

        if row_controls[1].button("✏️", key=f"edit_button_{symbol}"):
            st.session_state.edit_row = symbol
            st.session_state.edit_original_value = amount
            st.rerun() # Rerun to properly render the edit mode immediately

    # --- Edit Mode ---
    if st.session_state.edit_row == symbol:
        # Use a unique key for number_input within the edit context
        new_amount = cols[2].number_input("Edit amount", value=amount, key=f"edit_input_{symbol}_value", format="%.8f")

        # Ticker, price, value (read-only)
        cols[1].write(symbol)
        cols[3].write(f"${price:,.2f}")
        cols[4].write(f"${price * new_amount:,.2f}")

        # Buttons for Save and Discard
        # Place buttons outside the initial `cols` to avoid layout issues with number_input
        st.write("") # Add some vertical space for clarity
        edit_action_cols = st.columns([1, 1])

        # Check if new_amount has actually changed from the original value to enable save
        if new_amount != st.session_state.edit_original_value:
            if edit_action_cols[0].button("Save", key=f"save_{symbol}_button"):
                st.session_state.portfolio[symbol] = new_amount
                save_portfolio(st.session_state.portfolio)
                st.session_state.edit_row = None
                st.success(f"{symbol} updated.")
                st.rerun() # Rerun to exit edit mode and update table
        else:
            edit_action_cols[0].button("Save", key=f"save_{symbol}_button_disabled", disabled=True) # Disabled button

        if edit_action_cols[1].button("Discard", key=f"discard_{symbol}_button"):
            st.session_state.edit_row = None
            st.rerun() # Rerun to exit edit mode
    else:
        # Normal row
        cols[1].write(symbol)
        cols[2].write(f"{amount:,.8f}")
        cols[3].write(f"${price:,.2f}")
        cols[4].write(f"${value:,.2f}")

st.divider()
st.subheader("Portfolio Summary")
st.write(f"**Total Portfolio Value:** ${total_value:,.2f}")

# 1. Add the pie chart based on the "Current Holdings" (Plotly)
if holdings_data:
    st.subheader("Portfolio Allocation")
    # Filter out holdings with zero value for the pie chart
    non_zero_holdings = [item for item in holdings_data if item["value"] > 0]

    if non_zero_holdings:
        labels = [item["symbol"] for item in non_zero_holdings]
        values = [item["value"] for item in non_zero_holdings]

        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        fig.update_traces(hoverinfo='label+percent', textinfo='value', textfont_size=15,
                          marker=dict(line=dict(color='#000000', width=1)))
        fig.update_layout(title_text="Allocation by Holding Value", title_x=0.5)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No holdings with a value greater than zero to display in the pie chart.")
else:
    st.info("Add some holdings to see your portfolio allocation!")