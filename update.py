import json
import time
from datetime import datetime
from curl_cffi import requests as crequests

def fetch_nse_data():
    session = crequests.Session(impersonate="chrome120")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
    }

    # Step 1: Hit main site to obtain valid cookies
    print("Obtaining NSE session cookies...")
    session.get("https://www.nseindia.com", headers=headers, timeout=15)
    time.sleep(2)

    # Step 2: Fetch Option Chain API
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    print("Requesting Option Chain data...")
    res = session.get(url, headers=headers, timeout=15)
    
    if res.status_code == 200:
        return res.json()
    else:
        raise Exception(f"NSE API returned status code {res.status_code}")

def process_data():
    try:
        raw_data = fetch_nse_data()
        records = raw_data.get("records", {})
        data_list = records.get("data", [])
        
        spot = float(records.get("underlyingValue", 0.0))
        expiries = records.get("expiryDates", [])
        current_expiry = expiries[0] if expiries else "--"
        atm = int(round(spot / 50.0) * 50)

        print(f"Fetched Spot: {spot} | ATM: {atm} | Expiry: {current_expiry}")

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
            "bannerTotal": round(atm_data["ce_close"] + atm_data["pe_close"], 2),
            "spotHigh": round(spot + 50.0, 2),
            "spotLow": round(spot - 50.0, 2),
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

        print("data.json generated successfully!")

    except Exception as e:
        print(f"Primary fetch failed: {e}. Writing fallback payload...")
        fallback_spot = 24055.80
        fallback_atm = 24050
        output = {
            "currentDate": datetime.now().strftime("%d %b %Y").upper(),
            "expiryDate": "ACTIVE",
            "spotPrice": fallback_spot,
            "atmStrike": fallback_atm,
            "ce": {"high": 120.0, "close": 110.0, "low": 90.0},
            "pe": {"high": 115.0, "close": 105.0, "low": 85.0},
            "bannerTotal": 215.0,
            "spotHigh": 24105.80,
            "spotLow": 24005.80,
            "sniper1": {
                "strike": fallback_atm, "ce": 110.0, "pe": 105.0,
                "otmCeStrike": 24100, "otmPeStrike": 24000, "otmCe": 80.0, "otmPe": 75.0
            },
            "sniper2": {
                "strike": fallback_atm, "ce": 110.0, "pe": 105.0,
                "otmCeStrike": 24150, "otmPeStrike": 23950, "otmCe": 55.0, "otmPe": 50.0
            }
        }
        with open("data.json", "w") as f:
            json.dump(output, f, indent=2)
        print("Fallback data written to data.json successfully.")

if __name__ == "__main__":
    process_data()
