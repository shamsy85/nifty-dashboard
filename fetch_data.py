import json
from datetime import datetime
import requests

# Standard headers to prevent 403 Forbidden errors from NSE
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


def fetch_nse_option_chain():
    """Establishes session cookies with NSE and fetches live option chain data."""
    session = requests.Session()
    # 1. Visit main page first to get session cookies
    session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)

    # 2. Fetch Option Chain endpoint
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    response = session.get(url, headers=HEADERS, timeout=10)

    if response.status_code != 200:
        raise ConnectionError(
            f"Failed to fetch data from NSE API. HTTP Status: {response.status_code}"
        )

    return response.json()


def process_and_save():
    nse_data = fetch_nse_option_chain()

    records = nse_data["records"]
    filtered = nse_data["filtered"]["data"]

    # Underlying NIFTY Spot Price & Expiry Details
    spot_price = float(records["underlyingValue"])
    current_date = datetime.now().strftime("%d-%b-%Y").upper()
    expiry_date = records["expiryDates"][0].upper()

    # ATM Strike (Nearest 50)
    atm_strike = int(round(spot_price / 50.0) * 50)

    # Extract ATM Option Data
    strike_map = {item["strikePrice"]: item for item in filtered}
    atm_data = strike_map.get(atm_strike, {})

    ce_close = float(atm_data.get("CE", {}).get("lastPrice", 0.0))
    pe_close = float(atm_data.get("PE", {}).get("lastPrice", 0.0))

    banner_total = round(ce_close + pe_close, 2)

    # Save to data.json
    output_data = {
        "spotPrice": spot_price,
        "expiryDate": expiry_date,
        "currentDate": current_date,
        "atmStrike": atm_strike,
        "bannerTotal": banner_total,
        "ce": {"close": ce_close},
        "pe": {"close": pe_close},
    }

    with open("data.json", "w") as f:
        json.dump(output_data, f, indent=2)

    print(
        f"Updated data.json successfully for {current_date} (Expiry: {expiry_date})"
    )


if __name__ == "__main__":
    process_and_save()
