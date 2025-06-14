import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Crypto Portfolio Tracker", layout="wide")

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
div[data-testid="stMainBlockContainer"] {padding-top: 0.5rem;}
.stButton>button {
    height: 1.8em; border-radius: 5px; padding: 0 0.3em; display: flex; align-items: center;
    justify-content: center; font-size: 0.9em; line-height: 1; white-space: nowrap;
}
.stButton > button[data-testid^="stButton-secondary"] {
    height: 1.6em; min-width: 1.6em; width: 1.6em; padding: 0; font-size: 0.9em; border-radius: 50%;
    margin: 0 0.1rem;
}
.st-emotion-cache-1uj25sm.e1f1d6gn4 {padding-left: 0; padding-right: 0;}
.st-emotion-cache-1kyxpmf.e1f1d6gn1 {padding-left: 0.1rem; padding-right: 0.1rem;}
div[data-testid^="stVerticalBlock"] > div[data-testid^="stHorizontalBlock"] > div[data-testid^="stBlock"] {
    display: flex; align-items: center; min-height: 2.2em;
}
.st-emotion-cache-fyb0a4, .st-emotion-cache-1c7y3k9 {margin-top: 0 !important; margin-bottom: 0 !important;}
div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div:first-child {
    border-bottom: none !important;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_crypto_prices(coin_ids):
    if not coin_ids: return {}
    ids_param = ",".join(coin_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        prices = {coin_id: data[coin_id]['usd'] for coin_id in coin_ids if coin_id in data and 'usd' in data[coin_id]}
        return prices
    except: return {}

@st.cache_data(ttl=3600)
def get_coin_list():
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        coins_data = response.json()
        return {coin['symbol'].lower(): coin['id'] for coin in coins_data}
    except: return {}

coin_id_map = get_coin_list()

def get_coingecko_id(ticker_or_name):
    return coin_id_map.get(ticker_or_name.lower())

st.title("Crypto Portfolio Tracker")
st.markdown("Enter your cryptocurrency holdings below to track their real-time value.")

# Session state initialization
if 'holdings' not in st.session_state: st.session_state.holdings = []
if 'new_ticker_input_value' not in st.session_state: st.session_state.new_ticker_input_value = ""
if 'new_amount_input_value' not in st.session_state: st.session_state.new_amount_input_value = 0.0
if 'selected_for_delete' not in st.session_state: st.session_state.selected_for_delete = set()

# Add new holding
st.subheader("Add New Holding")
col1, col2, col3 = st.columns([2, 1.5, 1])
with col1: new_ticker = st.text_input("Crypto Ticker or Name", value=st.session_state.new_ticker_input_value, key="add_new_ticker_input").strip()
with col2: new_amount = st.number_input("Amount", min_value=0.0, value=st.session_state.new_amount_input_value, key="add_new_amount_input", format="%.8f")
with col3:
    st.markdown("<div style='height: 33px;'></div>", unsafe_allow_html=True)
    if st.button("Add Holding", key="add_holding_button", type="primary"):
        if new_ticker and new_amount > 0:
            coingecko_id = get_coingecko_id(new_ticker)
            if coingecko_id:
                found = False
                for holding in st.session_state.holdings:
                    if holding['coingecko_id'] == coingecko_id:
                        holding['amount'] += new_amount
                        st.success(f"Updated {new_ticker.upper()} to {holding['amount']}.")
                        found = True
                        break
                if not found:
                    st.session_state.holdings.append({"ticker": new_ticker.upper(), "coingecko_id": coingecko_id, "amount": new_amount})
                    st.success(f"Added {new_amount} {new_ticker.upper()}!")
                st.session_state.new_ticker_input_value = ""
                st.session_state.new_amount_input_value = 0.0
                st.rerun()
            else: st.error(f"Could not find CoinGecko ID for '{new_ticker}'.")
        else: st.warning("Enter a ticker and amount > 0.")

st.markdown("---")

# Holdings display
st.subheader("Your Current Holdings")

if not st.session_state.holdings:
    st.info("No holdings added yet.")
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
            "Ticker": row['ticker'], "Amount": row['amount'], "Current Price": current_price,
            "Current Value": current_value, "coingecko_id": coingecko_id, "index": index
        })

    st.write("### Portfolio Breakdown")
    cols = st.columns([0.8, 2, 1.5, 1.5, 1.5])
    headers = ["", "Ticker", "Amount", "Current Price", "Current Value"]
    for col, header in zip(cols, headers):
        col.markdown(f"<div style='margin-bottom:0px; font-weight:600;'>{header}</div>", unsafe_allow_html=True)
    st.markdown("---")

    # Holdings rows
    for i, holding in enumerate(st.session_state.holdings):
        coingecko_id = holding['coingecko_id']
        current_price = current_prices.get(coingecko_id, 0.0)
        current_value = holding['amount'] * current_price

        col_checkbox, col_ticker, col_amount, col_price, col_value = st.columns([0.8, 2, 1.5, 1.5, 1.5])

        with col_checkbox:
            is_checked = st.checkbox("", key=f"checkbox_{i}", value=(i in st.session_state.selected_for_delete), label_visibility="collapsed")
            if is_checked:
                st.session_state.selected_for_delete.add(i)
            else:
                st.session_state.selected_for_delete.discard(i)

        with col_ticker: st.write(holding['ticker'])
        with col_amount: st.write(f"{holding['amount']:.8f}")
        with col_price: st.write(f"${current_price:,.2f}")
        with col_value: st.write(f"${current_value:,.2f}")

    st.markdown("---")

    if len(st.session_state.selected_for_delete) > 0:
        if st.button(f"Delete Selected ({len(st.session_state.selected_for_delete)})", key="delete_multiple_button", type="secondary"):
            indices_to_delete = sorted(list(st.session_state.selected_for_delete), reverse=True)
            for idx in indices_to_delete:
                if idx < len(st.session_state.holdings):
                    del st.session_state.holdings[idx]
            st.session_state.selected_for_delete.clear()
            st.success("Selected holdings deleted.")
            st.rerun()

    st.subheader("Portfolio Summary")
    st.metric(label="Total Portfolio Value", value=f"${total_portfolio_value:,.2f}")

    if total_portfolio_value > 0:
        temp_df_for_chart = pd.DataFrame(portfolio_data)
        temp_df_for_chart['percentage'] = (temp_df_for_chart['Current Value'] / total_portfolio_value) * 100
        pie_chart_data = temp_df_for_chart[temp_df_for_chart['Current Value'] > 0]
        if not pie_chart_data.empty:
            fig = px.pie(pie_chart_data, values='Current Value', names='Ticker', title='Portfolio Distribution')
            fig.update_traces(textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No significant holdings to display.")
    else:
        st.info("No holdings with value.")

st.markdown("---")
st.caption("Developed by Eduardo Miguel Bennaton for demonstration purposes.")
