# Crypto Portfolio Tracker

A responsive web application built with Streamlit to help users track their cryptocurrency holdings with live price data from CoinGecko. This tool provides a clear overview of your digital asset portfolio, including current prices, total values, and a visual distribution of your investments.

## Features

* **Live Price Tracking**: Fetches real-time cryptocurrency prices for your holdings using the CoinGecko API.
* **Add/Update Holdings**: Easily add new cryptocurrencies to your portfolio or update existing amounts.
* **Portfolio Management**: A dynamic table allows you to view, edit, and delete individual cryptocurrency holdings.
* **Interactive Data Editor**: Utilize Streamlit's `st.data_editor` for a seamless editing experience, including direct amount modification and selection for deletion.
* **Portfolio Summary**: Displays the total estimated value of your portfolio in USD.
* **Visual Distribution**: Presents a pie chart illustrating the proportional value of each cryptocurrency in your portfolio.
* **Persistent Data Storage**: Your portfolio data is automatically saved to a local JSON file, ensuring your holdings are remembered between sessions.
* **Clean User Interface**: Custom CSS ensures a streamlined and focused user experience.

## Technologies Used

* **Streamlit**: For rapidly building the interactive web application.
* **CoinGecko API**: For fetching up-to-date cryptocurrency price data and coin lists.
* **Pandas**: For efficient data handling and manipulation of portfolio data.
* **Plotly**: For generating interactive pie charts to visualize portfolio distribution.
* **Python**: The core programming language for the application logic.

## How to Run

To get this Crypto Portfolio Tracker up and running on your local machine:

1.  **Clone the repository** (if applicable) or ensure you have all project files in one directory.
2.  **Ensure you have Python installed** (Python 3.8+ recommended).
3.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
4.  **Install the required libraries**:
    ```bash
    pip install streamlit pandas plotly requests
    ```
    *(Note: Ensure your Streamlit version is `1.29.0` or higher for full compatibility with `st.column_config.Column`'s `visibility` argument, though `pip install --upgrade streamlit` typically handles this.)*
5.  **Run the Streamlit application**:
    ```bash
    streamlit run app.py
    ```
    (Replace `app.py` with `crypto_tracker.py` if you haven't renamed your main file.)

    This will open the application in your default web browser.

## Project Structure (if modularized)

If the project has been modularized into separate files:

* `app.py`: The main Streamlit application script, orchestrating UI and logic.
* `data_handler.py`: Contains functions for interacting with data (fetching prices, loading/saving portfolio).
* `portfolio_manager.py`: Encapsulates core portfolio logic (adding, updating, deleting holdings).
* `ui_components.py`: Houses functions responsible for rendering specific UI elements and forms.

This separation enhances readability, maintainability, and reusability of the code.
