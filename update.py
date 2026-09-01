
import requests
import json
import time
from datetime import datetime

HOME = "https://www.nseindia.com/"
API = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/138.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
    "Origin": "https://www.nseindia.com",
    "Connection": "keep-alive",
}

session = requests.Session()
session.headers.update(headers)

# Get NSE cookies first
session.get(HOME, timeout=20)
time.sleep(2)

r = session.get(API, timeout=20)

# Retry once if NSE blocks the request
if r.status_code != 200:
    session.get(HOME, timeout=20)
    time.sleep(2)
    r = session.get(API, timeout=20)

r.raise_for_status()

data = r.json()

spot = data["records"]["underlyingValue"]
expiry = data["records"]["expiryDates"][0]
atm = round(spot / 50) * 50

ce = pe = None

for item in data["records"]["data"]:
    if item["strikePrice"] == atm:
        ce = item.get("CE")
        pe = item.get("PE")
        break

output = {
    "currentDate": datetime.now().strftime("%d %b %Y"),
    "expiryDate": expiry,
    "spotPrice": spot,
    "atmStrike": atm,

    "ce": {
        "high": ce["highPrice"],
        "close": ce["lastPrice"],
        "low": ce["lowPrice"]
    },

    "pe": {
        "high": pe["highPrice"],
        "close": pe["lastPrice"],
        "low": pe["lowPrice"]
    },

    "bannerTotal": ce["lastPrice"] + pe["lastPrice"],

    "spotHigh": spot,
    "spotLow": spot,

    "sniper1": {
        "strike": atm,
        "ce": ce["lastPrice"],
        "pe": pe["lastPrice"],
        "otmCeStrike": atm + 50,
        "otmPeStrike": atm - 50,
        "otmCe": 0,
        "otmPe": 0
    },

    "sniper2": {
        "strike": atm,
        "ce": ce["lastPrice"],
        "pe": pe["lastPrice"],
        "otmCeStrike": atm + 100,
        "otmPeStrike": atm - 100,
        "otmCe": 0,
        "otmPe": 0
    }
}

with open("data.json", "w") as f:
    json.dump(output, f, indent=2)

print("data.json updated successfully")
