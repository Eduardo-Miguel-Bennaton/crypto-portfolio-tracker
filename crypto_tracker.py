import streamlit as st
import json
import os
import plotly.graph_objects as go
import requests 
import time

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

/* Table cell alignment */
div[data-testid="column"] > div:first-child {
    padding-top: 0.3rem;
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
        return {coin['symbol'].lower(): coin['id'] for coin in coins_data} | {coin['name'].lower(): coin['id'] for coin in coins_data}
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
        except:
            return []
    return []

def save_portfolio(portfolio):
    with open(DATA_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

# State initialization
for key, default in {
    "portfolio": load_portfolio(),
    "selected_rows": set(),
    "edit_row": None,
    "edit_original_amount": None,
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
                st.session_state.selected_rows.clear()
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

st.divider()

# Current Holdings Table
st.subheader("Your Portfolio")

coin_ids = list(set([h["coingecko_id"] for h in st.session_state.portfolio]))
prices = get_crypto_prices(coin_ids)

holdings_data, total_value = [], 0.0
for h in st.session_state.portfolio:
    price = prices.get(h["coingecko_id"], 0.0)
    value = price * h["amount"]
    total_value += value
    holdings_data.append({**h, "price": price, "value": value})

if holdings_data:
    # Delete selected button
    if st.session_state.selected_rows:
        if st.button("Delete Selected", type="primary"):
            st.session_state.portfolio = [
                h for h in st.session_state.portfolio if h["ticker"] not in st.session_state.selected_rows
            ]
            st.session_state.selected_rows.clear()
            save_portfolio(st.session_state.portfolio)
            st.success("Deleted selected holdings.")
            time.sleep(1)
            st.rerun()
    else:
        st.button("Delete Selected", disabled=True)

    header_cols = st.columns([1, 2, 2, 2, 2])
    for i, header in enumerate([" ", "Ticker", "Amount", "Price (USD)", "Value (USD)"]):
        if header.strip():  # Only render non-empty headers
            header_cols[i].write(f"**{header}**")


    valid_symbols = set()

    for item in holdings_data:
        symbol, amount, price, value = item["ticker"], item["amount"], item["price"], item["value"]
        valid_symbols.add(symbol)
        row = st.columns([1, 2, 2, 2, 2])

        with row[0]:
            left, right = st.columns([1, 1])
            cb_key = f"cb_{symbol}"

            if cb_key not in st.session_state:
                st.session_state[cb_key] = False

            def update_selection(sym=symbol, key=cb_key):
                if st.session_state[key]:
                    st.session_state.selected_rows.add(sym)
                else:
                    st.session_state.selected_rows.discard(sym)

            left.checkbox("", value=(symbol in st.session_state.selected_rows),
                key=cb_key, on_change=update_selection)

            if right.button("✏️", key=f"edit_{symbol}"):
                st.session_state.edit_row, st.session_state.edit_original_amount = symbol, amount
                st.rerun()

        if st.session_state.edit_row == symbol:
            row[1].write(symbol)
            new_amt = row[2].number_input("Edit", value=amount, key=f"edit_input_{symbol}",
                                           format="%.8f", label_visibility="hidden")
            row[3].write(f"${price:,.2f}")
            row[4].write(f"${price*new_amt:,.2f}")

            save_col, discard_col = st.columns([1, 1])
            if new_amt != st.session_state.edit_original_amount:
                if save_col.button("💾 Save", key=f"save_{symbol}"):
                    for h in st.session_state.portfolio:
                        if h["ticker"] == symbol:
                            h["amount"] = new_amt
                    save_portfolio(st.session_state.portfolio)
                    st.session_state.edit_row = None
                    time.sleep(1)
                    st.rerun()
            else:
                save_col.button("Save", disabled=True, key=f"save_disabled_{symbol}")

            if discard_col.button("Cancel", key=f"cancel_{symbol}"):
                st.session_state.edit_row = None
                st.rerun()
        else:
            row[1].write(symbol)
            row[2].write(f"{amount:,.8f}")
            row[3].write(f"${price:,.2f}")
            row[4].write(f"${value:,.2f}")

    # Cleanup orphan checkboxes
    st.session_state.selected_rows = st.session_state.selected_rows.intersection(valid_symbols)
else:
    st.info("Your portfolio is empty. Add your first holding above.")

st.divider()

# Summary Section
st.subheader("Portfolio Summary")
st.markdown(f"<div class='total-value'>Total: ${total_value:,.2f}</div>", unsafe_allow_html=True)

# Pie Chart
if holdings_data:
    non_zero = [h for h in holdings_data if h["value"] > 0]
    if non_zero:
        labels = [h["ticker"] for h in non_zero]
        values = [h["value"] for h in non_zero]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
        fig.update_layout(margin=dict(t=20, b=20, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No holdings with value to visualize.")