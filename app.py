import streamlit as st
import pandas as pd
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    initial_sidebar_state="expanded"
)

# Custom CSS with clean, minimal theme
st.markdown("""
    <style>
    /* Clean, minimal theme colors */
    :root {
        --bg: #ffffff;
        --bg-secondary: #f0f2f6;
        --text-primary: #262730;
        --text-secondary: #4b5563;
        --border: #e5e7eb;
        --accent: #4b5563;
        --accent-hover: #6b7280;
        --card-bg: #ffffff;
        --hover: #f8fafc;
        --success: #059669;
        --warning: #d97706;
        --error: #dc2626;
    }
    
    /* Override Streamlit's default theme */
    .stApp {
        background-color: var(--bg) !important;
        color: var(--text-primary) !important;
    }
    
    /* Main container styling */
    .main {
        background-color: var(--bg) !important;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header styling */
    .header {
        background-color: var(--bg) !important;
        color: var(--text-primary) !important;
        padding: 2rem 0;
        margin-bottom: 2rem;
        text-align: center;
        border-bottom: 1px solid var(--border);
    }
    
    .header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: var(--text-primary);
    }
    
    .header p {
        font-size: 1.1rem;
        color: var(--text-secondary);
    }
    
    /* Card styling */
    .card {
        background-color: var(--card-bg) !important;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid var(--border);
        margin-bottom: 1rem;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: var(--accent) !important;
        color: white !important;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 0.25rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        background-color: var(--accent-hover) !important;
    }
    
    /* Exchange toggle styling */
    .exchange-toggle {
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .exchange-toggle button {
        background: var(--bg) !important;
        border: 1px solid var(--accent) !important;
        color: var(--accent) !important;
        padding: 0.75rem 1.5rem;
        border-radius: 0.25rem;
        font-weight: 500;
    }
    
    .exchange-toggle button.active {
        background: var(--accent) !important;
        color: white !important;
    }
    
    /* Table styling */
    .dataframe {
        width: 100% !important;
        border-collapse: separate;
        border-spacing: 0;
        margin: 1rem 0;
        font-size: 0.9rem;
        background-color: var(--card-bg) !important;
        color: var(--text-primary) !important;
        border-radius: 0.25rem;
        overflow: hidden;
    }
    
    .dataframe th {
        background-color: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        padding: 10px !important;
        font-weight: 600;
        border-bottom: 1px solid var(--border);
        text-align: left !important;
    }
    
    .dataframe td {
        padding: 10px !important;
        border-bottom: 1px solid var(--border);
        color: var(--text-secondary) !important;
        text-align: left !important;
    }
    
    .dataframe td:nth-child(1) {
        min-width: 200px !important;
    }
    
    .dataframe tr:hover {
        background-color: var(--hover) !important;
    }
    
    /* Alert styling */
    .stAlert {
        border-radius: 0.25rem;
        padding: 1rem;
        background-color: var(--card-bg) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border);
    }
    
    /* Selectbox styling */
    .stSelectbox {
        background-color: var(--card-bg) !important;
        color: var(--text-primary) !important;
    }
    
    .stSelectbox>div>div {
        background-color: var(--card-bg) !important;
        color: var(--text-primary) !important;
    }
    
    /* Progress bar styling */
    .stProgress > div > div {
        background-color: var(--accent) !important;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: var(--bg) !important;
        border-right: 1px solid var(--border);
    }
    
    /* Text styling */
    h1, h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 600;
    }
    
    p {
        color: var(--text-secondary) !important;
    }
    
    /* Authentication page styling */
    .stTextInput>div>div>input {
        background-color: var(--card-bg) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0.25rem;
        padding: 0.75rem;
    }
    
    .stTextInput>div>div>input::placeholder {
        color: var(--text-secondary) !important;
    }
    
    /* Fix for Streamlit's default white backgrounds */
    .stMarkdown, .stText, .stButton, .stSelectbox, .stTextInput {
        background-color: var(--bg) !important;
    }
    
    /* Fix for Streamlit's default text colors */
    .stMarkdown p, .stText p, .stSelectbox div, .stTextInput div {
        color: var(--text-primary) !important;
    }
    
    /* Fix for Streamlit's default button text */
    .stButton>button>div>p {
        color: white !important;
    }
    
    /* Fix for Streamlit's default headers */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: var(--text-primary) !important;
    }
    
    /* Link styling */
    a {
        color: var(--accent) !important;
        text-decoration: none;
        white-space: nowrap;
    }
    
    a:hover {
        text-decoration: underline;
    }
    
    /* Mobile-specific adjustments */
    @media (max-width: 768px) {
        .header {
            padding: 1.5rem 0;
            margin-bottom: 1rem;
        }
        
        .header h1 {
            font-size: 2rem;
        }
        
        .card {
            padding: 1rem;
            margin-bottom: 0.75rem;
        }
        
        .dataframe {
            font-size: 0.8rem;
        }
        
        .dataframe th, .dataframe td {
            padding: 0.75rem;
        }
        
        .stButton>button {
            padding: 0.6rem 1.2rem;
        }
        
        .exchange-toggle button {
            padding: 0.6rem 1.2rem;
            font-size: 0.9rem;
        }
    }
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
        
        # Calculate total batches
        batch_size = 50
        total_batches = (len(tokens) + batch_size - 1) // batch_size
        
        # Analyze stocks
        results = []
        for batch_num in range(total_batches):
            # Update progress
            progress = (batch_num + 1) / total_batches
            progress_bar.progress(progress)
            status_text.text(f"Analyzing batch {batch_num + 1} of {total_batches}...")
            
            # Process batch
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(tokens))
            batch_tokens = tokens[start_idx:end_idx]
            
            batch_results = analyze_stock_batch(
                alice, 
                batch_tokens, 
                st.session_state.selected_strategy,
                st.session_state.selected_exchange
            )
            results.extend(batch_results)
            
            # Update status with matches found
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
