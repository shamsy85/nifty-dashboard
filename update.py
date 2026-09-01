import os
import json
import time
import requests
from datetime import datetime

# NSE JSON API Endpoint
API_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/option-chain",
    "Accept": "application/json, text/plain, */*"
}

def fetch_data():
    session = requests.Session()
    session.headers.update(headers)

    # 1. Warm-up session to establish cookies
    try:
        session.get("https://www.nseindia.com", timeout=15)
        time.sleep(2)
    except Exception as e:
        print(f"Session init warning: {e}")

    # 2. Fetch Option Chain JSON
    response = session.get(API_URL, timeout=30)
    response.raise_for_status()
    return response.json()

def process_and_save():
    raw_data = fetch_data()
    records = raw_data.get("records", {})
    data_list = records.get("data", [])

    # Extract Spot Price
    spot = float(records.get("underlyingValue", 0))
    if spot == 0 and data_list:
        # Fallback if underlyingValue is nested inside records
        spot = float(data_list[0].get("PE", {}).get("underlyingValue") or data_list[0].get("CE", {}).get("underlyingValue") or 0)

    # Calculate ATM Strike (Nearest 50)
    atm = int(round(spot / 50.0) * 50)

    # Filter data for current expiry
    expiry_dates = records.get("expiryDates", [])
    current_expiry = expiry_dates[0] if expiry_dates else "--"

    # Map option chain records by strike price for the active expiry
    strike_map = {}
    for item in data_list:
        if item.get("expiryDate") == current_expiry:
            strike_map[item.get("strikePrice")] = item

    def get_strike_info(strike):
        item = strike_map.get(strike, {})
        ce = item.get("CE", {})
        pe = item.get("PE", {})
        return {
            "ce_high": float(ce.get("highPrice", 0)),
            "ce_close": float(ce.get("lastPrice", 0)),
            "ce_low": float(ce.get("lowPrice", 0)),
            "pe_high": float(pe.get("highPrice", 0)),
            "pe_close": float(pe.get("lastPrice", 0)),
            "pe_low": float(pe.get("lowPrice", 0)),
        }

    atm_data = get_strike_info(atm)
    snip1_otm_ce = get_strike_info(atm + 50)
    snip1_otm_pe = get_strike_info(atm - 50)
    snip2_otm_ce = get_strike_info(atm + 100)
    snip2_otm_pe = get_strike_info(atm - 100)

    output = {
        "currentDate": datetime.now().strftime("%d %b %Y").upper(),
        "expiryDate": str(current_expiry).upper(),
        "spotPrice": spot,
        "atmStrike": atm,

        "ce": {
            "high": atm_data["ce_high"],
            "close": atm_data["ce_close"],
            "low": atm_data["ce_low"]
        },
        "pe": {
            "high": atm_data["pe_high"],
            "close": atm_data["pe_close"],
            "low": atm_data["pe_low"]
        },

        "bannerTotal": atm_data["ce_close"] + atm_data["pe_close"],

        "spotHigh": spot + 50.0,
        "spotLow": spot - 50.0,

        "sniper1": {
            "strike": atm,
            "ce": atm_data["ce_close"],
            "pe": atm_data["pe_close"],
            "otmCeStrike": atm + 50,
            "otmPeStrike": atm - 50,
            "otmCe": snip1_otm_ce["ce_close"],
            "otmPe": snip1_otm_pe["pe_close"]
        },

        "sniper2": {
            "strike": atm,
            "ce": atm_data["ce_close"],
            "pe": atm_data["pe_close"],
            "otmCeStrike": atm + 100,
            "otmPeStrike": atm - 100,
            "otmCe": snip2_otm_ce["ce_close"],
            "otmPe": snip2_otm_pe["pe_close"]
        }
    }

    with open("data.json", "w") as f:
        json.dump(output, f, indent=2)

    print("data.json generated successfully from NSE JSON API.")

if __name__ == "__main__":
    process_and_save()
