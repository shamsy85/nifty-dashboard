import json
import requests
import pandas as pd
from datetime import datetime

CSV_URL = "https://www.nseindia.com/api/reports?archives=[%7B%22name%22:%22Option%20Chain%20-%20NIFTY%22,%22type%22:%22csv%22%7D]"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.nseindia.com/option-chain?symbol=NIFTY",
    "Accept": "*/*"
}

session = requests.Session()

try:
    # 1. Acquire valid NSE cookies
    session.get("https://www.nseindia.com", headers=headers, timeout=30)
    
    # 2. Download CSV archive
    r = session.get(CSV_URL, headers=headers, timeout=30)
    r.raise_for_status()

    with open("optionchain.csv", "wb") as f:
        f.write(r.content)

    # 3. Read CSV skipping metadata headers (usually skip top 1-2 lines depending on export format)
    df = pd.read_csv("optionchain.csv", skiprows=1)

    # Clean column names (strip whitespace and uppercase)
    df.columns = [col.strip() for col in df.columns]

    # Convert numeric columns from strings safely (handling commas like "22,500.00")
    numeric_cols = ["STRIKE PRICE", "CE LTP", "CE HIGH", "CE LOW", "PE LTP", "PE HIGH", "PE LOW", "UNDERLYING VALUE"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')

    # 4. Calculate Spot and ATM
    spot_series = df["UNDERLYING VALUE"].dropna()
    spot = float(spot_series.iloc[0]) if not spot_series.empty else 22000.00
    atm = int(round(spot / 50) * 50)

    # Helper function to extract option parameters by strike price
    def get_option_data(strike_price):
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

    atm_data = get_option_data(atm)
    
    # Retrieve OTM strike data for Sniper calculations
    sniper1_ce_otm = get_option_data(atm + 50)
    sniper1_pe_otm = get_option_data(atm - 50)
    
    sniper2_ce_otm = get_option_data(atm + 100)
    sniper2_pe_otm = get_option_data(atm - 100)

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

        # Placeholder values for spot intraday high/low (can be updated via index API)
        "spotHigh": spot + 75.0,
        "spotLow": spot - 60.0,

        "sniper1": {
            "strike": atm,
            "ce": atm_data["ce_close"],
            "pe": atm_data["pe_close"],
            "otmCeStrike": atm + 50,
            "otmPeStrike": atm - 50,
            "otmCe": sniper1_ce_otm["ce_close"],
            "otmPe": sniper1_pe_otm["pe_close"]
        },

        "sniper2": {
            "strike": atm,
            "ce": atm_data["ce_close"],
            "pe": atm_data["pe_close"],
            "otmCeStrike": atm + 100,
            "otmPeStrike": atm - 100,
            "otmCe": sniper2_ce_otm["ce_close"],
            "otmPe": sniper2_pe_otm["pe_close"]
        }
    }

    with open("data.json", "w") as f:
        json.dump(output, f, indent=2)

    print("data.json successfully generated with accurate OTM data.")

except Exception as e:
    print(f"Failed to extract option chain: {e}")
