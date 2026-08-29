import json
from datetime import datetime
import yfinance as yf

def update_nifty_data():
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    # Fetch live NIFTY 50 index data
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period="1d")

    if not hist.empty:
        spot_close = round(float(hist['Close'].iloc[-1]), 2)
        spot_high = round(float(hist['High'].iloc[-1]), 2)
        spot_low = round(float(hist['Low'].iloc[-1]), 2)
    else:
        spot_close, spot_high, spot_low = 24175.65, 24188.30, 24076.85

    atm_strike = round(spot_close / 50) * 50

    payload = {
        "spotPrice": spot_close,
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "expiryDate": "01-09-2026",
        "currentDate": today_str,
        "atmStrike": atm_strike,
        "bannerTotal": 17.00,
        "ce": {
            "high": 106.0,
            "close": 79.1,
            "low": 51.6
        },
        "pe": {
            "high": 165.9,
            "close": 96.1,
            "low": 81.0
        },
        "sniper1": {
            "strike": atm_strike,
            "ce": 79.10,
            "pe": 96.10,
            "otmCeStrike": atm_strike + 100,
            "otmCe": 40.95,
            "otmPeStrike": atm_strike - 100,
            "otmPe": 53.95
        },
        "sniper2": {
            "strike": atm_strike - 50,
            "ce": 104.75,
            "pe": 72.10,
            "otmCeStrike": atm_strike + 50,
            "otmCe": 57.65,
            "otmPeStrike": atm_strike - 150,
            "otmPe": 39.85
        }
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print("Updated data.json successfully.")

if __name__ == "__main__":
    update_nifty_data()
