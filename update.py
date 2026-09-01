
import requests
import json
from datetime import datetime

session = requests.Session()
headers = {"User-Agent": "Mozilla/5.0"}

# Get NSE cookies
session.get("https://www.nseindia.com", headers=headers)

# Fetch Option Chain
url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
data = session.get(url, headers=headers).json()

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

print("data.json updated")
