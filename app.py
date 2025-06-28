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

# Set theme configuration using teal (#7FE2D3)
st.markdown("""
    <style>
        .button-box {
            margin-bottom: 1rem;
        }

        /* NSE Selected - Aqua */
        .nse-btn button {
            background-color: #A7D6D6 !important;
            color: black !important;
        }
        .nse-btn button:hover {
            background-color: #94CACA !important;
        }

        /* BSE Selected - Peach */
        .bse-btn button {
            background-color: #F9D5C2 !important;
            color: black !important;
        }
        .bse-btn button:hover {
            background-color: #F2C0AC !important;
        }

        /* Inactive Button - Blue Gray */
        .default-btn button {
            background-color: #DDEBF1 !important;
            color: black !important;
        }
        .default-btn button:hover {
            background-color: #CFE0E8 !important;
        }
    </style>
""", unsafe_allow_html=True)




# Initialize session state
if 'selected_exchange' not in st.session_state:
    st.session_state.selected_exchange = 'NSE'

def get_stock_lists_for_exchange(exchange):
    if exchange == 'NSE':
        return {k: v for k, v in STOCK_LISTS.items() if k in [
            'NIFTY FNO', 'NIFTY 50', 'NIFTY 200', 'NIFTY 500', 'ALL STOCKS'
        ]}
    else:
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


st.markdown('<div class="exchange-toggle">', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    btn_class = "nse-btn" if st.session_state.selected_exchange == 'NSE' else "default-btn"
    st.markdown(f'<div class="button-box {btn_class}">', unsafe_allow_html=True)
    if st.button("NSE", key="nse_btn", help="Switch to NSE stocks", use_container_width=True):
        st.session_state.selected_exchange = 'NSE'
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    btn_class = "bse-btn" if st.session_state.selected_exchange == 'BSE' else "default-btn"
    st.markdown(f'<div class="button-box {btn_class}">', unsafe_allow_html=True)
    if st.button("BSE", key="bse_btn", help="Switch to BSE stocks", use_container_width=True):
        st.session_state.selected_exchange = 'BSE'
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)



st.markdown('</div>', unsafe_allow_html=True)

try:
    alice = initialize_alice()
except Exception as e:
    st.error(f"Failed to initialize AliceBlue API: {e}")
    alice = None

@st.cache_data(ttl=300)
def fetch_screened_stocks(tokens, strategy):
    try:
        if not alice:
            raise Exception("AliceBlue API is not initialized.")
        return analyze_all_tokens_advanced(alice, tokens, strategy, exchange=st.session_state.selected_exchange)
    except Exception as e:
        st.error(f"Error fetching stock data: {e}")
        return []

def clean_and_display_data(data, strategy):
    if not data or not isinstance(data, list):
        return pd.DataFrame()

    df = pd.DataFrame(data)
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

    df = df.sort_values(by="Strength", ascending=False)
    return df

def safe_display(df, title):
    if df.empty:
        st.warning(f"No stocks found for {title}")
    else:
        st.markdown(f"### {title}")
        if "Name" in df.columns:
            df["Name"] = df["Name"].apply(
                lambda x: generate_tradingview_link(x, st.session_state.selected_exchange)
            )
        st.markdown(df.to_html(escape=False), unsafe_allow_html=True)

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

st.markdown("### Strategy Details")
st.markdown(strategy_descriptions[strategy])

if strategy == "Custom Price Movement":
    col1, col2, col3 = st.columns(3)
    with col1:
        duration_days = st.number_input(
            "Duration (Days)", min_value=1, max_value=365, value=30,
            help="Number of days to look back"
        )
    with col2:
        target_percentage = st.number_input(
            "Target Percentage", min_value=0.1, max_value=1000.0,
            value=10.0, step=0.1, help="Target percentage change"
        )
    with col3:
        direction = st.selectbox(
            "Direction", ["up", "down"], help="Price movement direction"
        )

if st.button("Start Screening", use_container_width=True):
    tokens = available_lists.get(selected_list, [])
    if not tokens:
        st.warning(f"No stocks found for {selected_list}.")
    else:
        with st.spinner("Analyzing stocks..."):
            if strategy == "Custom Price Movement":
                screened_stocks = analyze_all_tokens_custom(
                    alice, tokens, duration_days, target_percentage, direction,
                    exchange=st.session_state.selected_exchange
                )
            else:
                screened_stocks = analyze_all_tokens_advanced(
                    alice, tokens, strategy,
                    exchange=st.session_state.selected_exchange
                )
        df = clean_and_display_data(screened_stocks, strategy)
        safe_display(df, strategy)
