import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from scipy.signal import argrelextrema
from alice_client import get_cached_historical_data

def analyze_stock_batch(alice, tokens, strategy, exchange='NSE', batch_size=50):
    """Analyze a batch of stocks in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_token = {
            executor.submit(analyze_stock, alice, token, strategy, exchange): token
            for token in tokens[:batch_size]
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

def analyze_stock(alice, token, strategy, exchange='NSE'):
    """Analyze a single stock with optimized data fetching."""
    try:
        # Use cached historical data
        instrument, df = get_cached_historical_data(
            alice, token, 
            datetime.now() - timedelta(days=365), 
            datetime.now(), 
            "D", 
            exchange
        )
        
        if len(df) < 100:
            return None

        # Calculate indicators efficiently
        df['50_EMA'] = df['close'].ewm(span=50, adjust=False).mean()
        df['200_EMA'] = df['close'].ewm(span=200, adjust=False).mean()
        df['RSI'] = compute_rsi(df['close'])

        if strategy == "EMA, RSI & Support Zone (Buy)":
            return analyze_bullish(df, instrument)
        elif strategy == "EMA, RSI & Resistance Zone (Sell)":
            return analyze_bearish(df, instrument)
        
        return None

    except Exception as e:
        print(f"Error analyzing {token}: {e}")
        return None

def compute_rsi(prices, period=14):
    """Compute RSI efficiently."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_bullish(df, instrument):
    """Analyze bullish signals efficiently."""
    try:
        # Find support zones
        close_prices = df['close'].values
        window_size = max(int(len(df) * 0.05), 5)
        local_min = argrelextrema(close_prices, np.less_equal, order=window_size)[0]

        valid_supports = []
        for m in local_min:
            if m < len(df) - 126:  # Only recent supports
                continue
            support_price = close_prices[m]
            current_price = close_prices[-1]
            if 1.05 <= (current_price / support_price) <= 1.20:
                if df['volume'].iloc[-1] > df['volume'].iloc[m] * 0.8:
                    valid_supports.append({
                        'price': support_price,
                        'touches': 1
                    })

        if not valid_supports:
            return None

        # Get strongest support
        strongest_support = max(valid_supports, key=lambda x: x['touches'])
        current_price = close_prices[-1]
        distance_pct = ((current_price - strongest_support['price']) / strongest_support['price']) * 100

        # Check conditions
        ema_crossover = df['50_EMA'].iloc[-1] > df['200_EMA'].iloc[-1]
        rsi_value = df['RSI'].iloc[-1]
        rsi_ok = 30 <= rsi_value <= 70

        if ema_crossover and rsi_ok:
            return {
                'Name': instrument.symbol,
                'Close': current_price,
                'Support': strongest_support['price'],
                'Strength': strongest_support['touches'],
                'Distance_pct': distance_pct,
                'RSI': rsi_value,
                'Trend': 'Bullish'
            }
        return None

    except Exception as e:
        print(f"Error in bullish analysis: {e}")
        return None

def analyze_bearish(df, instrument):
    """Analyze bearish signals efficiently."""
    try:
        # Find resistance zones
        close_prices = df['close'].values
        window_size = max(int(len(df) * 0.05), 5)
        local_max = argrelextrema(close_prices, np.greater_equal, order=window_size)[0]

        valid_resistances = []
        for m in local_max:
            if m < len(df) - 126:  # Only recent resistances
                continue
            resistance_price = close_prices[m]
            current_price = close_prices[-1]
            if 0.80 <= (current_price / resistance_price) <= 0.95:
                if df['volume'].iloc[-1] > df['volume'].iloc[m] * 0.8:
                    valid_resistances.append({
                        'price': resistance_price,
                        'touches': 1
                    })

        if not valid_resistances:
            return None

        # Get strongest resistance
        strongest_resistance = max(valid_resistances, key=lambda x: x['touches'])
        current_price = close_prices[-1]
        distance_pct = ((strongest_resistance['price'] - current_price) / current_price) * 100

        # Check conditions
        ema_crossover = df['50_EMA'].iloc[-1] < df['200_EMA'].iloc[-1]
        rsi_value = df['RSI'].iloc[-1]
        rsi_ok = 30 <= rsi_value <= 70

        if ema_crossover and rsi_ok:
            return {
                'Name': instrument.symbol,
                'Close': current_price,
                'Resistance': strongest_resistance['price'],
                'Strength': strongest_resistance['touches'],
                'Distance_pct': distance_pct,
                'RSI': rsi_value,
                'Trend': 'Bearish'
            }
        return None

    except Exception as e:
        print(f"Error in bearish analysis: {e}")
        return None

def analyze_all_tokens(alice, tokens, strategy, exchange='NSE'):
    """Analyze all tokens with optimized batch processing."""
    results = []
    batch_size = 50
    total_batches = (len(tokens) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(tokens))
        batch_tokens = tokens[start_idx:end_idx]
        
        batch_results = analyze_stock_batch(alice, batch_tokens, strategy, exchange, batch_size)
        results.extend(batch_results)
    
    return results 
