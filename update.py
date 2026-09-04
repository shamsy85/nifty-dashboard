import datetime
import json
import os
import requests

def get_current_expiry():
    # Helper to return your target expiry date string format, e.g., "2026-09-10"
    return "2026-09-10"

def update_dashboard():
    # 1. Fetch Option Chain Data (Replace with your actual API endpoint / authentication headers)
    url = "YOUR_UPSTOX_OPTION_CHAIN_API_URL"
    headers = {"Authorization": "Bearer YOUR_ACCESS_TOKEN"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print("Failed to fetch option chain data.")
        return

    res_json = response.json()
    data = res_json.get("data", [])
    spot = float(res_json.get("spot_price", 0.0))
    spot_high = float(res_json.get("spot_high", spot))
    spot_low = float(res_json.get("spot_low", spot))

    # 2. Initialize variables for HLC ATM (min absolute difference between CE and PE)
    min_diff = float('inf')
    hlc_atm_strike = 0
    ce_close, ce_high, ce_low = 0.0, 0.0, 0.0
    pe_close, pe_high, pe_low = 0.0, 0.0, 0.0

    # Scan option chain to find HLC ATM using min(|CE - PE|)
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

    # 3. Calculate Sniper ATM based on market close / spot rounding to the nearest 100
    sniper_atm_strike = int(round(spot / 100.0) * 100) if spot > 0 else hlc_atm_strike

    target_s1_ce_strike = sniper_atm_strike + 100
    target_s1_pe_strike = sniper_atm_strike - 100
    target_s2_ce_strike = sniper_atm_strike + 200
    target_s2_pe_strike = sniper_atm_strike - 200

    # Initialize sniper values
    s1_ce_close, s1_pe_close = 0.0, 0.0
    s2_ce_close, s2_pe_close = 0.0, 0.0

    # Scan option chain again to pick up exact prices for Sniper strikes
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
        
        if s_val == target_s1_ce_strike:
            s1_ce_close = ce_ltp
        elif s_val == target_s1_pe_strike:
            s1_pe_close = pe_ltp
        elif s_val == target_s2_ce_strike:
            s2_ce_close = ce_ltp
        elif s_val == target_s2_pe_strike:
            s2_pe_close = pe_ltp

    # Calculate Sniper averages: (CE + PE) / 2
    sniper1_avg = round((s1_ce_close + s1_pe_close) / 2.0, 3) if (s1_ce_close > 0 and s1_pe_close > 0) else 0.0
    sniper2_avg = round((s2_ce_close + s2_pe_close) / 2.0, 3) if (s2_ce_close > 0 and s2_pe_close > 0) else 0.0

    # 4. Save JSON Payload with HLC ATM and Sniper ATM
    payload = {
        "currentDate": datetime.datetime.now().strftime("%d %b %Y").upper(),
        "expiryDate": datetime.datetime.strptime(get_current_expiry(), "%Y-%m-%d").strftime("%d-%b-%Y").upper(),
        "spotPrice": spot,
        "hlcAtmStrike": hlc_atm_strike,
        "ce": {"high": round(ce_high, 2), "close": round(ce_close, 2), "low": round(ce_low, 2)},
        "pe": {"high": round(pe_high, 2), "close": round(pe_close, 2), "low": round(pe_low, 2)},
        "bannerTotal": round(min_diff, 2),
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "sniper1": {
            "strike": sniper_atm_strike, 
            "ce": round(s1_ce_close, 2), 
            "pe": round(s1_pe_close, 2),
            "otmCeStrike": target_s1_ce_strike, 
            "otmPeStrike": target_s1_pe_strike,
            "otmCe": round(s1_ce_close, 2), 
            "otmPe": round(s1_pe_close, 2),
            "sniperValue": sniper1_avg
        },
        "sniper2": {
            "strike": sniper_atm_strike, 
            "ce": round(s2_ce_close, 2), 
            "pe": round(s2_pe_close, 2),
            "otmCeStrike": target_s2_ce_strike, 
            "otmPeStrike": target_s2_pe_strike,
            "otmCe": round(s2_ce_close, 2), 
            "otmPe": round(s2_pe_close, 2),
            "sniperValue": sniper2_avg
        }
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=4)
    print("Dashboard data updated successfully.")

if __name__ == "__main__":
    update_dashboard()
