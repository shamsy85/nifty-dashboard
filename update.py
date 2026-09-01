
import requests
import pandas as pd
import json
from datetime import datetime

CSV_URL = "https://www.nseindia.com/api/reports?archives=[%7B%22name%22:%22Option%20Chain%20-%20NIFTY%22,%22type%22:%22csv%22%7D]"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nseindia.com/option-chain?symbol=NIFTY",
    "Accept": "*/*"
}

session = requests.Session()

# Get cookies
session.get("https://www.nseindia.com", headers=headers, timeout=30)

r = session.get(CSV_URL, headers=headers, timeout=30)
r.raise_for_status()

with open("optionchain.csv","wb") as f:
    f.write(r.content)

df = pd.read_csv("optionchain.csv")

# Find underlying value
spot = float(df["Underlying Value"].dropna().iloc[0])

atm = round(spot/50)*50

row = df[df["Strike Price"]==atm].iloc[0]

ce_close = float(row["CE LTP"])
pe_close = float(row["PE LTP"])

output = {
    "currentDate": datetime.now().strftime("%d %b %Y"),
    "expiryDate": str(df["Expiry Date"].dropna().iloc[0]),
    "spotPrice": spot,
    "atmStrike": atm,

    "ce":{
        "high": float(row["CE High Price"]),
        "close": ce_close,
        "low": float(row["CE Low Price"])
    },

    "pe":{
        "high": float(row["PE High Price"]),
        "close": pe_close,
        "low": float(row["PE Low Price"])
    },

    "bannerTotal": ce_close+pe_close,

    "spotHigh": spot,
    "spotLow": spot,

    "sniper1":{
        "strike":atm,
        "ce":ce_close,
        "pe":pe_close,
        "otmCeStrike":atm+50,
        "otmPeStrike":atm-50,
        "otmCe":0,
        "otmPe":0
    },

    "sniper2":{
        "strike":atm,
        "ce":ce_close,
        "pe":pe_close,
        "otmCeStrike":atm+100,
        "otmPeStrike":atm-100,
        "otmCe":0,
        "otmPe":0
    }
}

with open("data.json","w") as f:
    json.dump(output,f,indent=2)

print("data.json created successfully.")
