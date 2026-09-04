import datetime
import json
import os
import requests

def get_current_expiry():
    return "2026-09-10"

def load_access_token():
    if os.path.exists("access_token.txt"):
        with open("access_token.txt", "r") as f:
            return f.read().strip()
    return os.getenv("UPSTOX_ACCESS_TOKEN", "")

def update_dashboard():
    access_token = load_access_token()
    if not access_token:
        print("Error: Access token not found. Please ensure get_token.py saves the token or set UPSTOX_ACCESS_TOKEN.")
        return

    instrument_key = "NSE_INDEX|Nifty 50"
    expiry_date = get_current_expiry()
    url = f"https://api.upstox.com/v2/option/chain?instrument_key={instrument_key}&expiry_date={expiry_date}"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch option chain data. Status: {response.status_code}, Response: {response.text}")
        return

    res_json = response.json()
    data = res_json.get("data", [])
    
    spot = float(res_json.get("spot_price", 0.0))
    if spot == 0.0 and data:
        spot = float(data[0].get("spot_price", 0.0))

    # 1. Initialize variables for HLC ATM (min absolute difference between CE and PE)
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
            pe_high = float(put_opts.get("high_price") or m_call.get("high_price") or pe_ltp)
            pe_low = float(put_opts.get("low_price") or m_call.get("low_price") or pe_ltp)

    if hlc_atm_strike == 0 and spot > 0:
        hlc_atm_strike = int(round(spot / 50.0) * 50)

    # 2. Sniper ATM explicitly rounded to the nearest 100
    sniper_atm_strike = int(round(spot / 100.0) * 100) if spot > 0 else int(round(hlc_atm_strike / 100.0) * 100)

    target_s1_ce_strike = sniper_atm_strike + 100
    target_s1_pe_strike = sniper_atm_strike - 100
    target_s2_ce_strike = sniper_atm_strike + 200
    target_s2_pe_strike = sniper_atm_strike - 200

    # Values storage
    s_atm_ce_val, s_atm_pe_val = 0.0, 0.0
    s1_ce_val, s1_pe_val = 0.0, 0.0
    s2_ce_val, s2_pe_val = 0.0, 0.0

    # Scan option chain to pick up exact prices for Sniper 100-rounded ATM and OTM legs
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
        
        if s_val == sniper_atm_strike:
            s_atm_ce_val = ce_ltp
            s_atm_pe_val = pe_ltp
        elif s_val == target_s1_ce_strike:
            s1_ce_val = ce_ltp
        elif s_val == target_s1_pe_strike:
            s1_pe_val = pe_ltp
        elif s_val == target_s2_ce_strike:
            s2_ce_val = ce_ltp
        elif s_val == target_s2_pe_strike:
            s2_pe_val = pe_ltp

    # 3. Save JSON Payload
    payload = {
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
        "bannerTotal": round(ce_close + pe_close, 2),
        "spotHigh": float(res_json.get("spot_high", spot)),
        "spotLow": float(res_json.get("spot_low", spot)),
        "sniper1": {
            "strike": sniper_atm_strike, 
            "ce": round(s_atm_ce_val, 2), 
            "pe": round(s_atm_pe_val, 2),
            "otmCeStrike": target_s1_ce_strike, 
            "otmPeStrike": target_s1_pe_strike,
            "otmCe": round(s1_ce_val, 2), 
            "otmPe": round(s1_pe_val, 2)
        },
        "sniper2": {
            "strike": sniper_atm_strike, 
            "ce": round(s_atm_ce_val, 2), 
            "pe": round(s_atm_pe_val, 2),
            "otmCeStrike": target_s2_ce_strike, 
            "otmPeStrike": target_s2_pe_strike,
            "otmCe": round(s2_ce_val, 2), 
            "otmPe": round(s2_pe_val, 2)
        }
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=4)
    print("Dashboard data updated successfully with 100-rounded Sniper ATM.")

if __name__ == "__main__":
    update_dashboard()
