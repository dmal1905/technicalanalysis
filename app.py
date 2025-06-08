import streamlit as st
import pandas as pd
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool, cpu_count
from functools import partial
from alice_client import initialize_alice, save_credentials, load_credentials
from advanced_analysis import (
    analyze_all_tokens_advanced,
    analyze_all_tokens_custom
)
from stock_lists import STOCK_LISTS
from utils import generate_tradingview_link

# Page Configuration
st.set_page_config(
    page_title="Stock Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Set theme configuration
st.markdown("""
    <style>
        /* Override Streamlit's default theme */
        .stButton>button {
            background-color: #2563eb !important;
        }
        .stButton>button:hover {
            background-color: #1d4ed8 !important;
        }
        .stProgress > div > div {
            background-color: #2563eb !important;
        }
        .stSelectbox > div > div {
            background-color: #2563eb !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        .stTabs [data-baseweb="tab"] {
            height: 4rem;
            white-space: pre-wrap;
            background-color: #2563eb !important;
            border-radius: 4px 4px 0 0;
            gap: 1rem;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1d4ed8 !important;
        }
        table { width: 100% !important; }
        th, td { padding: 10px !important; text-align: left !important; }
        td:nth-child(1) { min-width: 200px !important; }
        a { white-space: nowrap; }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_exchange' not in st.session_state:
    st.session_state.selected_exchange = 'NSE'

def get_stock_lists_for_exchange(exchange):
    """Filter stock lists based on the selected exchange."""
    if exchange == 'NSE':
        return {k: v for k, v in STOCK_LISTS.items() if k in [
            'NIFTY FNO', 'NIFTY 50', 'NIFTY 200', 'NIFTY 500', 'ALL STOCKS'
        ]}
    else:  # BSE
        return {k: v for k, v in STOCK_LISTS.items() if k in [
            'BSE 500', 'BSE Large Cap Index', 'BSE Mid Cap Index', 
            'BSE Small Cap Index', 'BSE 400 MidSmallCap', 
            'BSE 250 LargeMidCap', 'BSE ALL STOCKS'
        ]}

# Header
st.markdown("""
    <div class="header">
        <h1>Stock Screener</h1>
        <p>Advanced Technical Analysis for NSE & BSE</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### Authentication")
    user_id, api_key = load_credentials()
    
    if not user_id or not api_key:
        st.markdown("Enter AliceBlue API Credentials")
        new_user_id = st.text_input("User ID", type="password")
        new_api_key = st.text_input("API Key", type="password")
        if st.button("Login", use_container_width=True):
            save_credentials(new_user_id, new_api_key)
            st.success("Credentials saved!")
            st.rerun()
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
        This screener uses technical analysis to identify potential trading opportunities.
        Please conduct your own due diligence before making any trading decisions.
    """)

# Main Content
tabs = st.tabs(["Stock Screener"])

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
            
            return analyze_all_tokens_advanced(alice, tokens, strategy, exchange=st.session_state.selected_exchange)
        except Exception as e:
            st.error(f"Error fetching stock data: {e}")
            return []

    def clean_and_display_data(data, strategy):
        """Clean and convert the data into a DataFrame based on the strategy."""
        if not data or not isinstance(data, list):
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Convert numeric columns
        df["Close"] = df["Close"].astype(float).round(2)
        df["Strength"] = df["Strength"].astype(float).round(2)
        
        if strategy == "Custom Price Movement":
            df["Start_Price"] = df["Start_Price"].astype(float).round(2)
            df["Percentage_Change"] = df["Percentage_Change"].astype(float).round(2)
            df["Volatility"] = df["Volatility"].astype(float).round(2)
        else:
            df["Volume"] = df["Volume"].astype(float).round(2)
            df["Patterns"] = df["Patterns"].apply(lambda x: ", ".join(x) if x else "None")
            df["Volume_Nodes"] = df["Volume_Nodes"].apply(lambda x: ", ".join(map(str, x[:3])) if x else "None")
        
        # Sort by strength
        df = df.sort_values(by="Strength", ascending=False)
        
        return df

    def safe_display(df, title):
        """Displays the stock data with clickable TradingView links."""
        if df.empty:
            st.warning(f"No stocks found for {title}")
        else:
            st.markdown(f"### {title}")
            if "Name" in df.columns:
                df["Name"] = df["Name"].apply(
                    lambda x: generate_tradingview_link(x, st.session_state.selected_exchange)
                )
            st.markdown(df.to_html(escape=False), unsafe_allow_html=True)

    # Stock Selection and Strategy
    col1, col2 = st.columns(2)
    
    with col1:
        available_lists = get_stock_lists_for_exchange(st.session_state.selected_exchange)
        selected_list = st.selectbox(
            "Select Stock List",
            list(available_lists.keys()),
            help="Choose a list of stocks to analyze"
        )
    
    with col2:
        strategy = st.selectbox(
            "Select Strategy",
            [
                "Price Action Breakout",
                "Volume Profile Analysis",
                "Market Structure Analysis",
                "Multi-Factor Analysis",
                "Custom Price Movement"
            ],
            help="Choose a technical analysis strategy"
        )

    # Strategy descriptions
    strategy_descriptions = {
        "Price Action Breakout": """
            - Identifies strong breakouts with volume confirmation
            - Analyzes candlestick patterns and price action
            - Considers multiple timeframe confirmation
            - Includes volume profile analysis
        """,
        "Volume Profile Analysis": """
            - Identifies high-volume price levels
            - Analyzes volume distribution
            - Detects institutional buying/selling
            - Includes volume-weighted price levels
        """,
        "Market Structure Analysis": """
            - Analyzes market structure (HH/HL vs LH/LL)
            - Identifies trend strength and direction
            - Includes multiple timeframe analysis
            - Considers market regime (trending vs ranging)
        """,
        "Multi-Factor Analysis": """
            - Combines price action, volume, and market structure
            - Includes relative strength analysis
            - Considers sector rotation
            - Integrates market breadth indicators
        """,
        "Custom Price Movement": """
            - Customizable price movement analysis
            - Set your own duration and percentage targets
            - Track stocks moving up or down by your specified amount
            - Includes volume trend and volatility analysis
        """
    }

    # Display strategy description
    st.markdown("### Strategy Details")
    st.markdown(strategy_descriptions[strategy])

    # Custom strategy parameters
    if strategy == "Custom Price Movement":
        col1, col2, col3 = st.columns(3)
        with col1:
            duration_days = st.number_input(
                "Duration (Days)",
                min_value=1,
                max_value=365,
                value=30,
                help="Number of days to look back"
            )
        with col2:
            target_percentage = st.number_input(
                "Target Percentage",
                min_value=0.1,
                max_value=1000.0,
                value=10.0,
                step=0.1,
                help="Target percentage change"
            )
        with col3:
            direction = st.selectbox(
                "Direction",
                ["up", "down"],
                help="Price movement direction"
            )

    # Start Screening Button
    if st.button("Start Screening", use_container_width=True):
        available_lists = get_stock_lists_for_exchange(st.session_state.selected_exchange)
        tokens = available_lists.get(selected_list, [])
        if not tokens:
            st.warning(f"No stocks found for {selected_list}.")
        else:
            with st.spinner("Analyzing stocks..."):
                if strategy == "Custom Price Movement":
                    screened_stocks = analyze_all_tokens_custom(
                        alice, 
                        tokens, 
                        duration_days, 
                        target_percentage, 
                        direction, 
                        exchange=st.session_state.selected_exchange
                    )
                else:
                    screened_stocks = analyze_all_tokens_advanced(
                        alice, 
                        tokens, 
                        strategy, 
                        exchange=st.session_state.selected_exchange
                    )
            df = clean_and_display_data(screened_stocks, strategy)
            safe_display(df, strategy)

def process_stock_chunk(chunk_data):
    """Process a chunk of stocks using multiprocessing."""
    alice, tokens, strategy, exchange = chunk_data
    results = []
    for token in tokens:
        try:
            result = analyze_stock(alice, token, strategy, exchange)
            if result:
                results.append(result)
        except Exception as e:
            print(f"Error analyzing stock {token}: {str(e)}")
            continue
    return results

def screen_stocks():
    """Screen stocks based on selected criteria."""
    try:
        # Get selected stock list
        selected_list = st.session_state.selected_list
        if not selected_list:
            st.error("Please select a stock list")
            return

        # Get tokens for selected list
        tokens = STOCK_LISTS[selected_list]
        
        # Create progress bar and status
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Starting stock analysis...")
        
        # Calculate chunks for multiprocessing
        num_processes = cpu_count() - 1  # Leave one CPU free
        chunk_size = 200
        chunks = [tokens[i:i + chunk_size] for i in range(0, len(tokens), chunk_size)]
        total_chunks = len(chunks)
        
        # Prepare data for multiprocessing
        chunk_data = [(alice, chunk, st.session_state.selected_strategy, st.session_state.selected_exchange) 
                     for chunk in chunks]
        
        # Process chunks using multiprocessing
        results = []
        with Pool(processes=num_processes) as pool:
            for i, chunk_results in enumerate(pool.imap_unordered(process_stock_chunk, chunk_data)):
                # Update progress
                progress = (i + 1) / total_chunks
                progress_bar.progress(progress)
                status_text.text(f"Processing chunk {i + 1} of {total_chunks}...")
                
                # Extend results
                results.extend(chunk_results)
                status_text.text(f"Found {len(results)} matches so far...")
        
        # Complete progress
        progress_bar.progress(1.0)
        status_text.text(f"Analysis complete! Found {len(results)} matches.")
        
        if results:
            # Convert results to DataFrame
            df = pd.DataFrame(results)
            
            # Clean and display data
            df = clean_and_display_data(df)
            
            # Show results
            st.dataframe(df, use_container_width=True)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                "Download Results",
                csv,
                "stock_screener_results.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.info("No stocks found matching the criteria.")
            
    except Exception as e:
        st.error(f"Error during stock screening: {str(e)}")
        progress_bar.empty()
        status_text.empty()

def analyze_stock_batch(alice, tokens, strategy, exchange):
    """Analyze a batch of stocks in parallel using multiprocessing."""
    num_processes = cpu_count() - 1  # Leave one CPU free
    chunk_size = len(tokens) // num_processes + 1
    chunks = [tokens[i:i + chunk_size] for i in range(0, len(tokens), chunk_size)]
    
    # Prepare data for multiprocessing
    chunk_data = [(alice, chunk, strategy, exchange) for chunk in chunks]
    
    results = []
    with Pool(processes=num_processes) as pool:
        chunk_results = pool.map(process_stock_chunk, chunk_data)
        for chunk_result in chunk_results:
            results.extend(chunk_result)
    
    return results

def clean_and_display_data(df):
    """Clean and format the data for display."""
    try:
        # Convert numeric columns
        numeric_cols = ['Close', 'Support', 'Resistance', 'Distance_pct', 'RSI']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Format percentages
        if 'Distance_pct' in df.columns:
            df['Distance_pct'] = df['Distance_pct'].map('{:.2f}%'.format)
        
        # Format RSI
        if 'RSI' in df.columns:
            df['RSI'] = df['RSI'].map('{:.2f}'.format)
        
        # Sort by relevant columns
        sort_cols = ['Distance_pct', 'RSI']
        sort_cols = [col for col in sort_cols if col in df.columns]
        if sort_cols:
            df = df.sort_values(by=sort_cols)
        
        return df
        
    except Exception as e:
        st.error(f"Error cleaning data: {str(e)}")
        return df 
