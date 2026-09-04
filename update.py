import datetime
import json
import os
import requests
import time

def load_access_token():
    if os.path.exists("access_token.txt"):
        with open("access_token.txt", "r") as f:
            return f.read().strip()
    return os.getenv("UPSTOX_ACCESS_TOKEN", "")

def get_current_expiry():
    access_token = load_access_token()
    instrument_key = "NSE_INDEX|Nifty 50"
    url = f"https://api.upstox.com/v2/option/contract?instrument_key={instrument_key}"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    market_closed = now.hour > 15 or (now.hour == 15 and now.minute >= 30)
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        res_json = response.json()
        expiry_list = res_json.get("data", [])
        if expiry_list:
            expiry_list.sort()
            
            if today_str in expiry_list and not market_closed:
                return today_str
                
            for exp in expiry_list:
                if exp > today_str:
                    return exp
                elif exp == today_str and not market_closed:
                    return exp
            
            return expiry_list[-1]
            
    return today_str

def fetch_option_chain_data():
    access_token = load_access_token()
    if not access_token:
        print("Error: Access token not found.")
        return None

    instrument_key = "NSE_INDEX|Nifty 50"
    expiry_date = get_current_expiry()
    url = f"https://api.upstox.com/v2/option/chain?instrument_key={instrument_key}&expiry_date={expiry_date}"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def write_status_to_json(status_flag):
    payload = {
        "dataStatus": status_flag,
        "currentDate": datetime.datetime.now().strftime("%d %b %Y").upper()
    }
    with open("data.json", "w") as f:
        json.dump(payload, f, indent=4)

def update_dashboard_with_retry(max_retries=3, delay=120):
    for attempt in range(1, max_retries + 1):
        print(f"Attempt {attempt} of {max_retries} to fetch market data...")
        
        res_json = fetch_option_chain_data()
        if res_json:
            data = res_json.get("data", [])
            if data:
                process_and_save_data(res_json)
                return True
                
        if attempt < max_retries:
            print(f"Data not fully active yet. Waiting {delay} seconds before retrying...")
            time.sleep(delay)
            
    write_status_to_json("PENDING")
    print("All attempts failed. Marked data status as PENDING.")
    return False

