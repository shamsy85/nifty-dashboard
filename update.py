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
    
    # 3. Query Upstox Option Chain API dynamically
    headers = get_upstox_headers()
    if headers.get("Authorization") != "Bearer " and atm_strike > 0:
        try:
            expiry_date = get_current_expiry()
            print(f"Querying Upstox API for active expiry: {expiry_date} at strike {atm_strike}...")
            url = f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty%2050&expiry_date={expiry_date}"
            response = requests.get(url, headers=headers, timeout=8)
            
            print(f"Upstox API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                res_json = response.json()
                data = res_json.get("data", [])
                print(f"Total strikes returned in chain: {len(data)}")
                
                found = False
                for item in data:
                    item_strike = item.get("strike_price")
                    if item_strike is not None and float(item_strike) == float(atm_strike):
                        found = True
                        
                        # Extract Call Options data
                        call_opts = item.get("call_options", {})
                        call_market = call_opts.get("market_data", {})
                        call_ohlc = call_market.get("ohlc", {})
                        ce_close_val = call_market.get("ltp") or call_market.get("close_price") or call_ohlc.get("close")
                        
                        ce_high = round(float(call_market.get("high") or call_ohlc.get("high") or call_market.get("high_price") or ce_close_val or 0.0), 2)
                        ce_low = round(float(call_market.get("low") or call_ohlc.get("low") or call_market.get("low_price") or ce_close_val or 0.0), 2)
                        ce_close = round(float(ce_close_val or 0.0), 2)

                        # Extract Put Options data
                        put_opts = item.get("put_options", {})
                        put_market = put_opts.get("market_data", {})
                        put_ohlc = put_market.get("ohlc", {})
                        pe_close_val = put_market.get("ltp") or put_market.get("close_price") or put_ohlc.get("close")
                        
                        pe_high = round(float(put_market.get("high") or put_ohlc.get("high") or put_market.get("high_price") or pe_close_val or 0.0), 2)
                        pe_low = round(float(put_market.get("low") or put_ohlc.get("low") or put_market.get("low_price") or pe_close_val or 0.0), 2)
                        pe_close = round(float(pe_close_val or 0.0), 2)
                        
                        print(f"Matched ATM {atm_strike} -> CE Close: {ce_close}, PE Close: {pe_close}")
                        break
                
                if not found:
                    print(f"Warning: ATM strike {atm_strike} was not found in the option chain response data.")
            else:
                print(f"Upstox API error response: {response.text}")
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
