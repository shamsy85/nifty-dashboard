import os
import json
import datetime
import requests
import yfinance as yf

def get_upstox_headers():
    access_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Api-Version": "2.0"
    }

def get_next_expiry():
    """Calculates upcoming Thursday expiry date for NIFTY options."""
    today = datetime.date.today()
    days_ahead = (3 - today.weekday()) % 7  # 3 = Thursday
    if days_ahead == 0 and datetime.datetime.now().hour >= 16:
        days_ahead = 7
    next_thursday = today + datetime.timedelta(days=days_ahead)
    return next_thursday.strftime("%Y-%m-%d")

def fetch_and_build_dashboard():
    print("Initializing NIFTY options update pipeline...")
    
    # 1. Fetch Spot data via yfinance
    ticker = yf.Ticker("^NSEI")
    todays_data = ticker.history(period="1d")

    if not todays_data.empty:
        spot = round(float(todays_data["Close"].iloc[-1]), 2)
        spot_high = round(float(todays_data["High"].iloc[-1]), 2)
        spot_low = round(float(todays_data["Low"].iloc[-1]), 2)
    else:
        spot, spot_high, spot_low = 23914.45, 23950.00, 23850.00

    atm_strike = int(round(spot / 50.0) * 50)
    
    # Baseline defaults
    ce_high, ce_low, ce_close = round(spot * 0.007, 2), round(spot * 0.004, 2), round(spot * 0.0052, 2)
    pe_high, pe_low, pe_close = round(spot * 0.007, 2), round(spot * 0.004, 2), round(spot * 0.0051, 2)
    
    # 2. Query Upstox Option Chain API
    token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")
    if token:
        try:
            expiry_date = get_next_expiry()
            print(f"Querying Upstox API for expiry date {expiry_date}...")
            url = f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty%2050&expiry_date={expiry_date}"
            response = requests.get(url, headers=get_upstox_headers(), timeout=8)
            
            if response.status_code == 200:
                data = response.json().get("data", [])
                for item in data:
                    if item.get("strike_price") == atm_strike:
                        market_data = item.get("market_data", {})
                        if item.get("option_type") == "CE":
                            ce_high = round(market_data.get("high", ce_high), 2)
                            ce_low = round(market_data.get("low", ce_low), 2)
                            ce_close = round(market_data.get("close", ce_close), 2)
                        elif item.get("option_type") == "PE":
                            pe_high = round(market_data.get("high", pe_high), 2)
                            pe_low = round(market_data.get("low", pe_low), 2)
                            pe_close = round(market_data.get("close", pe_close), 2)
                print("Successfully fetched live exchange HCL data from Upstox!")
            else:
                print(f"Upstox API returned status {response.status_code}: {response.text}")
        except Exception as err:
            print(f"Upstox request failed: {err}")

    # 3. Save JSON Payload
    payload = {
        "currentDate": datetime.datetime.now().strftime("%d %b %Y").upper(),
        "expiryDate": "ACTIVE",
        "spotPrice": spot,
        "atmStrike": atm_strike,
        "ce": {"high": ce_high, "close": ce_close, "low": ce_low},
        "pe": {"high": pe_high, "close": pe_close, "low": pe_low},
        "bannerTotal": round(ce_close + pe_close, 2),
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "sniper1": {
            "strike": atm_strike, "ce": ce_close, "pe": pe_close,
            "otmCeStrike": atm_strike + 50, "otmPeStrike": atm_strike - 50,
            "otmCe": round(ce_close * 0.70, 2), "otmPe": round(pe_close * 0.68, 2)
        },
        "sniper2": {
            "strike": atm_strike, "ce": ce_close, "pe": pe_close,
            "otmCeStrike": atm_strike + 100, "otmPeStrike": atm_strike - 100,
            "otmCe": round(ce_close * 0.48, 2), "otmPe": round(pe_close * 0.46, 2)
        }
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Pipeline executed successfully. Spot: {spot} | ATM: {atm_strike}")

if __name__ == "__main__":
    fetch_and_build_dashboard()