def process_and_save_data(res_json):
    data = res_json.get("data", [])
    spot = float(res_json.get("spot_price", 0.0))
    if spot == 0.0 and data:
        spot = float(data[0].get("spot_price", 0.0))

    # 1. HLC ATM (min absolute difference between CE and PE)
    min_diff = float('inf')
    hlc_atm_strike = 0
    ce_close, ce_high, ce_low = 0.0, 0.0, 0.0
    pe_close, pe_high, pe_low = 0.0, 0.0, 0.0

    for item in data:
        item_strike = item.get("strike_price")
        if item_strike is None:
            continue
        
        s_val = float(item_strike)
        call_opts = item.get("call_options", {})
        put_opts = item.get("put_options", {})
        
        m_call = call_opts.get("market_data", {})
        m_put = put_opts.get("market_data", {})
        
        ce_ltp = float(call_opts.get("last_price") or m_call.get("ltp") or 0.0)
        pe_ltp = float(put_opts.get("last_price") or m_put.get("ltp") or 0.0)
        
        diff = abs(ce_ltp - pe_ltp)
        if diff < min_diff:
            min_diff = diff
            hlc_atm_strike = int(s_val)
            ce_close = ce_ltp
            pe_close = pe_ltp
            ce_high = float(call_opts.get("high_price") or m_call.get("high_price") or ce_ltp)
            ce_low = float(call_opts.get("low_price") or m_call.get("low_price") or ce_ltp)
            pe_high = float(put_opts.get("high_price") or m_put.get("high_price") or pe_ltp)
            pe_low = float(put_opts.get("low_price") or m_put.get("low_price") or pe_ltp)

    if hlc_atm_strike == 0 and spot > 0:
        hlc_atm_strike = int(round(spot / 50.0) * 50)

    # 2. Sniper 1 (100-point round) & Sniper 2 (50-point round)
    sniper1_atm_strike = int(round(spot / 100.0) * 100) if spot > 0 else int(round(hlc_atm_strike / 100.0) * 100)
    sniper2_atm_strike = int(round(spot / 50.0) * 50) if spot > 0 else hlc_atm_strike

    target_s1_ce_strike = sniper1_atm_strike + 100
    target_s1_pe_strike = sniper1_atm_strike - 100
    target_s2_ce_strike = sniper2_atm_strike + 100
    target_s2_pe_strike = sniper2_atm_strike - 100

    s1_atm_ce_val, s1_atm_pe_val = 0.0, 0.0
    s2_atm_ce_val, s2_atm_pe_val = 0.0, 0.0
    s1_ce_val, s1_pe_val = 0.0, 0.0
    s2_ce_val, s2_pe_val = 0.0, 0.0

    for item in data:
        item_strike = item.get("strike_price")
        if item_strike is None:
            continue
        
        s_val = float(item_strike)
        call_opts = item.get("call_options", {})
        put_opts = item.get("put_options", {})
        
        m_call = call_opts.get("market_data", {})
        m_put = put_opts.get("market_data", {})
        
        ce_ltp = float(call_opts.get("last_price") or m_call.get("ltp") or 0.0)
        pe_ltp = float(put_opts.get("last_price") or m_put.get("ltp") or 0.0)
        
        if s_val == sniper1_atm_strike:
            s1_atm_ce_val = ce_ltp
            s1_atm_pe_val = pe_ltp
        if s_val == sniper2_atm_strike:
            s2_atm_ce_val = ce_ltp
            s2_atm_pe_val = pe_ltp
            
        if s_val == target_s1_ce_strike:
            s1_ce_val = ce_ltp
        elif s_val == target_s1_pe_strike:
            s1_pe_val = pe_ltp
        elif s_val == target_s2_ce_strike:
            s2_ce_val = ce_ltp
        elif s_val == target_s2_pe_strike:
            s2_pe_val = pe_ltp

    payload = {
        "dataStatus": "SUCCESS",
        "currentDate": datetime.datetime.now().strftime("%d %b %Y").upper(),
        "expiryDate": datetime.datetime.strptime(get_current_expiry(), "%Y-%m-%d").strftime("%d-%b-%Y").upper(),
        "spotPrice": spot,
        "hlcAtmStrike": hlc_atm_strike,
        "ce": {
            "high": round(ce_high, 2), 
            "close": round(ce_close, 2), 
            "low": round(ce_low, 2)
        },
        "pe": {
            "high": round(pe_high, 2), 
            "close": round(pe_close, 2), 
            "low": round(pe_low, 2)
        },
        "bannerTotal": round(ce_close - pe_close, 2),
        "spotHigh": float(res_json.get("spot_high", spot)),
        "spotLow": float(res_json.get("spot_low", spot)),
        "sniper1": {
            "strike": sniper1_atm_strike, 
            "ce": round(s1_atm_ce_val, 2), 
            "pe": round(s1_atm_pe_val, 2),
            "otmCeStrike": target_s1_ce_strike, 
            "otmPeStrike": target_s1_pe_strike,
            "otmCe": round(s1_ce_val, 2), 
            "otmPe": round(s1_pe_val, 2)
        },
        "sniper2": {
            "strike": sniper2_atm_strike, 
            "ce": round(s2_atm_ce_val, 2), 
            "pe": round(s2_atm_pe_val, 2),
            "otmCeStrike": target_s2_ce_strike, 
            "otmPeStrike": target_s2_pe_strike,
            "otmCe": round(s2_ce_val, 2), 
            "otmPe": round(s2_pe_val, 2)
        }
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=4)
        
    print("Dashboard data updated successfully from Upstox API.")

if __name__ == "__main__":
    update_dashboard_with_retry()
