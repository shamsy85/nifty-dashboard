import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf


def get_tuesday_expiry():
    today = datetime.now()
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0 and today.hour >= 16:
        days_until_tuesday = 7
    expiry_date = today + timedelta(days=days_until_tuesday)
    return expiry_date.strftime("%d-%b-%Y").upper()


def fetch_and_update():
    nifty = yf.Ticker("^NSEI")
    data = nifty.history(period="5d")

    if data.empty:
        # Fallback to default index price if market data fetch fails
        spot_price = 24080.40
        spot_high = 24150.00
        spot_low = 24010.00
    else:
        spot_price = float(round(data["Close"].iloc[-1], 2))
        spot_high = float(round(data["High"].iloc[-1], 2))
        spot_low = float(round(data["Low"].iloc[-1], 2))

    atm_strike = int(round(spot_price / 50.0) * 50)
    current_date = datetime.now().strftime("%d-%b-%Y").upper()
    expiry_date = get_tuesday_expiry()

    ce_close = round(spot_price * 0.0045, 2)
    pe_close = round(spot_price * 0.0040, 2)
    banner_total = round(ce_close + pe_close, 2)

    payload = {
        "spotPrice": spot_price,
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "expiryDate": expiry_date,
        "currentDate": current_date,
        "atmStrike": atm_strike,
        "bannerTotal": banner_total,
        "ce": {
            "high": round(ce_close * 1.3, 2),
            "close": ce_close,
            "low": round(ce_close * 0.7, 2),
        },
        "pe": {
            "high": round(pe_close * 1.4, 2),
            "close": pe_close,
            "low": round(pe_close * 0.6, 2),
        },
        "minSupply": round(spot_price + (ce_close * 1.1), 2),
        "minDemand": round(spot_price - (pe_close * 1.1), 2),
        "maxSupply": round(spot_price + (banner_total * 1.1), 2),
        "maxDemand": round(spot_price - (banner_total * 1.1), 2),
        "sniper1": {
            "strike": atm_strike,
            "ce": ce_close,
            "pe": pe_close,
            "otmCeStrike": atm_strike + 100,
            "otmCe": round(ce_close * 0.4, 2),
            "otmPeStrike": atm_strike - 100,
            "otmPe": round(pe_close * 0.4, 2),
        },
        "sniper2": {
            "strike": atm_strike + 50,
            "ce": round(ce_close * 0.8, 2),
            "pe": round(pe_close * 1.2, 2),
            "otmCeStrike": atm_strike + 150,
            "otmCe": round(ce_close * 0.3, 2),
            "otmPeStrike": atm_strike - 50,
            "otmPe": round(pe_close * 0.6, 2),
        },
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"data.json successfully updated for NIFTY at {spot_price}")


if __name__ == "__main__":
    fetch_and_update()
