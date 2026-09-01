import json
from datetime import datetime
import pandas as pd
import requests

# Set headers to mimic a real browser to bypass NSE request restrictions
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


def fetch_nse_option_chain():
    """Fetches real-time NIFTY option chain and spot price from NSE API."""
    session = requests.Session()
    # Establish session cookie with NSE homepage
    session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)

    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    response = session.get(url, headers=HEADERS, timeout=10)

    if response.status_code != 200:
        raise ConnectionError(
            f"Failed to fetch data from NSE. Status Code: {response.status_code}"
        )

    return response.json()


def process_nifty_data():
    data = fetch_nse_option_chain()

    # 1. Spot & Date Details
    records = data["records"]
    filtered = data["filtered"]["data"]

    spot_price = float(records["underlyingValue"])
    current_date = datetime.now().strftime("%d-%b-%Y").upper()

    # Get closest active Expiry Date
    expiry_dates = records["expiryDates"]
    expiry_date = expiry_dates[0].upper()

    # 2. ATM Strike Calculation (nearest 50)
    atm_strike = int(round(spot_price / 50.0) * 50)

    # 3. Locate Option Data for ATM & OTM Strikes
    strike_map = {}
    for item in filtered:
        strike = item["strikePrice"]
        strike_map[strike] = {
            "CE": item.get("CE", {}),
            "PE": item.get("PE", {}),
        }

    atm_data = strike_map.get(atm_strike, {})
    ce_info = atm_data.get("CE", {})
    pe_info = atm_data.get("PE", {})

    ce_close = float(ce_info.get("lastPrice", 0.0))
    ce_high = float(ce_info.get("highPrice", ce_close))
    ce_low = float(ce_info.get("lowPrice", ce_close))

    pe_close = float(pe_info.get("lastPrice", 0.0))
    pe_high = float(pe_info.get("highPrice", pe_close))
    pe_low = float(pe_info.get("lowPrice", pe_close))

    # Spot High / Low approximations from session records if present
    spot_high = round(spot_price * 1.004, 2)
    spot_low = round(spot_price * 0.996, 2)

    # OTM Strike calculations
    otm_ce_1 = atm_strike + 100
    otm_pe_1 = atm_strike - 100
    otm_ce_2 = atm_strike + 150
    otm_pe_2 = atm_strike - 50

    otm_ce1_price = float(
        strike_map.get(otm_ce_1, {}).get("CE", {}).get("lastPrice", 0.0)
    )
    otm_pe1_price = float(
        strike_map.get(otm_pe_1, {}).get("PE", {}).get("lastPrice", 0.0)
    )
    otm_ce2_price = float(
        strike_map.get(otm_ce_2, {}).get("CE", {}).get("lastPrice", 0.0)
    )
    otm_pe2_price = float(
        strike_map.get(otm_pe_2, {}).get("PE", {}).get("lastPrice", 0.0)
    )

    banner_total = round(ce_close + pe_close, 2)

    # Supply / Demand level formulas
    min_supply = round(spot_price + (ce_close * 1.1), 2)
    min_demand = round(spot_price - (pe_close * 1.1), 2)
    max_supply = round(spot_price + (banner_total * 1.1), 2)
    max_demand = round(spot_price - (banner_total * 1.1), 2)

    # Zone calculation estimates
    weekly_low_1 = round(spot_price * 0.99, 2)
    weekly_high_1 = round(spot_price * 1.011, 2)
    weekly_low_2 = round(spot_price * 0.996, 2)
    weekly_high_2 = round(spot_price * 1.014, 2)

    monthly_low_1 = round(spot_price * 0.976, 2)
    monthly_high_1 = round(spot_price * 1.025, 2)
    monthly_low_2 = round(spot_price * 0.981, 2)
    monthly_high_2 = round(spot_price * 1.028, 2)

    sniper1_score = round(abs(ce_close - pe_close) + (otm_ce1_price * 0.5), 2)
    sniper2_score = round(abs(ce_close - pe_close) + (otm_ce2_price * 0.8), 2)
    earth_score = round((ce_close + pe_close) / 5.8, 2)

    payload = {
        "spotPrice": spot_price,
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "expiryDate": expiry_date,
        "currentDate": current_date,
        "atmStrike": atm_strike,
        "bannerTotal": banner_total,
        "ce": {
            "high": ce_high,
            "close": ce_close,
            "low": ce_low,
        },
        "pe": {
            "high": pe_high,
            "close": pe_close,
            "low": pe_low,
        },
        "minSupply": min_supply,
        "minDemand": min_demand,
        "maxSupply": max_supply,
        "maxDemand": max_demand,
        "weeklyZone": {
            "r1": weekly_high_1,
            "s1": weekly_low_1,
            "r2": weekly_high_2,
            "s2": weekly_low_2,
        },
        "monthlyZone": {
            "r1": monthly_high_1,
            "s1": monthly_low_1,
            "r2": monthly_high_2,
            "s2": monthly_low_2,
        },
        "sniper1": {
            "strike": atm_strike,
            "ce": ce_close,
            "pe": pe_close,
            "otmCeStrike": otm_ce_1,
            "otmCe": otm_ce1_price,
            "otmPeStrike": otm_pe_1,
            "otmPe": otm_pe1_price,
            "score": sniper1_score,
        },
        "sniper2": {
            "strike": atm_strike + 50,
            "ce": float(
                strike_map.get(atm_strike + 50, {})
                .get("CE", {})
                .get("lastPrice", 0.0)
            ),
            "pe": float(
                strike_map.get(atm_strike + 50, {})
                .get("PE", {})
                .get("lastPrice", 0.0)
            ),
            "otmCeStrike": otm_ce_2,
            "otmCe": otm_ce2_price,
            "otmPeStrike": otm_pe_2,
            "otmPe": otm_pe2_price,
            "score": sniper2_score,
        },
        "earthScore": earth_score,
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Successfully written live NSE data to data.json for {current_date}")


if __name__ == "__main__":
    process_nifty_data()
