import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# --- Configuration ---
# Set the page title and layout
st.set_page_config(page_title="Crypto Portfolio Tracker", layout="wide")

# --- Helper Functions ---

@st.cache_data(ttl=3600)  # Cache data for 1 hour to avoid excessive API calls
def get_crypto_prices(coin_ids):
    """
    Fetches real-time cryptocurrency prices from the CoinGecko API.

    Args:
        coin_ids (list): A list of CoinGecko coin IDs (e.g., ['bitcoin', 'ethereum']).

    Returns:
        dict: A dictionary where keys are CoinGecko coin IDs and values are their
              current prices in USD. Returns an empty dictionary if the API call fails.
    """
    if not coin_ids:
        return {}

    # Convert list of coin IDs to a comma-separated string for the API
    ids_param = ",".join(coin_ids)
    # CoinGecko API endpoint for simple price lookup
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd"
    
    try:
        response = requests.get(url, timeout=10) # Set a timeout for the request
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()
        
        prices = {}
        for coin_id in coin_ids:
            if coin_id in data and 'usd' in data[coin_id]:
                prices[coin_id] = data[coin_id]['usd']
            else:
                # Handle cases where a coin ID might not be found or price is missing
                st.warning(f"Could not fetch price for '{coin_id}'. It might be an invalid ID or temporary API issue.")
                prices[coin_id] = 0 # Assign 0 or handle as per your logic
        return prices
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching crypto prices: {e}. Please check your internet connection or CoinGecko API status.")
        return {} # Return empty dictionary on error
    except json.JSONDecodeError:
        st.error("Error decoding JSON response from CoinGecko API. The API might be returning an invalid response.")
        return {}
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return {}


@st.cache_data(ttl=3600)
def get_coin_list():
    """
    Fetches the list of supported coins from CoinGecko API to help with ID mapping.

    Returns:
        dict: A dictionary mapping coin symbols (like 'btc') and names ('Bitcoin') to their
              CoinGecko IDs ('bitcoin').
    """
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        coins_data = response.json()
        
        coin_map = {}
        for coin in coins_data:
            # Map both symbol and name to the CoinGecko ID
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

# Load the coin list once at the start
coin_id_map = get_coin_list()

def get_coingecko_id(ticker_or_name):
    """
    Converts a common ticker (e.g., 'BTC') or name ('Bitcoin') to its CoinGecko ID.
    """
    lookup_key = ticker_or_name.lower()
    return coin_id_map.get(lookup_key)

# --- Streamlit App Layout ---

st.title("💰 Crypto Portfolio Tracker")
st.markdown("""
    Enter your cryptocurrency holdings below to track their real-time value and performance.
    Prices are fetched from CoinGecko.
""")

# Initialize session state for holdings if not already present
# This allows us to add/remove holdings dynamically
if 'holdings' not in st.session_state:
    st.session_state.holdings = []

# Section for adding new holdings
st.subheader("Add New Holding")
col1, col2, col3 = st.columns(3)

with col1:
    new_ticker = st.text_input("Crypto Ticker or Name (e.g., BTC, Ethereum)", key="new_ticker_input").strip()
with col2:
    new_amount = st.number_input("Amount (e.g., 0.5, 100)", min_value=0.0, value=0.0, key="new_amount_input", format="%.8f")
with col3:
    # Add a small buffer column for alignment if needed, or simply for spacing
    st.markdown("<div style='height: 33px;'></div>", unsafe_allow_html=True) # Spacer for button alignment
    if st.button("Add Holding"):
        if new_ticker and new_amount > 0:
            coingecko_id = get_coingecko_id(new_ticker)
            if coingecko_id:
                st.session_state.holdings.append({
                    "ticker": new_ticker.upper(), # Store in uppercase for display
                    "coingecko_id": coingecko_id,
                    "amount": new_amount,
                    "cost_basis": 0.0 # Placeholder for future cost basis
                })
                st.success(f"Added {new_amount} {new_ticker.upper()} to your portfolio!")
                # Clear inputs after adding
                st.session_state.new_ticker_input = ""
                st.session_state.new_amount_input = 0.0
            else:
                st.error(f"Could not find CoinGecko ID for '{new_ticker}'. Please check the ticker/name.")
        else:
            st.warning("Please enter both a crypto ticker/name and an amount greater than zero.")

