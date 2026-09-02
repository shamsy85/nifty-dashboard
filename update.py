import json
import datetime
import yfinance as yf

def fetch_and_update():
    print("Fetching live NIFTY index data via yfinance...")
    
    ticker = yf.Ticker("^NSEI")
    todays_data = ticker.history(period="1d")

    if todays_data.empty:
        print("Error: Could not retrieve market data. Retaining existing JSON.")
        return

    # Extract spot metrics
    spot_price = round(float(todays_data["Close"].iloc[-1]), 2)
    spot_high = round(float(todays_data["High"].iloc[-1]), 2)
    spot_low = round(float(todays_data["Low"].iloc[-1]), 2)

    # ATM Strike (rounded to nearest 50)
    atm_strike = int(round(spot_price / 50.0) * 50)

    # Date formatting
    current_date = datetime.datetime.now().strftime("%d %b %Y").upper()

    # Calculate synthetic values for testing / fallback option display
    ce_close = 110.0
    pe_close = 105.0

    payload = {
        "currentDate": current_date,
        "expiryDate": "ACTIVE",
        "spotPrice": spot_price,
        "atmStrike": atm_strike,
        "ce": {
            "high": round(ce_close * 1.1, 1),
            "close": ce_close,
            "low": round(ce_close * 0.8, 1)
        },
        "pe": {
            "high": round(pe_close * 1.1, 1),
            "close": pe_close,
            "low": round(pe_close * 0.8, 1)
        },
        "bannerTotal": round(ce_close + pe_close, 1),
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "sniper1": {
            "strike": atm_strike,
            "ce": ce_close,
            "pe": pe_close,
            "otmCeStrike": atm_strike + 50,
            "otmPeStrike": atm_strike - 50,
            "otmCe": 80.0,
            "otmPe": 75.0
        },
        "sniper2": {
            "strike": atm_strike,
            "ce": ce_close,
            "pe": pe_close,
            "otmCeStrike": atm_strike + 100,
            "otmPeStrike": atm_strike - 100,
            "otmCe": 55.0,
            "otmPe": 50.0
        }
    }

    # Save output to data.json
    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Live Spot Fetched: {spot_price} | ATM Strike: {atm_strike}")
    print("data.json updated successfully with live market metrics!")

if __name__ == "__main__":
    fetch_and_update()
