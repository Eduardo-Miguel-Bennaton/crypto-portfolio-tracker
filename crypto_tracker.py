import streamlit as st
import json
import os
import plotly.graph_objects as go
import requests 
import time # <--- NEW: Import time module

# File to persist data
DATA_FILE = "portfolio_data.json"

# --- Streamlit Page Configuration & Styling ---
st.set_page_config(page_title="Crypto Portfolio Tracker", layout="wide")

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display: none;}
header {visibility: hidden;} /* Hides the top header bar */

/* Adjust top padding of the main content block */
div[data-testid="stMainBlockContainer"] {
    padding-top: 1rem; /* Adjust this value as needed, e.g., 0rem for no padding, 1rem for some */
}
</style>
""", unsafe_allow_html=True)

# --- CoinGecko API Functions (from your provided code) ---
@st.cache_data(ttl=3600) # Cache prices for 1 hour
def get_crypto_prices(coin_ids):
    """
    Fetches real-time cryptocurrency prices from the CoinGecko API.
    """
    if not coin_ids:
        return {}

    ids_param = ",".join(coin_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        prices = {}
        for coin_id in coin_ids:
            if coin_id in data and 'usd' in data[coin_id]:
                prices[coin_id] = data[coin_id]['usd']
            else:
                prices[coin_id] = 0.0 # Default to 0 if price not found
        return prices
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching crypto prices: {e}. Please check your internet connection or CoinGecko API status.")
        return {}
    except json.JSONDecodeError:
        st.error("Error decoding JSON response from CoinGecko API. The API might be returning an invalid response.")
        return {}
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching prices: {e}")
        return {}


@st.cache_data(ttl=86400) # Cache coin list for 24 hours
def get_coin_list():
    """
    Fetches the list of supported coins from CoinGecko API to help with ID mapping.
    """
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        coins_data = response.json()
        
        coin_map = {}
        for coin in coins_data:
            coin_map[coin['symbol'].lower()] = coin['id']
            coin_map[coin['name'].lower()] = coin['id']
        return coin_map
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching coin list: {e}. Some coin lookups might fail.")
        return {}
    except json.JSONDecodeError:
        st.error("Error decoding JSON response from CoinGecko API for coin list.")
        return {}
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching coin list: {e}")
        return {}

# Fetch the coin list once
coin_id_map = get_coin_list()

def get_coingecko_id(ticker_or_name):
    """
    Converts a common ticker (e.g., 'BTC') or name ('Bitcoin') to its CoinGecko ID.
    """
    lookup_key = ticker_or_name.lower()
    return coin_id_map.get(lookup_key)

# --- Portfolio Data Persistence ---
def load_portfolio():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                else:
                    st.error("Portfolio file corrupted. Starting with empty portfolio.")
                    return []
        except json.JSONDecodeError:
            st.error("Error loading portfolio data. The file might be corrupted. Starting with an empty portfolio.")
            return []
    return []

def save_portfolio(portfolio):
    with open(DATA_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

# --- Streamlit Session State Initialization ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_portfolio()
if "selected_rows" not in st.session_state:
    st.session_state.selected_rows = set()
if "edit_row" not in st.session_state:
    st.session_state.edit_row = None
if "edit_original_amount" not in st.session_state:
    st.session_state.edit_original_amount = None
# Re-adding these flags for inline error message display
if "ticker_not_found" not in st.session_state:
    st.session_state.ticker_not_found = False
if "ticker_warning_message" not in st.session_state:
    st.session_state.ticker_warning_message = ""
if "perform_deletion" not in st.session_state:
    st.session_state.perform_deletion = False

# --- Add New Holding Form ---
st.title("Crypto Portfolio Tracker")
st.markdown("""
    Enter your cryptocurrency holdings below to track their real-time value and performance.
    Prices are fetched from CoinGecko.
