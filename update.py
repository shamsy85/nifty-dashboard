import os
import json
import time
import requests
import pandas as pd
from datetime import datetime

# NSE API URL for Option Chain CSV
CSV_URL = "https://www.nseindia.com/api/reports?archives=[%7B%22name%22:%22Option%20Chain%20-%20NIFTY%22,%22type%22:%22csv%22%7D]"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/option-chain",
    "Accept": "*/*"
}

def fetch_option_chain():
    session = requests.Session()
    session.headers.update(headers)

    # Step 1: Initialize cookies by hitting the homepage
    try:
        session.get("https://www.nseindia.com", timeout=15)
        time.sleep(2)  # Delay to simulate human browsing
    except Exception as e:
        print(f"Warning: Failed to initialize home session: {e}")

    # Step 2: Request the CSV download
    response = session.get(CSV_URL, timeout=30)
    response.raise_for_status()

    with open("optionchain.csv", "wb") as f:
        f.write(response.content)

def process_data():
    # NSE CSVs often contain 1 header line before the actual table
    try:
        df = pd.read_csv("optionchain.csv", skiprows=1)
    except Exception:
        # Fallback if skiprows isn't required on certain archive formats
        df = pd.read_csv("optionchain.csv")

    # Clean whitespace from column names
    df.columns = [str(col).strip().upper() for col in df.columns]

    # Convert numeric fields and strip commas (e.g., '22,100.00' -> 22100.00)
    numeric_cols = [
        "STRIKE PRICE", "CE LTP", "CE HIGH", "CE LOW", 
        "PE LTP", "PE HIGH", "PE LOW", "UNDERLYING VALUE"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')

    # Get underlying Spot Price
    spot_series = df["UNDERLYING VALUE"].dropna()
    if spot_series.empty:
        raise ValueError("Could not extract 'UNDERLYING VALUE' from CSV")
    spot = float(spot_series.iloc[0])

    # Compute ATM Strike (Nearest 50)
    atm = int(round(spot / 50.0) * 50)

    # Helper function to get pricing parameters for any strike
    def get_strike_data(strike_price):
        sub_df = df[df["STRIKE PRICE"] == strike_price]
        if sub_df.empty:
            return {"ce_high": 0.0, "ce_close": 0.0, "ce_low": 0.0, "pe_high": 0.0, "pe_close": 0.0, "pe_low": 0.0}
        r = sub_df.iloc[0]
        return {
            "ce_high": float(r.get("CE HIGH", 0) or 0),
            "ce_close": float(r.get("CE LTP", 0) or 0),
            "ce_low": float(r.get("CE LOW", 0) or 0),
            "pe_high": float(r.get("PE HIGH", 0) or 0),
            "pe_close": float(r.get("PE LTP", 0) or 0),
            "pe_low": float(r.get("PE LOW", 0) or 0),
        }

    # Fetch primary ATM options data
    atm_data = get_strike_data(atm)
    
    # Fetch OTM legs for Sniper calculations
    snip1_otm_ce = get_strike_data(atm + 50)
    snip1_otm_pe = get_strike_data(atm - 50)

    snip2_otm_ce = get_strike_data(atm + 100)
    snip2_otm_pe = get_strike_data(atm - 100)

    # Extract Expiry Date
    expiry_series = df["EXPIRY DATE"].dropna() if "EXPIRY DATE" in df.columns else pd.Series(["--"])
    expiry = str(expiry_series.iloc[0]).upper()

    output = {
        "currentDate": datetime.now().strftime("%d %b %Y").upper(),
        "expiryDate": expiry,
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

        "spotHigh": spot + 50.0,  # Proxy range for Earth indicator
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

    print("data.json successfully generated.")

if __name__ == "__main__":
    fetch_option_chain()
    process_data()
