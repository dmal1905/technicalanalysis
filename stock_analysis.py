import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from scipy.signal import argrelextrema

def get_historical_data(alice, token, from_date, to_date, interval="D", exchange='NSE'):
    """Fetch historical data and return as a DataFrame."""
    exchange_name = 'BSE (1)' if exchange == 'BSE' else 'NSE'
    instrument = alice.get_instrument_by_token(exchange_name, token)
    historical_data = alice.get_historical(instrument, from_date, to_date, interval)
    df = pd.DataFrame(historical_data).dropna()
    return instrument, df

def compute_rsi(prices, period=14):
    """Compute RSI for a given price series."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def cluster_zones(zones, prices, threshold=0.02):
    """Cluster nearby price zones."""
    if not zones:
        return []
    
    # Sort zones by price
    sorted_zones = sorted(zones, key=lambda x: x['price'])
    clusters = []
    current_cluster = [sorted_zones[0]]
    
    for zone in sorted_zones[1:]:
        if abs(zone['price'] - current_cluster[-1]['price']) / current_cluster[-1]['price'] <= threshold:
            current_cluster.append(zone)
        else:
            # Calculate average price for the cluster
            avg_price = sum(z['price'] for z in current_cluster) / len(current_cluster)
            clusters.append({
                'price': avg_price,
                'touches': len(current_cluster)
            })
            current_cluster = [zone]
    
    # Add the last cluster
    if current_cluster:
        avg_price = sum(z['price'] for z in current_cluster) / len(current_cluster)
        clusters.append({
            'price': avg_price,
            'touches': len(current_cluster)
        })
    
    return clusters

def analyze_stock_bullish(alice, token, exchange='NSE'):
    """
    Analyze stock for bullish signals using support zones, EMA crossover, and RSI filter.
    Logic:
      - Support zones are determined via local minimum analysis.
      - Current price must be 5-20% above a recent support and with sufficient volume.
      - Requires bullish EMA crossover (50 EMA > 200 EMA) and RSI not overbought.
    """
    try:
        instrument, df = get_historical_data(
            alice, token, datetime.now() - timedelta(days=730), datetime.now(), "D", exchange
        )
        if len(df) < 100:
            return None

        df['50_EMA'] = df['close'].ewm(span=50).mean()
        df['200_EMA'] = df['close'].ewm(span=200).mean()
        rsi = compute_rsi(df['close'])

        close_prices = df['close'].values
        scaler = MinMaxScaler()
        normalized_prices = scaler.fit_transform(close_prices.reshape(-1, 1)).flatten()

        window_size = max(int(len(df) * 0.05), 5)
        local_min = argrelextrema(normalized_prices, np.less_equal, order=window_size)[0]

        valid_supports = []
        for m in local_min:
            # Only consider recent support points (within last 6 months)
            if m < len(df) - 126:
                continue
            support_price = close_prices[m]
            current_price = close_prices[-1]
            # Check if current price is 5-20% above support
            if 1.05 <= (current_price / support_price) <= 1.20:
                if df['volume'].iloc[-1] > df['volume'].iloc[m] * 0.8:
                    valid_supports.append({
                        'price': support_price,
                        'date': df.index[m],
                        'touches': 1
                    })

        if not valid_supports:
            return None

        support_clusters = cluster_zones(valid_supports, close_prices)
        if not support_clusters:
            return None

        # Get the strongest support (most touches)
        strongest_support = max(support_clusters, key=lambda x: x['touches'])
        current_price = close_prices[-1]
        distance_pct = ((current_price - strongest_support['price']) / strongest_support['price']) * 100

        # Check EMA crossover and RSI conditions
        ema_crossover = df['50_EMA'].iloc[-1] > df['200_EMA'].iloc[-1]
        rsi_value = rsi.iloc[-1]
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
        print(f"Error analyzing {token}: {e}")
        return None

def analyze_stock_bearish(alice, token, exchange='NSE'):
    """
    Analyze stock for bearish signals using resistance zones, EMA crossover, and RSI filter.
    Logic:
      - Resistance zones are determined via local maximum analysis.
      - Current price must be 5-20% below a recent resistance and with sufficient volume.
      - Requires bearish EMA crossover (50 EMA < 200 EMA) and RSI not oversold.
    """
    try:
        instrument, df = get_historical_data(
            alice, token, datetime.now() - timedelta(days=730), datetime.now(), "D", exchange
        )
        if len(df) < 100:
            return None

        df['50_EMA'] = df['close'].ewm(span=50).mean()
        df['200_EMA'] = df['close'].ewm(span=200).mean()
        rsi = compute_rsi(df['close'])

        close_prices = df['close'].values
        scaler = MinMaxScaler()
        normalized_prices = scaler.fit_transform(close_prices.reshape(-1, 1)).flatten()

        window_size = max(int(len(df) * 0.05), 5)
        local_max = argrelextrema(normalized_prices, np.greater_equal, order=window_size)[0]

        valid_resistances = []
        for m in local_max:
            # Only consider recent resistance points (within last 6 months)
            if m < len(df) - 126:
                continue
            resistance_price = close_prices[m]
            current_price = close_prices[-1]
            # Check if current price is 5-20% below resistance
            if 0.80 <= (current_price / resistance_price) <= 0.95:
                if df['volume'].iloc[-1] > df['volume'].iloc[m] * 0.8:
                    valid_resistances.append({
                        'price': resistance_price,
                        'date': df.index[m],
                        'touches': 1
                    })

        if not valid_resistances:
            return None

        resistance_clusters = cluster_zones(valid_resistances, close_prices)
        if not resistance_clusters:
            return None

        # Get the strongest resistance (most touches)
        strongest_resistance = max(resistance_clusters, key=lambda x: x['touches'])
        current_price = close_prices[-1]
        distance_pct = ((strongest_resistance['price'] - current_price) / current_price) * 100

        # Check EMA crossover and RSI conditions
        ema_crossover = df['50_EMA'].iloc[-1] < df['200_EMA'].iloc[-1]
        rsi_value = rsi.iloc[-1]
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
        print(f"Error analyzing {token}: {e}")
        return None

def analyze_all_tokens_bullish(alice, tokens, exchange='NSE'):
    """Analyze all tokens for bullish signals in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_token = {
            executor.submit(analyze_stock_bullish, alice, token, exchange): token
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

def analyze_all_tokens_bearish(alice, tokens, exchange='NSE'):
    """Analyze all tokens for bearish signals in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_token = {
            executor.submit(analyze_stock_bearish, alice, token, exchange): token
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