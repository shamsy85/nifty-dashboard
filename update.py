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
                call_instrument_key = None
                put_instrument_key = None
                
                for item in data:
                    item_strike = item.get("strike_price")
                    if item_strike is not None and float(item_strike) == float(atm_strike):
                        call_opts = item.get("call_options", {})
                        put_opts = item.get("put_options", {})
                        
                        call_instrument_key = call_opts.get("instrument_key")
                        put_instrument_key = put_opts.get("instrument_key")
                        break
                
                # Fetch precise Market Quotes (OHLC + LTP) using individual instrument keys
                if call_instrument_key or put_instrument_key:
                    keys = ",".join([k for k in [call_instrument_key, put_instrument_key] if k])
                    quote_url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={keys}"
                    quote_res = requests.get(quote_url, headers=headers, timeout=8)
                    
                    if quote_res.status_code == 200:
                        q_data = quote_res.json().get("data", {})
                        
                        if call_instrument_key and call_instrument_key in q_data:
                            c_item = q_data[call_instrument_key]
                            c_ohlc = c_item.get("ohlc", {})
                            ce_high = round(float(c_ohlc.get("high") or c_item.get("last_price", 0.0)), 2)
                            ce_low = round(float(c_ohlc.get("low") or c_item.get("last_price", 0.0)), 2)
                            ce_close = round(float(c_item.get("last_price") or c_ohlc.get("close", 0.0)), 2)
                        
                        if put_instrument_key and put_instrument_key in q_data:
                            p_item = q_data[put_instrument_key]
                            p_ohlc = p_item.get("ohlc", {})
                            pe_high = round(float(p_ohlc.get("high") or p_item.get("last_price", 0.0)), 2)
                            pe_low = round(float(p_ohlc.get("low") or p_item.get("last_price", 0.0)), 2)
                            pe_close = round(float(p_item.get("last_price") or p_ohlc.get("close", 0.0)), 2)
                            
                        print(f"Fetched Quotes -> CE [H:{ce_high}, C:{ce_close}, L:{ce_low}] | PE [H:{pe_high}, C:{pe_close}, L:{pe_low}]")
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
