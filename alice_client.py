import os
import json
import datetime
from pya3 import Aliceblue
from functools import lru_cache
import pandas as pd

API_FILE = "api_credentials.json"

def save_credentials(user_id, api_key):
    """ Save AliceBlue credentials in a file for the day. """
    credentials = {
        "user_id": user_id,
        "api_key": api_key,
        "date": str(datetime.date.today())
    }
    with open(API_FILE, "w") as f:
        json.dump(credentials, f)

def load_credentials():
    """ Load AliceBlue credentials from file. """
    try:
        if os.path.exists(API_FILE):
            with open(API_FILE, "r") as f:
                credentials = json.load(f)
                # Check if credentials are from today
                if credentials.get("date") == str(datetime.date.today()):
                    return credentials.get("user_id"), credentials.get("api_key")
    except Exception as e:
        print(f"Error loading credentials: {e}")
    return None, None

def initialize_alice():
    """ Initialize AliceBlue API session with stored credentials. """
    user_id, api_key = load_credentials()
    if not user_id or not api_key:
        raise Exception("AliceBlue credentials not found. Please log in.")

    alice = Aliceblue(user_id=user_id, api_key=api_key)
    alice.get_session_id()
    return alice

@lru_cache(maxsize=1000)
def get_cached_historical_data(alice, token, from_date, to_date, interval="D", exchange='NSE'):
    """Cached version of historical data fetching."""
    exchange_name = 'BSE (1)' if exchange == 'BSE' else 'NSE'
    instrument = alice.get_instrument_by_token(exchange_name, token)
    historical_data = alice.get_historical(instrument, from_date, to_date, interval)
    df = pd.DataFrame(historical_data).dropna()
    return instrument, df

def clear_cache():
    """Clear the historical data cache."""
    get_cached_historical_data.cache_clear()
