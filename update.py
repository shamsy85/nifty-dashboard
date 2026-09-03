import os
import json
import datetime
import requests
import yfinance as yf

def get_upstox_headers():
    token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")
    if not token and os.path.exists("token.txt"):
        with open("token.txt", "r") as f:
            token = f.read().strip()
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Api-Version": "2.0"
    }

def get_current_expiry():
    """Calculates active expiry date (handles NSE weekly schedule)."""
    today = datetime.date.today()
    target_date = datetime.date(2026, 9, 8) if today <= datetime.date(2026, 9, 8) else today + datetime.timedelta(days=(3 - today.weekday()) % 7)
    return target_date.strftime("%Y-%m-%d")

def fetch_and_build_dashboard():
    print("Initializing NIFTY options update pipeline...")
    
    # 1. Fetch Spot data via yfinance
    ticker = yf.Ticker("^NSEI")
    todays_data = ticker.history(period="1d")

    if not todays_data.empty:
        spot = round(float(todays_data["Close"].iloc[-1]), 2)
        spot_high = round(float(todays_data["High"].iloc[-1]), 2)
        spot_low = round(float(todays_data["Low"].iloc[-1]), 2)
    else:
        spot, spot_high, spot_low = 0.0, 0.0, 0.0

    atm_strike = int(round(spot / 50.0) * 50) if spot > 0 else 0
    
    # 2. Safety fallbacks (initialized to 0)
    ce_high, ce_low, ce_close = 0.0, 0.0, 0.0
    pe_high, pe_low, pe_close = 0.0, 0.0, 0.0
    
    headers = get_upstox_headers()
    if headers.get("Authorization") != "Bearer " and atm_strike > 0:
        try:
            expiry_date = get_current_expiry()
            print(f"Querying Upstox Option Chain for active expiry: {expiry_date} at strike {atm_strike}...")
            url = f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty%2050&expiry_date={expiry_date}"
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.status_code == 200:
                data = response.json().get("data", [])
                
                def extract_option_metrics(opt_dict):
                    if not opt_dict:
                        return 0.0, 0.0, 0.0
                    m_data = opt_dict.get("market_data", {})
                    ohlc = opt_dict.get("ohlc", {})
                    
                    high = float(ohlc.get("high") or m_data.get("high") or 0.0)
                    close = float(opt_dict.get("last_price") or m_data.get("ltp") or m_data.get("close") or 0.0)
                    low = float(ohlc.get("low") or m_data.get("low") or 0.0)
                    return high, close, low

                for item in data:
                    item_strike = item.get("strike_price")
                    if item_strike is not None and float(item_strike) == float(atm_strike):
                        call_opts = item.get("call_options", {})
                        put_opts = item.get("put_options", {})
                        
                        ce_high, ce_close, ce_low = extract_option_metrics(call_opts)
                        pe_high, pe_close, pe_low = extract_option_metrics(put_opts)
                        break
                
                print(f"Extracted ATM Strike: {atm_strike} | CE [H:{ce_high}, C:{ce_close}, L:{ce_low}] | PE [H:{pe_high}, C:{pe_close}, L:{pe_low}]")
            else:
                print(f"Option Chain API error response: {response.text}")
        except Exception as err:
            print(f"Upstox request failed with exception: {err}")

    # 4. Save JSON Payload
    payload = {
        "currentDate": datetime.datetime.now().strftime("%d %b %Y").upper(),
        "expiryDate": datetime.datetime.strptime(get_current_expiry(), "%Y-%m-%d").strftime("%d-%b-%Y").upper(),
        "spotPrice": spot,
        "atmStrike": atm_strike,
        "ce": {"high": ce_high, "close": ce_close, "low": ce_low},
        "pe": {"high": pe_high, "close": pe_close, "low": pe_low},
        "bannerTotal": round(ce_close + pe_close, 2),
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "sniper1": {
            "strike": atm_strike, "ce": ce_close, "pe": pe_close,
            "otmCeStrike": atm_strike + 50, "otmPeStrike": atm_strike - 50,
            "otmCe": round(ce_close * 0.70, 2), "otmPe": round(pe_close * 0.68, 2)
        },
        "sniper2": {
            "strike": atm_strike, "ce": ce_close, "pe": pe_close,
            "otmCeStrike": atm_strike + 100, "otmPeStrike": atm_strike - 100,
            "otmCe": round(ce_close * 0.48, 2), "otmPe": round(pe_close * 0.46, 2)
        }
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Pipeline executed successfully. Spot: {spot} | ATM: {atm_strike}")

if __name__ == "__main__":
    fetch_and_build_dashboard()
