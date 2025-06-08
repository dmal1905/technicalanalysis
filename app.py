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

# Page Configuration
st.set_page_config(
    page_title="Stock Screener Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
    <style>
    /* Main container styling */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Header styling */
    .header {
        background: linear-gradient(90deg, #1a237e, #0d47a1);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    /* Card styling */
    .card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(90deg, #1a237e, #0d47a1);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Exchange toggle styling */
    .exchange-toggle {
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .exchange-toggle button {
        background: white;
        border: 2px solid #1a237e;
        color: #1a237e;
        padding: 0.5rem 1.5rem;
        border-radius: 25px;
        transition: all 0.3s ease;
    }
    
    .exchange-toggle button.active {
        background: #1a237e;
        color: white;
    }
    
    /* Table styling */
    .dataframe {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
    }
    
    .dataframe th {
        background-color: #1a237e;
        color: white;
        padding: 0.75rem;
    }
    
    .dataframe td {
        padding: 0.75rem;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .dataframe tr:hover {
        background-color: #f5f5f5;
    }
    
    /* Alert styling */
    .stAlert {
        border-radius: 10px;
        padding: 1rem;
    }
    
    /* Selectbox styling */
    .stSelectbox {
        background-color: white;
    }
    
    /* Progress bar styling */
    .stProgress > div > div {
        background-color: #1a237e;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_exchange' not in st.session_state:
    st.session_state.selected_exchange = 'NSE'

# Header
st.markdown("""
    <div class="header">
        <h1 style="text-align: center; margin: 0;">📈 Stock Screener Pro</h1>
        <p style="text-align: center; margin: 0;">Advanced Technical Analysis for NSE & BSE</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🔐 Authentication")
    user_id, api_key = load_credentials()
    
    if not user_id or not api_key:
        st.markdown("#### Enter AliceBlue API Credentials")
        new_user_id = st.text_input("User ID", type="password")
        new_api_key = st.text_input("API Key", type="password")
        if st.button("Login", use_container_width=True):
            save_credentials(new_user_id, new_api_key)
            st.success("API credentials saved! Refreshing...")
            st.rerun()
    
    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("""
        This screener uses advanced technical analysis to identify potential trading opportunities.
        Please conduct your own due diligence before making any trading decisions.
    """)
    
    st.markdown("---")
    st.markdown("### 🛠️ Settings")
    st.markdown("Select your preferred exchange and stock list to begin screening.")

# Main Content
tabs = st.tabs(["📊 Stock Screener", "🛠️ Advanced Tools", "📈 Market Overview"])

with tabs[0]:
    # Exchange Selection
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

    # Current Exchange Display
    st.markdown(f"""
        <div class="card">
            <h2 style="text-align: center; color: #1a237e;">
                {st.session_state.selected_exchange} Stock Screener
            </h2>
        </div>
    """, unsafe_allow_html=True)

    # Initialize AliceBlue
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
            st.markdown(f"""
                <div class="card">
                    <h3 style="color: #1a237e;">{title}</h3>
                </div>
            """, unsafe_allow_html=True)
            
            if "Name" in df.columns:
                df["Name"] = df["Name"].apply(
                    lambda x: generate_tradingview_link(x, st.session_state.selected_exchange)
                )
            st.markdown(df.to_html(escape=False), unsafe_allow_html=True)

    # Stock Selection and Strategy
    col1, col2 = st.columns(2)
    
    with col1:
        selected_list = st.selectbox(
            "Select Stock List:",
            list(STOCK_LISTS.keys()),
            help="Choose a predefined list of stocks to analyze"
        )
    
    with col2:
        strategy = st.selectbox(
            "Select Strategy:",
            [
                "EMA, RSI & Support Zone (Buy)",
                "EMA, RSI & Resistance Zone (Sell)"
            ],
            help="Choose a technical analysis strategy"
        )

    # Start Screening Button
    if st.button("Start Screening", use_container_width=True):
        tokens = STOCK_LISTS.get(selected_list, [])
        if not tokens:
            st.warning(f"No stocks found for {selected_list}.")
        else:
            with st.spinner("Fetching and analyzing stocks..."):
                screened_stocks = fetch_screened_stocks(tokens, strategy)
            df = clean_and_display_data(screened_stocks, strategy)
            safe_display(df, strategy)

with tabs[1]:
    st.markdown("""
        <div class="card">
            <h2 style="color: #1a237e;">Advanced Technical Analysis Tools</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("RSI Checker for a Stock")
    col1, col2 = st.columns(2)
    
    with col1:
        stock_symbol = st.text_input(
            f"Enter {st.session_state.selected_exchange} Stock Symbol",
            help="Example: RELIANCE"
        )
    
    with col2:
        date = st.date_input(
            "Select Date",
            value=datetime.date.today(),
            help="Choose a date for RSI analysis"
        )

    if st.button("Check RSI", use_container_width=True):
        st.info(f"Feature coming soon: RSI lookup for {stock_symbol} on {date}")

with tabs[2]:
    st.markdown("""
        <div class="card">
            <h2 style="color: #1a237e;">Market Overview</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.info("Market overview features coming soon!")
    st.markdown("""
        Future features will include:
        - Market breadth indicators
        - Sector performance analysis
        - Top gainers and losers
        - Volume analysis
    """) 
