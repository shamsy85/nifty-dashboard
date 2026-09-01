import json
import time
from datetime import datetime
from curl_cffi import requests as crequests

def fetch_nifty_data():
    # Create session impersonating a modern browser TLS signature
    session = crequests.Session(impersonate="chrome120")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
    }

    print("Fetching homepage to establish session cookies...")
    session.get("https://www.nseindia.com", headers=headers, timeout=15)
    time.sleep(2)

    print("Fetching option chain API data...")
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    response = session.get(url, headers=headers, timeout=15)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")

def process_and_save():
    try:
        raw_data = fetch_nifty_data()
        records = raw_data.get("records", {})
        data_list = records.get("data", [])
        
        spot = float(records.get("underlyingValue", 0.0))
        expiries = records.get("expiryDates", [])
        current_expiry = expiries[0] if expiries else "--"

        # Calculate ATM strike (rounded to nearest 50)
        atm = int(round(spot / 50.0) * 50)

        # Helper to extract strike data cleanly
        def get_strike_row(strike):
            for item in data_list:
                if item.get("expiryDate") == current_expiry and item.get("strikePrice") == strike:
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
            return {"ce_high": 0, "ce_close": 0, "ce_low": 0, "pe_high": 0, "pe_close": 0, "pe_low": 0}

        atm_data = get_strike_row(atm)
        snip1_otm_ce = get_strike_row(atm + 50)
        snip1_otm_pe = get_strike_row(atm - 50)
        snip2_otm_ce = get_strike_row(atm + 100)
        snip2_otm_pe = get_strike_row(atm - 100)

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

        print("data.json successfully updated!")

    except Exception as e:
        print(f"Failed to fetch data: {e}")
        raise e

if __name__ == "__main__":
    process_and_save()
