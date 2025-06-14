import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

st.set_page_config(page_title="Crypto Portfolio Tracker", layout="wide")

@st.cache_data(ttl=3600)
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
                st.warning(f"Could not fetch price for '{coin_id}'. It might be an invalid ID or temporary API issue. Setting price to $0.00.")
                prices[coin_id] = 0.0
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

coin_id_map = get_coin_list()

def get_coingecko_id(ticker_or_name):
    """
    Converts a common ticker (e.g., 'BTC') or name ('Bitcoin') to its CoinGecko ID.
    """
    lookup_key = ticker_or_name.lower()
    return coin_id_map.get(lookup_key)


st.title("Crypto Portfolio Tracker")
st.markdown("""
    Enter your cryptocurrency holdings below to track their real-time value and performance.
    Prices are fetched from CoinGecko.
""")

if 'holdings' not in st.session_state:
    st.session_state.holdings = []

if 'new_ticker_input_value' not in st.session_state:
    st.session_state.new_ticker_input_value = ""
if 'new_amount_input_value' not in st.session_state:
    st.session_state.new_amount_input_value = 0.0

st.subheader("Add New Holding")
col1, col2, col3 = st.columns(3)

with col1:
    new_ticker = st.text_input(
        "Crypto Ticker or Name (e.g., BTC, ETH)",
        value=st.session_state.new_ticker_input_value,
        key="add_new_ticker_input"
    ).strip()
with col2:
    new_amount = st.number_input(
        "Amount (e.g., 0.5, 100)",
        min_value=0.0,
        value=st.session_state.new_amount_input_value,
        key="add_new_amount_input",
        format="%.8f"
    )
with col3:
    st.markdown("<div style='height: 33px;'></div>", unsafe_allow_html=True)
    if st.button("Add Holding", key="add_holding_button"):
        if new_ticker and new_amount > 0:
            coingecko_id = get_coingecko_id(new_ticker)
            if coingecko_id:
                st.session_state.holdings.append({
                    "ticker": new_ticker.upper(),
                    "coingecko_id": coingecko_id,
                    "amount": new_amount,
                    "cost_basis": 0.0
                })
                st.success(f"Added {new_amount} {new_ticker.upper()} to your portfolio!")
                st.session_state.new_ticker_input_value = ""
                st.session_state.new_amount_input_value = 0.0
                st.rerun()
            else:
                st.error(f"Could not find CoinGecko ID for '{new_ticker}'. Please check the ticker/name.")
        else:
            st.warning("Please enter both a crypto ticker/name and an amount greater than zero.")

st.markdown("---")

st.subheader("Your Current Holdings")

if not st.session_state.holdings:
    st.info("No holdings added yet. Use the 'Add New Holding' section above.")
else:
    holdings_df = pd.DataFrame(st.session_state.holdings)
    
    coin_ids_to_fetch = holdings_df['coingecko_id'].unique().tolist()
    
    current_prices = get_crypto_prices(coin_ids_to_fetch)

    portfolio_data = []
    total_portfolio_value = 0.0
    
    for index, row in holdings_df.iterrows():
        coingecko_id = row['coingecko_id']
        current_price = current_prices.get(coingecko_id, 0.0)
        current_value = row['amount'] * current_price
        total_portfolio_value += current_value

        portfolio_data.append({
            "Ticker": row['ticker'],
            "Amount": row['amount'],
            "Current Price (USD)": f"${current_price:,.2f}",
            "Current Value (USD)": f"${current_value:,.2f}",
            "coingecko_id": coingecko_id,
            "raw_current_value": current_value,
            "index": index
        })

    portfolio_df = pd.DataFrame(portfolio_data)
    
    st.table(portfolio_df[['Ticker', 'Amount', 'Current Price (USD)', 'Current Value (USD)']])

    st.markdown("---")
    
    st.subheader("Edit Holding")

    edit_holding_options = ["Select a holding to edit"] + [
        f"{h['ticker']} ({h['amount']})" for h in st.session_state.holdings
    ]

    selected_edit_option_index = st.selectbox(
        "Select holding to edit:",
        options=range(len(edit_holding_options)),
        format_func=lambda x: edit_holding_options[x],
        key="edit_holding_select"
    )

    if selected_edit_option_index > 0:
        selected_holding_index = selected_edit_option_index - 1
        holding_to_edit = st.session_state.holdings[selected_holding_index]

        st.markdown(f"**Editing: {holding_to_edit['ticker']} ({holding_to_edit['amount']})**")

        edit_col1, edit_col2 = st.columns(2)
        with edit_col1:
            edited_amount = st.number_input(
                "New Amount:",
                min_value=0.0,
                value=holding_to_edit['amount'],
                key=f"edit_amount_input_{selected_holding_index}",
                format="%.8f"
            )
        with edit_col2:
            st.markdown("<div style='height: 33px;'></div>", unsafe_allow_html=True)
            if st.button("Update Holding", key=f"update_holding_button_{selected_holding_index}"):
                if edited_amount >= 0:
                    st.session_state.holdings[selected_holding_index]['amount'] = edited_amount
                    st.success(f"Updated {holding_to_edit['ticker']} to {edited_amount} units.")
                    st.rerun()
                else:
                    st.error("Amount cannot be negative.")
    else:
        st.info("Select a holding from the dropdown above to edit its amount.")

    st.markdown("---")

    st.subheader("Remove Holding")
    holding_options_remove = ["Select a holding to remove"] + [
        f"{h['ticker']} ({h['amount']})" for h in st.session_state.holdings
    ]

    holding_to_remove_idx = st.selectbox(
        "Select a holding to remove:",
        options=range(len(holding_options_remove)),
        format_func=lambda x: holding_options_remove[x],
        key="remove_holding_select"
    )

    if holding_to_remove_idx > 0:
        if st.button("Remove Selected Holding", key="remove_selected_button"):
            removed_holding = st.session_state.holdings.pop(holding_to_remove_idx - 1)
            st.success(f"Removed {removed_holding['amount']} {removed_holding['ticker']} from your portfolio.")
            st.rerun()
    else:
        st.info("Select a holding from the dropdown above to remove it.")

    st.markdown("---")

    st.subheader("Portfolio Summary")
    st.metric(label="Total Portfolio Value", value=f"${total_portfolio_value:,.2f}")

    pie_chart_data = portfolio_df[portfolio_df['raw_current_value'] > 0]

    if total_portfolio_value > 0 and not pie_chart_data.empty:
        fig = px.pie(
            pie_chart_data,
            values='raw_current_value',
            names='Ticker',
            title='Portfolio Distribution by Value',
            hole=0.4
        )
        fig.update_traces(textinfo='percent+label', pull=[0.01] * len(pie_chart_data))
        fig.update_layout(showlegend=True, height=500, width=700)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No holdings with a positive value to display in the pie chart or portfolio is empty.")

st.markdown("---")
st.caption("This project was developed by Eduardo Miguel Bennaton solely for demonstration purposes.")