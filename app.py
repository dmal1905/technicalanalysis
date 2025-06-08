import streamlit as st
import pandas as pd
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from alice_client import initialize_alice, save_credentials, load_credentials
from stock_analysis import (
    analyze_all_tokens_bullish,
    analyze_all_tokens_bearish
)
from stock_lists import STOCK_LISTS
from utils import generate_tradingview_link

st.set_page_config(page_title="Stock Screener", layout="wide")

# Initialize session state for exchange selection if not exists
if 'selected_exchange' not in st.session_state:
    st.session_state.selected_exchange = 'NSE'

# Custom CSS for the exchange toggle
st.markdown("""
    <style>
    .exchange-toggle {
        display: flex;
        justify-content: center;
        margin: 20px 0;
    }
    .exchange-toggle button {
        padding: 10px 20px;
        margin: 0 5px;
        border: 2px solid #4CAF50;
        background-color: white;
        color: #4CAF50;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .exchange-toggle button.active {
        background-color: #4CAF50;
        color: white;
    }
    .exchange-toggle button:hover {
        background-color: #45a049;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

tabs = st.tabs(["📊 Stock Screener", "🛠️ Advanced Tools"])

with tabs[0]:
    st.warning("This screener is based on statistical analysis. Please conduct your own due diligence before making any trading decisions. This application is best compatible with **Google Chrome**.")

    # Exchange Selection with custom toggle buttons
    st.markdown('<div class="exchange-toggle">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("NSE", key="nse_btn", 
                    help="Switch to NSE stocks",
                    use_container_width=True,
                    type="primary" if st.session_state.selected_exchange == 'NSE' else "secondary"):
            st.session_state.selected_exchange = 'NSE'
            st.rerun()
    
    with col2:
        if st.button("BSE", key="bse_btn",
                    help="Switch to BSE stocks",
                    use_container_width=True,
                    type="primary" if st.session_state.selected_exchange == 'BSE' else "secondary"):
            st.session_state.selected_exchange = 'BSE'
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Display current exchange
    st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>{st.session_state.selected_exchange} Stock Screener</h2>", unsafe_allow_html=True)

    # Try loading stored credentials
    user_id, api_key = load_credentials()

    if not user_id or not api_key:
        st.title("Admin Login - Enter AliceBlue API Credentials")
        new_user_id = st.text_input("Enter User ID", type="password")  # Hide input
        new_api_key = st.text_input("Enter API Key", type="password")  # Hide input
        if st.button("Login"):
            save_credentials(new_user_id, new_api_key)
            st.success("API credentials saved! Refreshing...")
            st.rerun()

    try:
        alice = initialize_alice()
    except Exception as e:
        st.error(f"Failed to initialize AliceBlue API: {e}")
        alice = None

    @st.cache_data(ttl=300)
    def fetch_screened_stocks(tokens, strategy):
        """Fetch and analyze stocks based on selected strategy."""
        try:
            if not alice:
                raise Exception("AliceBlue API is not initialized.")
            
            if strategy == "EMA, RSI & Support Zone (Buy)":
                return analyze_all_tokens_bullish(alice, tokens, exchange=st.session_state.selected_exchange)

            elif strategy == "EMA, RSI & Resistance Zone (Sell)":
                return analyze_all_tokens_bearish(alice, tokens, exchange=st.session_state.selected_exchange)
        except Exception as e:
            st.error(f"Error fetching stock data: {e}")
            return []

    def clean_and_display_data(data, strategy):
        """Clean and convert the data into a DataFrame based on the strategy."""
        if not data or not isinstance(data, list):
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        if strategy == "EMA, RSI & Support Zone (Buy)":
            df["Close"] = df["Close"].astype(float).round(2)
            df["Support"] = df["Support"].astype(float).round(2)
            df["Distance_pct"] = df["Distance_pct"].astype(float).round(2)
            df["RSI"] = df["RSI"].astype(float).round(2)
        elif strategy == "EMA, RSI & Resistance Zone (Sell)":
            df["Close"] = df["Close"].astype(float).round(2)
            df["Resistance"] = df["Resistance"].astype(float).round(2)
            df["Distance_pct"] = df["Distance_pct"].astype(float).round(2)
            df["RSI"] = df["RSI"].astype(float).round(2)

        if "Strength" in df.columns:
            df = df.sort_values(by="Strength", ascending=False)
        
        return df

    def safe_display(df, title):
        """Displays the stock data with clickable TradingView links."""
        if df.empty:
            st.warning(f"No stocks found for {title}")
        else:
            st.markdown(f"## {title}")
            if "Name" in df.columns:
                df["Name"] = df["Name"].apply(
                    lambda x: generate_tradingview_link(x, st.session_state.selected_exchange)
                )
            st.markdown(df.to_html(escape=False), unsafe_allow_html=True)

    st.markdown("""
        <style>
            table { width: 100% !important; }
            th, td { padding: 10px !important; text-align: left !important; }
            td:nth-child(1) { min-width: 200px !important; }
            a { white-space: nowrap; }
        </style>
    """, unsafe_allow_html=True)

    selected_list = st.selectbox("Select Stock List:", list(STOCK_LISTS.keys()))
    strategy = st.selectbox(
        "Select Strategy:", 
        [
            "EMA, RSI & Support Zone (Buy)",
            "EMA, RSI & Resistance Zone (Sell)"
        ]
    )

    if st.button("Start Screening"):
        tokens = STOCK_LISTS.get(selected_list, [])
        if not tokens:
            st.warning(f"No stocks found for {selected_list}.")
        else:
            with st.spinner("Fetching and analyzing stocks..."):
                screened_stocks = fetch_screened_stocks(tokens, strategy)
            df = clean_and_display_data(screened_stocks, strategy)
            safe_display(df, strategy)

with tabs[1]:
    st.header("🛠️ Advanced Features (Experimental)")

    st.subheader("RSI Checker for a Stock")
    stock_symbol = st.text_input(f"Enter {st.session_state.selected_exchange} Stock Symbol (e.g., RELIANCE)")
    date = st.date_input("Pick a date", value=datetime.date.today())

    if st.button("Check RSI"):
        st.info(f"Feature coming soon: RSI lookup for {stock_symbol} on {date}")
        # Placeholder for future implementation
        # result = get_rsi_for_stock(stock_symbol, date)
        # st.write(result) 