""")

st.subheader("Add New Holding")
with st.form("add_coin_form"):
    col1_form, col2_form = st.columns([2, 1])
    with col1_form:
        symbol_input = st.text_input("Crypto Ticker or Name", key="add_symbol_input", label_visibility="hidden").upper().strip()
        
        # Display the specific error message for invalid tickers here, below the input
        if st.session_state.ticker_not_found:
            st.error(st.session_state.ticker_warning_message) # <--- Re-added for inline display

    with col2_form:
        amount_input = st.number_input("Crypto Amount", min_value=0.0, format="%.8f", key="add_amount_input", label_visibility="hidden")
    
    submitted = st.form_submit_button("Add Holding")

    if submitted:
        # Reset the ticker error flags at the start of every submission attempt
        st.session_state.ticker_not_found = False
        st.session_state.ticker_warning_message = ""

        if symbol_input and amount_input > 0:
            coingecko_id = get_coingecko_id(symbol_input)
            if coingecko_id:
                found = False
                for i, holding in enumerate(st.session_state.portfolio):
                    if holding["coingecko_id"] == coingecko_id:
                        st.session_state.portfolio[i]["amount"] += amount_input
                        st.success(f"Updated {symbol_input} amount to {st.session_state.portfolio[i]['amount']:,.8f} units!") # <--- Reverted to st.success
                        found = True
                        break
                if not found:
                    st.session_state.portfolio.append({
                        "ticker": symbol_input,
                        "coingecko_id": coingecko_id,
                        "amount": amount_input,
                        "cost_basis": 0.0 # Placeholder for future feature
                    })
                    st.success(f"Added {amount_input:,.8f} {symbol_input} to your portfolio!") # <--- Reverted to st.success
                
                save_portfolio(st.session_state.portfolio)
                st.session_state.selected_rows.clear()
                time.sleep(2) # <--- ADDED: Pause for 2 seconds to allow message to be read
                st.rerun() # Rerun to update the table and chart (and implicitly clear form inputs)
            else:
                st.session_state.ticker_not_found = True # <--- Re-added for inline display
                st.session_state.ticker_warning_message = "Invalid Ticker: Please enter a valid cryptocurrency ticker or name." # <--- Re-added for inline display
                time.sleep(2) # <--- ADDED: Pause for 2 seconds to allow message to be read
                st.rerun() # Rerun to clear the form inputs
        else:
            st.warning("Please enter both a crypto ticker/name and an amount greater than zero.") # <--- Kept st.warning
            time.sleep(2) # <--- ADDED: Pause for 2 seconds to allow message to be read
            st.rerun() # Rerun to clear the form inputs

# --- (The rest of your code for displaying holdings, delete button, edit mode, and chart) ---

st.divider()
st.subheader("Your Current Holdings")

# --- Process Holdings for Display and Chart ---
# Extract unique CoinGecko IDs from current holdings to fetch prices efficiently
coin_ids_to_fetch = list(set([holding["coingecko_id"] for holding in st.session_state.portfolio]))
current_prices = get_crypto_prices(coin_ids_to_fetch)

holdings_data_display = []
total_value = 0.0

for holding in st.session_state.portfolio:
    symbol = holding["ticker"]
    coingecko_id = holding["coingecko_id"]
    amount = holding["amount"]
    
    price = current_prices.get(coingecko_id, 0.0)
    value = price * amount
    total_value += value

    holdings_data_display.append({
        "symbol": symbol,
        "coingecko_id": coingecko_id,
        "amount": amount,
        "price": price,
        "value": value
    })

# --- Delete Selected Button (Fix: Appears if 1 or more selected) ---
if st.session_state.selected_rows:
    if st.button("Delete Selected", type="primary", key="delete_selected_button"):
        symbols_to_delete = st.session_state.selected_rows
        
        st.session_state.portfolio = [
            holding for holding in st.session_state.portfolio
            if holding["ticker"] not in symbols_to_delete
        ]
        
        st.session_state.selected_rows.clear()
        save_portfolio(st.session_state.portfolio)
        st.success("Selected holdings deleted.") # <--- Reverted to st.success
        time.sleep(2) # <--- ADDED: Pause
        st.rerun()

# --- Render Table Headers ---
header_cols = st.columns([1, 2, 2, 2, 2])
header_cols[0].write(" ")
header_cols[1].write("**Ticker**")
header_cols[2].write("**Amount**")
header_cols[3].write("**Price (USD)**")
header_cols[4].write("**Value (USD)**")

# --- Render Holdings Rows (Dynamic based on holdings_data_display) ---
if not holdings_data_display:
    st.info("No holdings added yet. Use the 'Add New Holding' section above.")
else:
    current_checkbox_symbols = set() 

    for item in holdings_data_display:
        symbol = item["symbol"]
        amount = item["amount"]
        price = item["price"]
        value = item["value"]
        current_checkbox_symbols.add(symbol)

        cols = st.columns([1, 2, 2, 2, 2])

        with cols[0]:
            row_controls = st.columns([1, 1])
            checkbox_key = f"checkbox_{symbol}"
            
            initial_checkbox_state = symbol in st.session_state.selected_rows
            
            def update_selected_rows(current_symbol):
                if st.session_state[f"checkbox_{current_symbol}"]:
                    st.session_state.selected_rows.add(current_symbol)
                else:
                    st.session_state.selected_rows.discard(current_symbol)

            row_controls[0].checkbox(
                "Select " + symbol, # Descriptive label for accessibility
                value=initial_checkbox_state, 
                key=checkbox_key,
                on_change=update_selected_rows,
                args=(symbol,),
                label_visibility="hidden" # Hide the label visually
            )

            if row_controls[1].button("✏️", key=f"edit_button_{symbol}"):
                st.session_state.edit_row = symbol
                for holding in st.session_state.portfolio:
                    if holding["ticker"] == symbol:
                        st.session_state.edit_original_amount = holding["amount"]
                        break
                st.rerun()

        # --- Edit Mode ---
        if st.session_state.edit_row == symbol:
            current_holding_amount = 0.0
            for holding in st.session_state.portfolio:
                if holding["ticker"] == symbol:
                    current_holding_amount = holding["amount"]
                    break

            new_amount = cols[2].number_input(
                "Edit amount for " + symbol, 
                value=current_holding_amount, 
                key=f"edit_input_{symbol}_value", 
                format="%.8f",
                label_visibility="hidden" # Hidden for cleaner UI
            )

            cols[1].write(symbol)
            cols[3].write(f"${price:,.2f}")
            cols[4].write(f"${price * new_amount:,.2f}")

            st.write("")
            edit_action_cols = st.columns([1, 1])

            if new_amount != st.session_state.edit_original_amount:
                if edit_action_cols[0].button("Save", key=f"save_{symbol}_button"):
                    for i, holding in enumerate(st.session_state.portfolio):
                        if holding["ticker"] == symbol:
                            st.session_state.portfolio[i]["amount"] = new_amount
                            break
                    save_portfolio(st.session_state.portfolio)
                    st.session_state.edit_row = None
                    st.success(f"{symbol} updated to {new_amount:,.8f} units.") # <--- Reverted to st.success
                    time.sleep(2) # <--- ADDED: Pause
                    st.rerun()
            else:
                edit_action_cols[0].button("Save", key=f"save_{symbol}_button_disabled", disabled=True)

            if edit_action_cols[1].button("Discard", key=f"discard_{symbol}_button"):
                st.session_state.edit_row = None
                st.rerun()
        else:
            # Normal row
            cols[1].write(symbol)
            cols[2].write(f"{amount:,.8f}")
            cols[3].write(f"${price:,.2f}")
            cols[4].write(f"${value:,.2f}")
    
    st.session_state.selected_rows = st.session_state.selected_rows.intersection(current_checkbox_symbols)


st.divider()
st.subheader("Portfolio Summary")
st.write(f"**Total Portfolio Value:** ${total_value:,.2f}")

# --- Portfolio Allocation Pie Chart ---
if holdings_data_display:
    st.subheader("Portfolio Allocation")
    non_zero_holdings = [item for item in holdings_data_display if item["value"] > 0]

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

st.markdown("---")
st.caption("This project was developed by Eduardo Miguel Bennaton solely for demonstration purposes.")