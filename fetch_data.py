import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf


def get_current_expiry():
    """Calculates the current/upcoming Tuesday expiry date for NIFTY options."""
    today = datetime.now()
    # Tuesday is weekday index 1 (Monday is 0, Tuesday is 1)
    days_until_tuesday = (1 - today.weekday()) % 7

    # If today is Tuesday after market close (after 4 PM), target next Tuesday's expiry
    if days_until_tuesday == 0 and today.hour >= 16:
        days_until_tuesday = 7

    expiry_date = today + timedelta(days=days_until_tuesday)
    return expiry_date.strftime("%d-%b-%Y").upper()


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

    # 3. Dynamic Date Formats (Tuesday Expiry)
    current_date_str = datetime.now().strftime("%d-%b-%Y").upper()
    expiry_date_str = get_current_expiry()

    # Note: Replace dummy option price values below with your option API data source
    ce_data = {"high": 145.20, "close": 110.50, "low": 85.00}

    pe_data = {"high": 180.00, "close": 95.30, "low": 60.10}

    banner_total = ce_data["close"] + pe_data["close"]

    # 4. Construct JSON payload
    payload = {
        "spotPrice": spot_close,
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "expiryDate": expiry_date_str,
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

    print(
        f"data.json updated: Current Date {current_date_str}, Expiry {expiry_date_str}"
    )


if __name__ == "__main__":
    fetch_nifty_data()
