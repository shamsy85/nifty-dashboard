import time
import json
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

    # Retry loop for NSE WAF rate-limiting
    for attempt in range(1, 4):
        try:
            print(f"Attempt {attempt}: Initializing NSE session cookies...")
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            time.sleep(2)

            url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
            print("Requesting Option Chain API...")
            res = session.get(url, headers=headers, timeout=10)
            
            if res.status_code == 200:
                print("Successfully fetched live NSE option chain!")
                return res.json()
            else:
                print(f"Attempt {attempt} failed with status code {res.status_code}")
        except Exception as err:
            print(f"Attempt {attempt} encountered error: {err}")
        
        time.sleep(3) # Wait before retry

    raise Exception("All 3 attempts to fetch live NSE option chain data failed.")
