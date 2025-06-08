import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from scipy.signal import argrelextrema
from sklearn.preprocessing import MinMaxScaler

def get_historical_data(alice, token, from_date, to_date, interval="D", exchange='NSE'):
    """Fetch historical data and return as a DataFrame."""
    exchange_name = 'BSE (1)' if exchange == 'BSE' else 'NSE'
    instrument = alice.get_instrument_by_token(exchange_name, token)
    historical_data = alice.get_historical(instrument, from_date, to_date, interval)
    df = pd.DataFrame(historical_data).dropna()
    return instrument, df

def identify_candlestick_patterns(df):
    """Identify common candlestick patterns."""
    patterns = []
    
    # Calculate basic candle properties
    df['body'] = df['close'] - df['open']
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
    df['body_size'] = abs(df['body'])
    df['total_size'] = df['high'] - df['low']
    
    # Doji
    doji = (df['body_size'] <= 0.1 * df['total_size'])
    if doji.iloc[-1]:
        patterns.append('Doji')
    
    # Hammer
    hammer = (
        (df['lower_shadow'] > 2 * df['body_size']) &
        (df['upper_shadow'] < df['body_size'])
    )
    if hammer.iloc[-1]:
        patterns.append('Hammer')
    
    # Engulfing
    if len(df) >= 2:
        bullish_engulfing = (
            (df['body'].iloc[-2] < 0) &  # Previous candle is bearish
            (df['body'].iloc[-1] > 0) &  # Current candle is bullish
            (df['open'].iloc[-1] < df['close'].iloc[-2]) &  # Current open below previous close
            (df['close'].iloc[-1] > df['open'].iloc[-2])  # Current close above previous open
        )
        if bullish_engulfing:
            patterns.append('Bullish Engulfing')
    
    return patterns

def analyze_volume_profile(df):
    """Analyze volume profile and identify significant price levels."""
    # Create price bins
    price_range = df['high'].max() - df['low'].min()
    num_bins = 50
    bin_size = price_range / num_bins
    
    # Calculate volume profile
    volume_profile = pd.DataFrame()
    volume_profile['price_level'] = np.arange(df['low'].min(), df['high'].max(), bin_size)
    volume_profile['volume'] = 0
    
    for i in range(len(df)):
        price = df['close'].iloc[i]
        volume = df['volume'].iloc[i]
        bin_index = int((price - df['low'].min()) / bin_size)
        if 0 <= bin_index < len(volume_profile):
            volume_profile.iloc[bin_index, 1] += volume
    
    # Identify high volume nodes
    mean_volume = volume_profile['volume'].mean()
    std_volume = volume_profile['volume'].std()
    high_volume_nodes = volume_profile[volume_profile['volume'] > mean_volume + std_volume]
    
    return high_volume_nodes

def analyze_market_structure(df):
    """Analyze market structure using higher highs and lower lows."""
    # Find local maxima and minima
    window = 5
    local_max = argrelextrema(df['high'].values, np.greater_equal, order=window)[0]
    local_min = argrelextrema(df['low'].values, np.less_equal, order=window)[0]
    
    # Analyze last 3 swing points
    recent_max = df['high'].iloc[local_max[-3:]]
    recent_min = df['low'].iloc[local_min[-3:]]
    
    # Determine trend
    if len(recent_max) >= 2 and len(recent_min) >= 2:
        higher_highs = recent_max.iloc[-1] > recent_max.iloc[-2]
        higher_lows = recent_min.iloc[-1] > recent_min.iloc[-2]
        
        if higher_highs and higher_lows:
            return "Uptrend"
        elif not higher_highs and not higher_lows:
            return "Downtrend"
        else:
            return "Sideways"
    
    return "Undefined"

