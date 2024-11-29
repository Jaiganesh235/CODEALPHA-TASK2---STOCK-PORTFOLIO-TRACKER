import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import yfinance as yf
import threading
import time
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.dates import DateFormatter, AutoDateLocator
from mplfinance.original_flavor import candlestick_ohlc
import matplotlib.dates as mdates
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.badges import badge

# Set up the page configuration
st.set_page_config(page_title="Stock Portfolio Tracker", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    /* General Body Styling */
    body {
        background-color: #f7f9fc;
        color: #2c3e50;
        font-family: 'Roboto', sans-serif;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #00509e;
    }

    /* Sidebar Styling */
    .css-1aumxhk, .css-1lcbmhc, .css-1avcm0n, .css-1l3ip04 {
        background: linear-gradient(to bottom, #023047, #00509e);
        color: white;
    }
    .css-1aumxhk a, .css-1aumxhk a:hover {
        color: #ffb703;
        text-decoration: none;
    }

    /* Enhanced Button Styling */
    .stButton > button {
        background: linear-gradient(to right, #ff9e00, #ff5e00);
        color: white;
        font-size: 1.2rem;
        font-weight: bold;
        padding: 10px 25px;
        border-radius: 12px;
        border: none;
        transition: all 0.3s ease-in-out;
    }
    .stButton > button:hover {
        background: linear-gradient(to right, #ff5e00, #ff9e00);
        transform: scale(1.05);
        color: white;
    }

    /* Input Field Styling */
    .stTextInput > div > div > input {
        font-size: 16px;
        background-color: #e1e5ea;
        color: #2c3e50;
        border-radius: 8px;
        padding: 8px;
    }

    /* Dataframe Table Styling */
    .stDataFrame, .stMarkdown {
        background-color: #ffffff;
        border-radius: 10px;
        color: #2c3e50;
        font-size: 1rem;
    }

    /* Badge Styling */
    .st-badge {
        background-color: #023047;
        color: white;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.9rem;
        font-weight: bold;
    }

    /* Logout Button */
    .logout-button {
        background-color: #e63946;
        color: white;
        font-size: 1rem;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 8px 16px;
        transition: all 0.2s ease;
    }
    .logout-button:hover {
        background-color: #ff6f61;
    }

    /* Navigation Button Highlight */
    .st-nav-active {
        background-color: #00509e !important;
        color: white;
        font-weight: bold;
        border-radius: 6px;
        padding: 8px;
    }

    /* Header Animation */
    h1 {
        animation: fadeIn 1.5s;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    </style>
""", unsafe_allow_html=True)


# Replace these with your actual API keys
FINNHUB_API_KEY = "csofiepr01qt3r34amqgcsofiepr01qt3r34amr0"
ALPHAVANTAGE_API_KEY = "VC7F743M0GN8W98M"
NEWS_API_KEY = "1546917503f04be98ee78776888b78f2"
DATA_FILE = "user_data.json"

# Load user data from file with error handling
def load_user_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                st.warning("User data file is corrupted. Resetting data.")
    return {}

# Save user data to file
def save_user_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, default=str)

# Initialize session state
def initialize_session_state():
    if 'user_logged_in' not in st.session_state:
        st.session_state.user_logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = {}
    if 'transactions' not in st.session_state:
        st.session_state.transactions = []
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = {}
    if 'real_time_prices' not in st.session_state:
        st.session_state.real_time_prices = {}
    thread = threading.Thread(target=fetch_real_time_prices, daemon=True)
    thread.start()    

# Fetch stock price using Finnhub or AlphaVantage
def fetch_stock_price(symbol):
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            price = data.get("c")
            if price is not None:
                return price
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHAVANTAGE_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if "Global Quote" in data and "05. price" in data["Global Quote"]:
                return float(data["Global Quote"]["05. price"])
        st.warning(f"Could not retrieve data for {symbol}.")
    except Exception as e:
        st.error(f"Error fetching stock price: {e}")
    return None

# Fetch real-time prices for portfolio stocks
def fetch_real_time_prices():
    while True:
        # Ensure 'portfolio' and 'real_time_prices' are initialized in session state
        if 'portfolio' not in st.session_state:
            st.session_state['portfolio'] = {}  # Initialize portfolio if it doesn't exist
        if 'real_time_prices' not in st.session_state:
            st.session_state['real_time_prices'] = {}  # Initialize real_time_prices if it doesn't exist
        
        # Iterate over all symbols in the portfolio and fetch their real-time prices
        for symbol in st.session_state.portfolio:
            price = fetch_stock_price(symbol)  # Fetch the current stock price
            if price is not None:
                # Update real_time_prices in session state if price is valid
                st.session_state.real_time_prices[symbol] = price

        # Sleep for 60 seconds before the next fetch cycle
        time.sleep(60)

# Fetch historical data for visualization
def fetch_stock_history(symbol, start_date=None, end_date=None):
    if start_date is None:
        start_date = datetime.now() - timedelta(days=90)
    if end_date is None:
        end_date = datetime.now()
    try:
        data = yf.download(symbol, start=start_date, end=end_date)
        if not data.empty:
            data = data.reset_index()
            data['Date'] = pd.to_datetime(data['Date'])
            return data
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
    st.warning(f"Could not retrieve historical data for {symbol}.")
    return pd.DataFrame()

# User Authentication
def authenticate(username, password, user_data):
    if username in user_data and user_data[username]["password"] == password:
        st.session_state.user_logged_in = True
        st.session_state.username = username
        st.session_state.portfolio = user_data[username].get("portfolio", {})
        st.session_state.transactions = user_data[username].get("transactions", [])
        st.session_state.watchlist = user_data[username].get("watchlist", {})
        return True
    return False

# Sign Up function
def sign_up(username, password, user_data):
    if username not in user_data:
        user_data[username] = {
            "password": password,
            "portfolio": {},
            "transactions": [],
            "watchlist": {}
        }
        save_user_data(user_data)
        st.success("Account created successfully! Please log in.")
        return True
    st.error("Username already exists.")
    return False

# Add stock to portfolio
def add_stock(symbol, shares, user_data):
    price = fetch_stock_price(symbol)
    if price is not None:
        if symbol in st.session_state.portfolio:
            st.session_state.portfolio[symbol]["shares"] += shares
            st.session_state.portfolio[symbol]["cost_basis"] += price * shares
        else:
            st.session_state.portfolio[symbol] = {"shares": shares, "price": price, "cost_basis": price * shares}
        st.session_state.transactions.append({
            "type": "buy", "symbol": symbol, "shares": shares, "price": price, "date": datetime.now().isoformat()
        })
        user_data[st.session_state.username]["portfolio"] = st.session_state.portfolio
        user_data[st.session_state.username]["transactions"] = st.session_state.transactions
        save_user_data(user_data)
        st.success(f"Added {shares} shares of {symbol} at ${price:.2f} each.")
    else:
        st.error("Failed to add stock due to data retrieval issues.")

# Remove stock from the portfolio
def remove_stock(symbol, shares, user_data):
    if symbol not in st.session_state.portfolio:
        st.error(f"{symbol} is not in your portfolio.")
    else:
        current_shares = st.session_state.portfolio[symbol]["shares"]
        if shares > current_shares:
            st.error(f"You cannot sell more shares ({shares}) than you own ({current_shares}).")
        else:
            price = fetch_stock_price(symbol)
            if price is not None:
                st.session_state.portfolio[symbol]["shares"] -= shares
                st.session_state.portfolio[symbol]["cost_basis"] -= st.session_state.portfolio[symbol]["price"] * shares

                if st.session_state.portfolio[symbol]["shares"] == 0:
                    del st.session_state.portfolio[symbol]

                st.session_state.transactions.append({
                    "type": "sell", "symbol": symbol, "shares": shares, "price": price, "date": datetime.now().isoformat()
                })

                user_data[st.session_state.username]["portfolio"] = st.session_state.portfolio
                user_data[st.session_state.username]["transactions"] = st.session_state.transactions
                save_user_data(user_data)

                st.metric(label=f"Removed from Portfolio", value=f"{symbol} Sold")
                st.success(f"Sold {shares} shares of {symbol} at ${price:.2f}.")
            else:
                st.error(f"Failed to fetch the current price for {symbol}.")


def add_to_watchlist(symbol, user_data):
    if symbol in st.session_state.watchlist:
        st.warning(f"{symbol} is already in your watchlist.")
    else:
        with st.spinner("Adding stock to watchlist..."):
            price = fetch_stock_price(symbol)
            if price is not None:
                st.session_state.watchlist[symbol] = {"price": price}
                user_data[st.session_state.username]["watchlist"] = st.session_state.watchlist
                save_user_data(user_data)
                st.success(f"Added {symbol} to your watchlist at ${price:.2f}.")
            else:
                st.error(f"Failed to fetch the current price for {symbol}.")



def portfolio_overview():
    st.subheader(f"Hello, {st.session_state.username}! Here's your portfolio overview:")

    # Calculate portfolio metrics
    total_value = sum(details["shares"] * st.session_state.real_time_prices.get(symbol, details["price"])
                      for symbol, details in st.session_state.portfolio.items())
    total_cost = sum(details["cost_basis"] for details in st.session_state.portfolio.values())
    total_gain_loss = total_value - total_cost
    gain_loss_percentage = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0

    # Metrics section
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Portfolio Value", value=f"${total_value:,.2f}")
    col2.metric(label="Total Cost", value=f"${total_cost:,.2f}")
    col3.metric(label="Gain/Loss", value=f"${total_gain_loss:,.2f}", delta=f"{gain_loss_percentage:.2f}%")

    # Portfolio details
    if st.session_state.portfolio:
        st.subheader("Portfolio Details")

        # Create a DataFrame for portfolio details
        portfolio_df = pd.DataFrame.from_dict(st.session_state.portfolio, orient="index")
        portfolio_df["Current Price"] = [
            st.session_state.real_time_prices.get(symbol, details["price"]) for symbol, details in st.session_state.portfolio.items()
        ]
        portfolio_df["Total Value"] = portfolio_df["shares"] * portfolio_df["Current Price"]
        portfolio_df["Gain/Loss"] = portfolio_df["Total Value"] - portfolio_df["cost_basis"]

        # Display enhanced DataFrame with sorting and filtering
        st.dataframe(portfolio_df[["shares", "Current Price", "cost_basis", "Total Value", "Gain/Loss"]],
                     use_container_width=True)

        # Plotly interactive pie chart for portfolio allocation
        import plotly.express as px
        fig = px.pie(portfolio_df, names=portfolio_df.index, values="Total Value",
                     title="Portfolio Allocation by Stock", hole=0.3)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Your portfolio is empty. Start adding stocks to see details!")



def real_time_stock_overview(symbol):
    st.subheader(f"Real-Time Stock Overview and Market News for {symbol}")

    # Fetch historical data for visualization
    data = fetch_stock_history(symbol)
    if data.empty:
        st.error("Could not retrieve historical data.")
        return

    # Convert 'Date' column to matplotlib date format
    data['Date'] = pd.to_datetime(data['Date'])  # Ensure 'Date' is in datetime format
    data['Date'] = mdates.date2num(data['Date'])  # Convert to numeric format for candlestick_ohlc

    # Calculate Daily Returns
    data["Daily Return"] = data["Close"].pct_change().dropna() * 100  # Percentage daily return

    # Tabs for visualizations and news
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Line Chart", 
        "🕯️ Candlestick Chart", 
        "📊 Daily Returns Histogram", 
        "📰 Latest News"
    ])

    # Tab 1: Line Chart
    with tab1:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(data["Date"], data["Close"], color="blue", label="Closing Price")
        ax.set_title(f"Closing Prices for {symbol}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price ($)")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.tick_params(axis='x', rotation=45)
        st.pyplot(fig)

    # Tab 2: Candlestick Chart
    with tab2:
        fig, ax = plt.subplots(figsize=(12, 6))
        candlestick_ohlc(ax, data[["Date", "Open", "High", "Low", "Close"]].values,
                         width=0.6, colorup="green", colordown="red")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.set_title(f"Candlestick Chart for {symbol}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price ($)")
        ax.tick_params(axis='x', rotation=45)
        st.pyplot(fig)

    # Tab 3: Histogram of Daily Returns
    with tab3:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.histplot(data["Daily Return"], bins=20, kde=True, color="#ff6347", ax=ax)
        ax.set_title(f"Daily Returns Histogram for {symbol}")
        ax.set_xlabel("Daily Return (%)")
        ax.set_ylabel("Frequency")
        st.pyplot(fig)

    # Tab 4: Latest News
    with tab4:
        st.markdown(f"### 📰 Latest News About {symbol}")
        news_articles = fetch_latest_news(symbol)
        if news_articles:
            for article in news_articles[:5]:  # Display top 5 articles
                st.markdown(f"#### {article['title']}")
                st.write(f"Published on: {article['publishedAt']} | Source: {article['source']['name']}")
                st.write(article["description"])
                st.markdown(f"[Read More]({article['url']})", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No recent news articles found.")




# Fetch latest news using the News API
def fetch_latest_news(symbol):
    try:
        url = f"https://newsapi.org/v2/everything?q={symbol}&sortBy=publishedAt&apiKey={"1546917503f04be98ee78776888b78f2"}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('articles', [])
        else:
            st.error(f"Failed to fetch news for {symbol}. Error code: {response.status_code}")
    except Exception as e:
        st.error(f"Error fetching news: {e}")
    return []



# Display Welcome Page for Login Page
def display_welcome_page():
    # Welcome Section
    st.markdown("""
        <div style="text-align: center; margin-top: 50px;">
            <h2>Welcome to Stock Portfolio Tracker</h2>
            <p>Your all-in-one tool to monitor, manage, and analyze your investments.</p>
            <p>Stay ahead with real-time insights, portfolio management, and trending stock updates.</p>
        </div>
    """, unsafe_allow_html=True)

    # Create columns for highlights
    col1, col2, col3 = st.columns(3)

    # Trending Stock Symbols
    with col1:
        st.subheader("🔥 Trending Stocks")
        trending_stocks = ["AAPL", "TSLA", "AMZN", "META", "GOOGL"]  # Example list; use API for live data
        for stock in trending_stocks:
            st.markdown(f"- {stock}")

    # Most Bought Stock of the Day
    with col2:
        st.subheader("💰 Most Bought Stock")
        # Fetch from API
        most_bought = {"symbol": "TSLA", "price": 750.25, "volume": "1.2M"}
        st.metric(label=most_bought["symbol"], value=f"${most_bought['price']}", delta=f"Volume: {most_bought['volume']}")

    # Highest Price Stock of the Day
    with col3:
        st.subheader("📌 Highest Price Stock")
        # Fetch from API
        highest_price_stock = {"symbol": "AMZN", "price": 3520.67, "volume": "2.5M"}
        st.metric(label=highest_price_stock["symbol"], value=f"${highest_price_stock['price']}")

    st.markdown("---")

    # Display Recent Market Trends
    st.subheader("📊 Recent Market Trends")
    col1, col2 = st.columns(2)

    with col1:
        st.write("### Top Gainers")
        # Example gainers; replace with API call
        top_gainers = [
            {"symbol": "AAPL", "change": "+2.5%"},
            {"symbol": "TSLA", "change": "+3.1%"},
            {"symbol": "MSFT", "change": "+1.8%"},
        ]
        for gainer in top_gainers:
            st.markdown(f"- {gainer['symbol']} {gainer['change']}")

    with col2:
        st.write("### Top Losers")
        # Example losers; replace with API call
        top_losers = [
            {"symbol": "NFLX", "change": "-1.7%"},
            {"symbol": "BABA", "change": "-2.4%"},
            {"symbol": "NIO", "change": "-1.9%"},
        ]
        for loser in top_losers:
            st.markdown(f"- {loser['symbol']} {loser['change']}")

    st.markdown("---")

    # Market Summary Chart Placeholder (Integrate with API for live data)
    st.write("### 📉 S&P 500 Performance")
    st.line_chart([4000, 4050, 4020, 4100, 4120])  # Replace with real data from API

# Main App
def main():
    
    user_data = load_user_data()

    st.title("📈 Stock Portfolio Tracker")
    
    
    # Sidebar setup
    if not st.session_state.user_logged_in:
        page = st.sidebar.radio("Explore", ["Login", "Sign Up"], index=0)
    else:

        st.sidebar.markdown(f"Welcome, {st.session_state.username}!")
        
        page = st.sidebar.radio(
            "Features",
            ["Portfolio Overview", "Add Stock", "Remove Stock", "Watchlist", "Transaction History", "Real-Time Stock Overview"],
            index=0,
            format_func=lambda x: f"🔹 {x}" if x == "Portfolio Overview" else f"🔸 {x}"
        )
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            initialize_session_state()
            st.info("You have been logged out. See you next time!")
            return
    
    
    # Main content
    if st.session_state.user_logged_in:
        if page == "Portfolio Overview":
            portfolio_overview()

        elif page == "Add Stock":
            st.header("Add Stock to Your Portfolio")
            symbol = st.text_input("Enter Stock Symbol (e.g., AAPL)").upper()
            shares = st.number_input("Enter Number of Shares", min_value=1, step=1)
            if st.button("Add Stock"):
                add_stock(symbol, shares, user_data)
        
        elif page == "Remove Stock":
            st.header("🛒 Remove Stock from Portfolio")
            symbol = st.text_input("Enter Stock Symbol to Sell (e.g., AAPL)").upper()
            shares = st.number_input("Enter Number of Shares to Sell", min_value=1, step=1)
            if st.button("Remove Stock"):
                remove_stock(symbol, shares, user_data)

        elif page == "Watchlist":
            st.header("📋 Manage Your Watchlist")
            symbol = st.text_input("Add Stock to Watchlist (Symbol)").upper()
            if st.button("Add to Watchlist"):
                add_to_watchlist(symbol, user_data)
            if st.session_state.watchlist:
                st.subheader("Current Watchlist")
                watchlist_df = pd.DataFrame.from_dict(st.session_state.watchlist, orient="index")
                watchlist_df.columns = ["Price"]
                st.dataframe(watchlist_df, use_container_width=True)
            else:
                st.info("Your watchlist is empty. Add stocks to track!")

        elif page == "Transaction History":
            st.header("📜 Transaction History")
            if st.session_state.transactions:
                transactions_df = pd.DataFrame(st.session_state.transactions)
                transactions_df["date"] = pd.to_datetime(transactions_df["date"])
                st.dataframe(transactions_df[["date", "type", "symbol", "shares", "price"]], use_container_width=True)
            else:
                st.warning("No transactions to display yet!")

        elif page == "Real-Time Stock Overview":
            st.header("Real-Time Stock Overview")
            symbol = st.text_input("Enter Stock Symbol for Real-Time Overview (e.g., AAPL)").upper()
            if st.button("Show Overview"):
                real_time_stock_overview(symbol)
    else:
        if page == "Login":
            st.sidebar.subheader("Login to Your Account")
            username = st.sidebar.text_input("Username")
            password = st.sidebar.text_input("Password", type="password")
            if st.sidebar.button("Login"):
                if authenticate(username, password, user_data):
                    st.session_state.user_logged_in = True
                    st.session_state.username = username
                    threading.Thread(target=fetch_real_time_prices, daemon=True).start()
                else:
                    st.sidebar.error("Invalid username or password.")
            display_welcome_page()

        elif page == "Sign Up":
            st.sidebar.subheader("Create an Account")
            new_username = st.sidebar.text_input("New Username")
            new_password = st.sidebar.text_input("New Password", type="password")
            if st.sidebar.button("Sign Up"):
                if sign_up(new_username, new_password, user_data):
                    st.success("Account created successfully! Please log in.")
                else:
                    st.error("Username already exists.")
            display_welcome_page()




# Run the app
if __name__ == "__main__":
    initialize_session_state()
    main()
