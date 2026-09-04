import csv
import os

def parse_bhavcopy_for_option(symbol_prefix, expiry_date_str, strike, option_type):
    """
    Parses bhavcopy.csv to find High, Low, Close for a specific option contract.
    NSE Bhavcopy usually formats dates as DD-MMM-YYYY or similar in the filename or contents,
    or we match the trading symbol directly (e.g., NIFTY08SEP2026C23900).
    """
    if not os.path.exists("bhavcopy.csv"):
        return None, None, None

    # Format expiry for symbol matching (e.g., 08-SEP-2026 -> 08SEP26)
    try:
        exp_dt = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d")
        day_str = exp_dt.strftime("%d").upper()
        mon_str = exp_dt.strftime("%b").upper()
        yr_str = exp_dt.strftime("%y")
        target_symbol_part = f"{day_str}{mon_str}{yr_str}{option_type[0]}{int(strike)}"
    except Exception:
        target_symbol_part = f"{int(strike)}{option_type}"

    try:
        with open("bhavcopy.csv", mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean keys (strip whitespace)
                row = {k.strip(): v.strip() for k, v in row.items() if k}
                
                # Check different possible column names for symbol and instrument type
                symbol = row.get("SYMBOL") or row.get("TKR") or row.get("INSTRUMENT", "")
                
                if symbol_prefix.upper() in symbol.upper() and target_symbol_part.upper() in symbol.upper():
                    high = float(row.get("HIGH_PRICE") or row.get("HIGH") or 0.0)
                    low = float(row.get("LOW_PRICE") or row.get("LOW") or 0.0)
                    close = float(row.get("CLOSE_PRICE") or row.get("CLOSE") or row.get("LTP") or 0.0)
                    return high, low, close
    except Exception as e:
        print(f"Error parsing bhavcopy.csv: {e}")
        
    return None, None, None

def process_and_save_data(res_json, spot, expiry_date_str):
    data = res_json.get("data", [])
    target_atm = int(round(spot / 50.0) * 50)

    min_diff = float('inf')
    hlc_atm_strike = target_atm
    ce_close, ce_high, ce_low = 0.0, 0.0, 0.0
    pe_close, pe_high, pe_low = 0.0, 0.0, 0.0

    # First download the latest available bhavcopy
    download_nse_bhavcopy()

    for item in data:
        item_strike = item.get("strike_price")
        if item_strike is None:
            continue
        
        s_val = float(item_strike)
        if abs(s_val - spot) > 500:
            continue
            
        call_opts = item.get("call_options", {})
        put_opts = item.get("put_options", {})
        
        ce_ltp = float(call_opts.get("last_price") or call_opts.get("market_data", {}).get("ltp") or 0.0)
        pe_ltp = float(put_opts.get("last_price") or put_opts.get("market_data", {}).get("ltp") or 0.0)
        
        diff = abs(ce_ltp - pe_ltp)
        if diff < min_diff:
            min_diff = diff
            hlc_atm_strike = int(s_val)
            ce_close = ce_ltp
            pe_close = pe_ltp

    # Fetch HLC from Bhavcopy for the determined ATM strike
    b_high, b_low, b_close = parse_bhavcopy_for_option("NIFTY", expiry_date_str, hlc_atm_strike, "CE")
    if b_close is not None:
        ce_high, ce_low, ce_close = b_high, b_low, b_close
    else:
        # Fallback to API values if Bhavcopy match isn't found
        for item in data:
            if float(item.get("strike_price", 0)) == hlc_atm_strike:
                c_opt = item.get("call_options", {})
                ce_high = float(c_opt.get("high_price") or c_opt.get("market_data", {}).get("high_price") or ce_close)
                ce_low = float(c_opt.get("low_price") or c_opt.get("market_data", {}).get("low_price") or ce_close)

    b_high, b_low, b_close = parse_bhavcopy_for_option("NIFTY", expiry_date_str, hlc_atm_strike, "PE")
    if b_close is not None:
        pe_high, pe_low, pe_close = b_high, b_low, b_close
    else:
        for item in data:
            if float(item.get("strike_price", 0)) == hlc_atm_strike:
                p_opt = item.get("put_options", {})
                pe_high = float(p_opt.get("high_price") or p_opt.get("market_data", {}).get("high_price") or pe_close)
                pe_low = float(p_opt.get("low_price") or p_opt.get("market_data", {}).get("low_price") or pe_close)

    sniper1_atm_strike = int(round(spot / 100.0) * 100)
    sniper2_atm_strike = target_atm

    target_s1_ce_strike = sniper1_atm_strike + 100
    target_s1_pe_strike = sniper1_atm_strike - 100
    target_s2_ce_strike = sniper2_atm_strike + 100
    target_s2_pe_strike = sniper2_atm_strike - 100

    s1_atm_ce_val, s1_atm_pe_val = 0.0, 0.0
    s2_atm_ce_val, s2_atm_pe_val = 0.0, 0.0
    s1_ce_val, s1_pe_val = 0.0, 0.0
    s2_ce_val, s2_pe_val = 0.0, 0.0

    for item in data:
        s_val = float(item.get("strike_price", 0))
        ce_ltp = float(item.get("call_options", {}).get("last_price") or 0.0)
        pe_ltp = float(item.get("put_options", {}).get("last_price") or 0.0)
        
        if s_val == sniper1_atm_strike:
            s1_atm_ce_val, s1_atm_pe_val = ce_ltp, pe_ltp
        if s_val == sniper2_atm_strike:
            s2_atm_ce_val, s2_atm_pe_val = ce_ltp, pe_ltp
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
        "expiryDate": datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d").strftime("%d-%b-%Y").upper(),
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
        "spotHigh": spot,
        "spotLow": spot,
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
        
    print("Dashboard data updated using Bhavcopy values.")
    push_to_github()
