import json
from datetime import datetime
import pandas as pd
import yfinance as yf


def fetch_nifty_data():
    # 1. Fetch Spot NIFTY Data (^NSEI)
    nifty = yf.Ticker("^NSEI")
    todays_data = nifty.history(period="1d")

    if todays_data.empty:
        raise ValueError("Could not fetch Nifty spot data.")

    spot_close = float(todays_data["Close"].iloc[-1])
    spot_high = float(todays_data["High"].iloc[-1])
    spot_low = float(todays_data["Low"].iloc[-1])

    # 2. Dynamic ATM Strike Calculation (Rounded to nearest 50)
    atm_strike = int(round(spot_close / 50.0) * 50)

    # 3. Expiry & Date Formats
    current_date_str = datetime.now().strftime("%d-%b-%Y").upper()

    # Note: Replace dummy values below with your live broker API or option chain fetcher logic
    ce_data = {"high": 145.20, "close": 110.50, "low": 85.00}

    pe_data = {"high": 180.00, "close": 95.30, "low": 60.10}

    banner_total = ce_data["close"] + pe_data["close"]

    # 4. Construct JSON output expected by your index.html script
    payload = {
        "spotPrice": spot_close,
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "expiryDate": "27-MAR-2026",
        "currentDate": current_date_str,
        "atmStrike": atm_strike,
        "bannerTotal": banner_total,
        "ce": ce_data,
        "pe": pe_data,
        "sniper1": {
            "strike": atm_strike,
            "ce": ce_data["close"],
            "pe": pe_data["close"],
            "otmCeStrike": atm_strike + 100,
            "otmCe": 45.20,
            "otmPeStrike": atm_strike - 100,
            "otmPe": 38.10,
        },
        "sniper2": {
            "strike": atm_strike + 50,
            "ce": 88.00,
            "pe": 120.40,
            "otmCeStrike": atm_strike + 150,
            "otmCe": 30.50,
            "otmPeStrike": atm_strike - 50,
            "otmPe": 65.20,
        },
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print("data.json successfully updated.")


if __name__ == "__main__":
    fetch_nifty_data()
