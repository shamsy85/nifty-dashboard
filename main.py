import os
import json
from fyers_apiv3 import fyersModel

def fetch_market_data():
    client_id = os.environ.get("FYERS_CLIENT_ID")
    access_token = os.environ.get("FYERS_ACCESS_TOKEN")

    if not client_id or not access_token:
        raise ValueError("Missing FYERS credentials or access token in environment variables.")

    # Initialize the FyersModel instance
    fyers = fyersModel.FyersModel(
        client_id=client_id, 
        token=access_token, 
        log_path=""
    )

    # Example: Fetch historical data for Nifty 50 (NSE:NIFTY50-INDEX)
    data = {
        "symbol": "NSE:NIFTY50-INDEX",
        "resolution": "D",
        "date_format": "1",
        "range_from": "2026-01-01",
        "range_to": "2026-09-01",
        "cont_flag": "1"
    }

    response = fyers.history(data=data)
    print("Fetched Data Response:", json.dumps(response, indent=2))

if __name__ == "__main__":
    fetch_market_data()
