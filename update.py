import os
import json
import time
import requests
from datetime import datetime

# URL and fallback headers
API_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
HOME_URL = "https://www.nseindia.com/option-chain"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

def fetch_data():
    session = requests.Session()
    session.headers.update(headers)

    # Step 1: Hit main page to get initial cookies
    response = session.get("https://www.nseindia.com", timeout=15)
    time.sleep(1)

    # Step 2: Hit option-chain landing page to solidify session
    response = session.get(HOME_URL, timeout=15)
    time.sleep(1)

    # Step 3: Switch headers to JSON request mode
    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Referer": HOME_URL,
        "X-Requested-With": "XMLHttpRequest"
    })

    # Step 4: Fetch API payload
    res = session.get(API_URL, timeout=30)
    res.raise_for_status()
    return res.json()

def process_and_save():
    try:
        raw_data = fetch_data()
        records = raw_data.get("records", {})
        data_list = records.get("data", [])

        spot = float(records.get("underlyingValue", 0))
        if spot == 0 and data_list:
            spot = float(data_list[0].get("PE", {}).get("underlyingValue") or data_list[0].get("CE", {}).get("underlyingValue") or 0)

        atm = int(round(spot / 50.0) * 50)
        expiry_dates = records.get("expiryDates", [])
        current_expiry = expiry_dates[0] if expiry_dates else "--"

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

        print("data.json generated successfully.")

    except Exception as e:
        print(f"Failed to fetch data: {e}")
        # Re-raise to flag failure in GitHub Actions UI if it fails completely
        raise e

if __name__ == "__main__":
    process_and_save()
