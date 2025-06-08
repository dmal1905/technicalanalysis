# Stock Screener Application

A powerful stock screening tool built with Streamlit that provides technical analysis for NSE and BSE stocks.

## Features

- Real-time stock screening for NSE and BSE
- Multiple technical analysis strategies
- Support for AliceBlue API integration
- Interactive UI with TradingView links
- Advanced technical indicators (EMA, RSI, Support/Resistance)

## Deployment on Streamlit Cloud

1. Fork this repository to your GitHub account
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Click "New app"
4. Select your forked repository
5. Set the main file path as `app.py`
6. Add your AliceBlue API credentials in the Streamlit Cloud secrets management:
   - Go to your app settings
   - Click on "Secrets"
   - Add your credentials in the following format:
   ```toml
   [aliceblue]
   user_id = "your_user_id"
   api_key = "your_api_key"
   ```

## Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Requirements

- Python 3.8+
- Streamlit 1.30.0+
- Pandas 2.1.0+
- Other dependencies listed in requirements.txt

## Security Note

This application requires AliceBlue API credentials for full functionality. Never commit your credentials to the repository. Use Streamlit's secrets management for secure credential storage.

## Browser Compatibility

This application is best compatible with Google Chrome for optimal performance and feature support. 