def analyze_stock_advanced(alice, token, strategy, exchange='NSE'):
    """Analyze stock using advanced strategies."""
    try:
        instrument, df = get_historical_data(
            alice, token, datetime.now() - timedelta(days=365), datetime.now(), "D", exchange
        )
        if len(df) < 100:
            return None

        result = {
            'Name': instrument.symbol,
            'Close': df['close'].iloc[-1],
            'Volume': df['volume'].iloc[-1],
            'Patterns': [],
            'Market_Structure': '',
            'Volume_Nodes': [],
            'Strength': 0
        }

        # Analyze candlestick patterns
        patterns = identify_candlestick_patterns(df)
        result['Patterns'] = patterns
        
        # Analyze market structure
        result['Market_Structure'] = analyze_market_structure(df)
        
        # Analyze volume profile
        volume_nodes = analyze_volume_profile(df)
        result['Volume_Nodes'] = volume_nodes['price_level'].tolist()
        
        # Calculate overall strength based on strategy
        if strategy == "Price Action Breakout":
            # Strong breakouts with volume confirmation
            if patterns and df['volume'].iloc[-1] > df['volume'].rolling(20).mean().iloc[-1] * 1.5:
                result['Strength'] = len(patterns) * 2
                
        elif strategy == "Volume Profile Analysis":
            # High volume nodes near current price
            current_price = df['close'].iloc[-1]
            nearby_nodes = volume_nodes[abs(volume_nodes['price_level'] - current_price) / current_price < 0.02]
            result['Strength'] = len(nearby_nodes) * 3
            
        elif strategy == "Market Structure Analysis":
            # Strong trend with confirmation
            if result['Market_Structure'] in ['Uptrend', 'Downtrend']:
                result['Strength'] = 5
                
        elif strategy == "Multi-Factor Analysis":
            # Combine all factors
            strength = 0
            strength += len(patterns) * 2  # Candlestick patterns
            strength += len(result['Volume_Nodes'])  # Volume nodes
            strength += 5 if result['Market_Structure'] in ['Uptrend', 'Downtrend'] else 0  # Market structure
            result['Strength'] = strength

        return result if result['Strength'] > 0 else None

    except Exception as e:
        print(f"Error analyzing {token}: {e}")
        return None

def analyze_all_tokens_advanced(alice, tokens, strategy, exchange='NSE'):
    """Analyze all tokens using advanced strategies in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_token = {
            executor.submit(analyze_stock_advanced, alice, token, strategy, exchange): token
            for token in tokens
        }
        for future in as_completed(future_to_token):
            token = future_to_token[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                print(f"Error processing {token}: {e}")
    return results

def analyze_price_movement(df, duration_days, target_percentage, direction='up'):
    """
    Analyze price movement over a specified duration.
    
    Args:
        df: DataFrame with price data
        duration_days: Number of days to look back
        target_percentage: Target percentage change
        direction: 'up' or 'down' for price movement direction
    
    Returns:
        tuple: (percentage_change, met_criteria)
    """
    if len(df) < duration_days:
        return 0, False
    
    # Get the price from duration_days ago and current price
    start_price = df['close'].iloc[-duration_days]
    current_price = df['close'].iloc[-1]
    
    # Calculate percentage change
    percentage_change = ((current_price - start_price) / start_price) * 100
    
    # Check if criteria is met
    if direction == 'up':
        met_criteria = percentage_change >= target_percentage
    else:  # down
        met_criteria = percentage_change <= -target_percentage
    
    return percentage_change, met_criteria

def analyze_stock_custom(alice, token, duration_days, target_percentage, direction='up', exchange='NSE'):
    """
    Analyze stock based on custom price movement criteria.
    
    Args:
        alice: AliceBlue API instance
        token: Stock token
        duration_days: Number of days to look back
        target_percentage: Target percentage change
        direction: 'up' or 'down' for price movement direction
        exchange: 'NSE' or 'BSE'
    
    Returns:
        dict: Analysis results or None if criteria not met
    """
    try:
        # Get more historical data than needed to ensure we have enough
        lookback_days = max(duration_days * 2, 365)  # At least double the duration or 1 year
        instrument, df = get_historical_data(
            alice, token, 
            datetime.now() - timedelta(days=lookback_days), 
            datetime.now(), 
            "D", 
            exchange
        )
        
        if len(df) < duration_days:
            return None

        # Calculate price movement
        percentage_change, met_criteria = analyze_price_movement(
            df, duration_days, target_percentage, direction
        )
        
        if not met_criteria:
            return None

        # Additional analysis for context
        volume_trend = df['volume'].iloc[-5:].mean() > df['volume'].iloc[-20:].mean()
        volatility = df['close'].pct_change().std() * 100
        
        result = {
            'Name': instrument.symbol,
            'Close': df['close'].iloc[-1],
            'Start_Price': df['close'].iloc[-duration_days],
            'Percentage_Change': percentage_change,
            'Volume_Trend': 'Increasing' if volume_trend else 'Decreasing',
            'Volatility': volatility,
            'Duration_Days': duration_days,
            'Direction': direction.capitalize(),
            'Strength': abs(percentage_change) / target_percentage  # Normalized strength
        }
        
        return result

    except Exception as e:
        print(f"Error analyzing {token}: {e}")
        return None

def analyze_all_tokens_custom(alice, tokens, duration_days, target_percentage, direction='up', exchange='NSE'):
    """Analyze all tokens using custom criteria in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_token = {
            executor.submit(
                analyze_stock_custom, 
                alice, 
                token, 
                duration_days, 
                target_percentage, 
                direction, 
                exchange
            ): token for token in tokens
        }
        for future in as_completed(future_to_token):
            token = future_to_token[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                print(f"Error processing {token}: {e}")
    return results 