st.markdown("---")

# Display current holdings and allow removal
st.subheader("Your Current Holdings")

if not st.session_state.holdings:
    st.info("No holdings added yet. Use the 'Add New Holding' section above.")
else:
    # Create a DataFrame from holdings for easier display and manipulation
    holdings_df = pd.DataFrame(st.session_state.holdings)
    
    # Get unique CoinGecko IDs for fetching prices
    coin_ids_to_fetch = holdings_df['coingecko_id'].unique().tolist()
    
    # Fetch current prices
    current_prices = get_crypto_prices(coin_ids_to_fetch)

    # Prepare data for display and calculation
    portfolio_data = []
    total_portfolio_value = 0.0
    
    for index, row in holdings_df.iterrows():
        coingecko_id = row['coingecko_id']
        current_price = current_prices.get(coingecko_id, 0.0) # Get price, default to 0 if not found
        current_value = row['amount'] * current_price
        total_portfolio_value += current_value

        portfolio_data.append({
            "Ticker": row['ticker'],
            "Amount": row['amount'],
            "Current Price (USD)": f"${current_price:,.2f}",
            "Current Value (USD)": f"${current_value:,.2f}",
            "coingecko_id": coingecko_id, # Keep for internal use
            "raw_current_value": current_value # Keep raw value for calculations
        })

    portfolio_df = pd.DataFrame(portfolio_data)
    
    # Display holdings in a data table
    st.table(portfolio_df[['Ticker', 'Amount', 'Current Price (USD)', 'Current Value (USD)']])

    # Option to remove holdings
    if st.session_state.holdings: # Only show if there are holdings
        st.subheader("Remove Holding")
        # Create a list of options for the selectbox
        holding_options = [f"{h['ticker']} ({h['amount']})" for h in st.session_state.holdings]
        
        # Add "Select to remove" as the first option if there are holdings
        if holding_options:
            holding_options.insert(0, "Select a holding to remove")
        
        holding_to_remove_idx = st.selectbox(
            "Select a holding to remove:",
            options=range(len(holding_options)), # Use indices for options
            format_func=lambda x: holding_options[x], # Display actual holding string
            key="remove_holding_select"
        )
        
        # Check if a valid holding was selected (not the "Select to remove" option)
        if holding_to_remove_idx > 0:
            if st.button("Remove Selected Holding"):
                # Remove the holding at the chosen index (adjust for the "Select to remove" offset)
                removed_holding = st.session_state.holdings.pop(holding_to_remove_idx - 1)
                st.success(f"Removed {removed_holding['amount']} {removed_holding['ticker']} from your portfolio.")
                st.rerun() # Rerun the app to update the display immediately
    
    st.markdown("---")

    # --- Portfolio Summary ---
    st.subheader("Portfolio Summary")
    st.metric(label="Total Portfolio Value", value=f"${total_portfolio_value:,.2f}")

    # --- Pie Chart ---
    if total_portfolio_value > 0 and not portfolio_df.empty:
        # Filter out holdings with zero value for the pie chart
        pie_chart_data = portfolio_df[portfolio_df['raw_current_value'] > 0]
        
        if not pie_chart_data.empty:
            # Create the pie chart using plotly.express
            fig = px.pie(
                pie_chart_data, 
                values='raw_current_value', 
                names='Ticker', 
                title='Portfolio Distribution by Value',
                hole=0.4 # Creates a donut chart
            )
            fig.update_traces(textinfo='percent+label', pull=[0.05] * len(pie_chart_data)) # Show percentage and label, slight pull for emphasis
            fig.update_layout(showlegend=True, height=500, width=700) # Adjust size
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No holdings with a positive value to display in the pie chart.")
    else:
        st.info("Add some holdings to see your portfolio summary and distribution!")

st.markdown("---")
st.caption("Data provided by CoinGecko API. Prices are refreshed periodically.")
