import streamlit as st
import json
import os
import plotly.graph_objects as go
import requests
import time
import pandas as pd # Import pandas for data manipulation with st.data_editor

DATA_FILE = "portfolio_data.json"

st.set_page_config(page_title="Crypto Portfolio Tracker", layout="wide")

# Modern clean SaaS-like styles
st.markdown("""
<style>
/* Hide default Streamlit elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display: none;}
header {visibility: hidden;}
div[data-testid="stMainBlockContainer"] { padding-top: 1rem; }

/* Smooth buttons */
button {
    transition: all 0.2s ease;
}
button:hover {
    transform: scale(1.05);
}

/* Section divider */
hr {
    border-top: 2px solid #e0e0e0;
}

/* Portfolio total emphasis */
.total-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #2e7d32;
}

/* --- NEW: Hide the "Add row" button from the data editor --- */
button[data-testid="stDataFrameAddRowButton"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_crypto_prices(coin_ids):
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
            prices[coin_id] = data.get(coin_id, {}).get('usd', 0.0)
        return prices
    except Exception as e:
        st.error(f"Error fetching crypto prices: {e}")
        return {}

@st.cache_data(ttl=86400)
def get_coin_list():
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        coins_data = response.json()
        # Create map for both symbol and name to coingecko_id
        coin_map = {}
        for coin in coins_data:
            coin_map[coin['symbol'].lower()] = coin['id']
            coin_map[coin['name'].lower()] = coin['id']
        return coin_map
    except Exception as e:
        st.error(f"Error fetching coin list: {e}")
        return {}

coin_id_map = get_coin_list()

def get_coingecko_id(ticker_or_name):
    return coin_id_map.get(ticker_or_name.lower())

def load_portfolio():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            # Handle empty or malformed JSON file
            return []
    return []

def save_portfolio(portfolio):
    with open(DATA_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

# State initialization
for key, default in {
    "portfolio": load_portfolio(),
    "ticker_not_found": False,
    "ticker_warning_message": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("Crypto Portfolio Tracker")
st.markdown("Track your cryptocurrency holdings with live prices from CoinGecko.")

# Add holding form
with st.form("add_coin_form"):
    col1, col2, col3 = st.columns([4, 3, 2])
    with col1:
        symbol_input = st.text_input("Crypto Ticker or Name", key="add_symbol_input", label_visibility="hidden").upper().strip()
        if st.session_state.ticker_not_found:
            st.error(st.session_state.ticker_warning_message)
    with col2:
        amount_input = st.number_input("Amount", min_value=0.0, format="%.8f", key="add_amount_input", label_visibility="hidden")
    submitted = col3.form_submit_button("Add")

    if submitted:
        st.session_state.ticker_not_found = False
        st.session_state.ticker_warning_message = ""
        if symbol_input and amount_input > 0:
            coingecko_id = get_coingecko_id(symbol_input)
            if coingecko_id:
                found = False
                for holding in st.session_state.portfolio:
                    if holding["coingecko_id"] == coingecko_id:
                        holding["amount"] += amount_input
                        st.success(f"Updated {symbol_input} to {holding['amount']:,.8f}")
                        found = True
                        break
                if not found:
                    st.session_state.portfolio.append({
                        "ticker": symbol_input,
                        "coingecko_id": coingecko_id,
                        "amount": amount_input
                    })
                    st.success(f"Added {amount_input:,.8f} {symbol_input}")
                save_portfolio(st.session_state.portfolio)
                time.sleep(1)
                st.rerun()
            else:
                st.session_state.ticker_not_found = True
                st.session_state.ticker_warning_message = "Invalid ticker. Please enter a valid crypto."
                time.sleep(1)
                st.rerun()
        else:
            st.warning("Fill both fields.")
            time.sleep(1)
            st.rerun()

coin_ids = list(set([h["coingecko_id"] for h in st.session_state.portfolio]))
prices = get_crypto_prices(coin_ids)

holdings_data = []
total_value = 0.0
for i, h in enumerate(st.session_state.portfolio):
    price = prices.get(h["coingecko_id"], 0.0)
    value = price * h["amount"]
    total_value += value
    holdings_data.append({
        "id": i, # Unique ID for each row, helpful for tracking deletions
        "Ticker": h["ticker"],
        "Amount": h["amount"],
        "Price (USD)": f"${price:,.2f}",
        "Value (USD)": f"${value:,.2f}"
    })

if holdings_data:
    df = pd.DataFrame(holdings_data)

    # Streamlit Data Editor
    edited_df = st.data_editor(
        df,
        column_config={
            "id": st.column_config.Column(
                "Select",
                help="Select to delete",
                width="small",
                disabled=True # 'id' column should not be editable directly
            ),
            "Ticker": st.column_config.Column(
                "Ticker",
                help="Cryptocurrency Ticker",
                width="medium",
                disabled=True # Ticker should not be editable after adding
            ),
            "Amount": st.column_config.NumberColumn(
                "Amount",
                help="Your holding amount",
                min_value=0.0,
                format="%.8f",
            ),
            "Price (USD)": st.column_config.Column(
                "Price (USD)",
                help="Current price in USD",
                disabled=True # Price is live, not editable
            ),
            "Value (USD)": st.column_config.Column(
                "Value (USD)",
                help="Total value in USD",
                disabled=True # Value is calculated, not editable
            )
        },
        hide_index=True,
        # Changed back to "dynamic" to bring back the "Select" column (checkboxes)
        num_rows="dynamic", 
        use_container_width=True,
        key="portfolio_editor"
    )

    # Get the state of the data editor safely
    editor_state = st.session_state.get('portfolio_editor', {})

    # Process changes from data_editor for edits
    if editor_state.get('edited_rows'):
        for idx, changes in editor_state['edited_rows'].items():
            original_id = df.loc[idx, 'id'] # Get the original unique ID from the DataFrame
            
            # Find the corresponding holding in st.session_state.portfolio using 'id'
            for h_idx, holding in enumerate(st.session_state.portfolio):
                if h_idx == original_id: # Assuming 'id' in DataFrame corresponds to list index
                    if 'Amount' in changes:
                        new_amount = changes['Amount']
                        # Ensure new_amount is a number before comparison
                        if isinstance(new_amount, (int, float)) and new_amount >= 0:
                            holding["amount"] = new_amount
                            save_portfolio(st.session_state.portfolio)
                            st.toast(f"Updated {holding['ticker']} amount to {new_amount:,.8f}", icon="✅")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Amount cannot be negative or invalid.")
                            time.sleep(0.5)
                            st.rerun()
                    break
    
    # Handle deletions from the data editor's internal mechanism
    # 'deleted_rows' contains the indices of rows marked for deletion
    if editor_state.get('deleted_rows'):
        # Get the original IDs of the deleted rows
        deleted_original_ids = [df.loc[i, 'id'] for i in editor_state['deleted_rows']]
        
        # Filter out the holdings based on their original IDs
        st.session_state.portfolio = [
            holding for h_idx, holding in enumerate(st.session_state.portfolio)
            if h_idx not in deleted_original_ids
        ]
        save_portfolio(st.session_state.portfolio)
        st.success("Deleted selected holdings.")
        time.sleep(1)
        st.rerun()
    
else:
    st.info("Your portfolio is empty. Add your first holding above.")

st.divider()

## Portfolio Summary
st.markdown(f"<div class='total-value'>Total: ${total_value:,.2f}</div>", unsafe_allow_html=True)

# Pie Chart
if holdings_data:
    non_zero = [h for h in st.session_state.portfolio if prices.get(h["coingecko_id"], 0.0) * h["amount"] > 0]
    if non_zero:
        labels = [h["ticker"] for h in non_zero]
        values = [prices.get(h["coingecko_id"], 0.0) * h["amount"] for h in non_zero]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
        fig.update_layout(margin=dict(t=20, b=20, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No holdings with value to visualize.")