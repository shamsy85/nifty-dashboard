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

def fetch_option_candles(instrument_key, headers):
    """Fetches intraday candles to get accurate High, Low, and Close."""
    try:
        encoded_key = requests.utils.quote(instrument_key, safe='')
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        url = f"https://api.upstox.com/v2/historical-candle/{encoded_key}/day/{today_str}"
        
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            candles = res.json().get("data", {}).get("candles", [])
            if candles:
                latest_candle = candles[0]
                return float(latest_candle[2]), float(latest_candle[4]), float(latest_candle[3])
    except Exception as e:
        print(f"Candle fetch error for {instrument_key}: {e}")
    return 0.0, 0.0, 0.0

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

    fallback_atm = int(round(spot / 50.0) * 50) if spot > 0 else 0
    atm_strike = fallback_atm
    
    ce_high, ce_low, ce_close = 0.0, 0.0, 0.0
    pe_high, pe_low, pe_close = 0.0, 0.0, 0.0
    min_diff = 0.0
    
    headers = get_upstox_headers()
    call_key, put_key = None, None

    if headers.get("Authorization") != "Bearer ":
        try:
            expiry_date = get_current_expiry()
            print(f"Querying Upstox Option Chain for active expiry: {expiry_date}...")
            url = f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty%2050&expiry_date={expiry_date}"
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.status_code == 200:
                data = response.json().get("data", [])
                
                # 2. Find the strike with the SMALLEST absolute difference between CE and PE
                min_diff = float('inf')
                best_strike_entry = None
                
                for item in data:
                    item_strike = item.get("strike_price")
                    if item_strike is None:
                        continue
                        
                    call_opts = item.get("call_options", {})
                    put_opts = item.get("put_options", {})
                    
                    m_call = call_opts.get("market_data", {})
                    m_put = put_opts.get("market_data", {})
                    
                    ce_ltp = float(call_opts.get("last_price") or m_call.get("ltp") or 0.0)
                    pe_ltp = float(put_opts.get("last_price") or m_put.get("ltp") or 0.0)
                    
                    if ce_ltp > 0 and pe_ltp > 0:
                        diff = abs(ce_ltp - pe_ltp)
                        if diff < min_diff:
                            min_diff = diff
                            best_strike_entry = item
                            atm_strike = int(item_strike)

                if not best_strike_entry:
                    atm_strike = fallback_atm
                    min_diff = 0.0
                    for item in data:
                        if item.get("strike_price") and float(item.get("strike_price")) == float(fallback_atm):
                            best_strike_entry = item
                            break

                if best_strike_entry:
                    call_opts = best_strike_entry.get("call_options", {})
                    put_opts = best_strike_entry.get("put_options", {})
                    
                    call_key = call_opts.get("instrument_key")
                    put_key = put_opts.get("instrument_key")
                    
                    m_call = call_opts.get("market_data", {})
                    m_put = put_opts.get("market_data", {})
                    ce_close = float(call_opts.get("last_price") or m_call.get("ltp") or 0.0)
                    pe_close = float(put_opts.get("last_price") or m_put.get("ltp") or 0.0)

                print(f"Calculated Min-Difference ATM Strike: {atm_strike} (CE-PE Difference: {min_diff})")
                
                # 3. Fetch precise candles for High, Low, and Close
                if call_key:
                    h, c, l = fetch_option_candles(call_key, headers)
                    if h > 0: ce_high = h
                    if c > 0: ce_close = c
                    if l > 0: ce_low = l
                    if ce_high == 0.0: ce_high = ce_close
                    if ce_low == 0.0: ce_low = ce_close

                if put_key:
                    h, c, l = fetch_option_candles(put_key, headers)
                    if h > 0: pe_high = h
                    if c > 0: pe_close = c
                    if l > 0: pe_low = l
                    if pe_high == 0.0: pe_high = pe_close
                    if pe_low == 0.0: pe_low = pe_close

                print(f"Resolved -> CE [H:{ce_high}, C:{ce_close}, L:{ce_low}] | PE [H:{pe_high}, C:{pe_close}, L:{pe_low}]")
            else:
                print(f"Option Chain error: {response.text}")
        except Exception as err:
            print(f"Request exception: {err}")

    # Fallback calculation if min_diff wasn't set from the loop
    if min_diff == float('inf') or min_diff == 0.0:
        min_diff = abs(ce_close - pe_close)

    # 4. Save JSON Payload (bannerTotal now stores the minimum difference value directly)
    payload = {
        "currentDate": datetime.datetime.now().strftime("%d %b %Y").upper(),
        "expiryDate": datetime.datetime.strptime(get_current_expiry(), "%Y-%m-%d").strftime("%d-%b-%Y").upper(),
        "spotPrice": spot,
        "atmStrike": atm_strike,
        "ce": {"high": round(ce_high, 2), "close": round(ce_close, 2), "low": round(ce_low, 2)},
        "pe": {"high": round(pe_high, 2), "close": round(pe_close, 2), "low": round(pe_low, 2)},
        "bannerTotal": round(min_diff, 2),
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "sniper1": {
            "strike": atm_strike, "ce": round(ce_close, 2), "pe": round(pe_close, 2),
            "otmCeStrike": atm_strike + 50, "otmPeStrike": atm_strike - 50,
            "otmCe": round(ce_close * 0.70, 2), "otmPe": round(pe_close * 0.68, 2)
        },
        "sniper2": {
            "strike": atm_strike, "ce": round(ce_close, 2), "pe": round(pe_close, 2),
            "otmCeStrike": atm_strike + 100, "otmPeStrike": atm_strike - 100,
            "otmCe": round(ce_close * 0.48, 2), "otmPe": round(pe_close * 0.46, 2)
        }
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Pipeline executed successfully. Spot: {spot} | ATM: {atm_strike} | Min Diff: {min_diff}")

if __name__ == "__main__":
    fetch_and_build_dashboard()
