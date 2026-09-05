def parse_bhavcopy_for_strike(target_strike, option_type, target_expiry_str):
    if not os.path.exists("bhavcopy.csv"):
        return 0.0, 0.0, 0.0

    try:
        dt_obj = datetime.datetime.strptime(target_expiry_str, "%Y-%m-%d")
        fmt1 = dt_obj.strftime("%Y-%m-%d")
        fmt2 = dt_obj.strftime("%d-%b-%Y").upper()
    except Exception:
        fmt1 = target_expiry_str
        fmt2 = target_expiry_str

    try:
        with open("bhavcopy.csv", mode="r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean headers
                row = {k.strip().upper(): (v.strip() if v else "") for k, v in row.items() if k}
                
                symbol = row.get("TCKRSYMB", "") or row.get("SYMBOL", "")
                if "NIFTY" not in symbol.upper():
                    continue

                strike_val = row.get("STRIKEPRIC") or row.get("STRIKE_PR") or row.get("STRIKE")
                opt_typ = row.get("OPTNTP") or row.get("OPTION_TYP") or row.get("OPTIONTYPE")
                expiry_val = row.get("XPRYDT") or row.get("EXPIRY_DT") or row.get("EXPIRY")
                
                if strike_val and opt_typ:
                    try:
                        matches_strike = float(strike_val) == float(target_strike)
                        matches_opt = option_type.upper() in opt_typ.upper()
                        matches_expiry = (not expiry_val) or (fmt1 in expiry_val or fmt2 in expiry_val)
                        
                        if matches_strike and matches_opt and matches_expiry:
                            high = float(row.get("HGHPRC") or row.get("HIGH") or row.get("HIGH_PRICE") or 0.0)
                            low = float(row.get("LWPRC") or row.get("LOW") or row.get("LOW_PRICE") or 0.0)
                            close = float(row.get("CLSPRC") or row.get("CLOSE") or row.get("CLOSE_PRICE") or row.get("SETTLE_PR") or 0.0)
                            
                            # Validate High >= Close >= Low
                            if high > 0 or low > 0 or close > 0:
                                return max(high, close), min(low, close) if low > 0 else low, close
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error reading bhavcopy.csv: {e}")
        
    return 0.0, 0.0, 0.0


def process_and_save_data(res_json, spot, expiry_date_str):
    data = res_json.get("data", [])
    if not data or spot <= 0:
        print("Invalid data or spot price received.")
        return

    download_nse_bhavcopy()

    min_diff = float('inf')
    hlc_atm_strike = int(round(spot / 50.0) * 50)

    for item in data:
        item_strike = item.get("strike_price")
        if item_strike is None:
            continue
        
        s_val = float(item_strike)
        if abs(s_val - spot) > 500:
            continue
            
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

    sniper1_atm_strike = int(round(spot / 100.0) * 100)
    sniper2_atm_strike = hlc_atm_strike

    target_s1_ce_strike = sniper1_atm_strike + 100
    target_s1_pe_strike = sniper1_atm_strike - 100
    target_s2_ce_strike = sniper2_atm_strike + 100
    target_s2_pe_strike = sniper2_atm_strike - 100

    # Parse Bhavcopy for High/Low/Close
    ce_high, ce_low, ce_close = parse_bhavcopy_for_strike(hlc_atm_strike, "CE", expiry_date_str)
    pe_high, pe_low, pe_close = parse_bhavcopy_for_strike(hlc_atm_strike, "PE", expiry_date_str)

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

        if s_val == hlc_atm_strike:
            ce_h = float(m_call.get("high_price") or call_opts.get("high_price") or 0.0)
            ce_l = float(m_call.get("low_price") or call_opts.get("low_price") or 0.0)
            ce_c = float(m_call.get("close_price") or call_opts.get("close_price") or ce_ltp)

            pe_h = float(m_put.get("high_price") or put_opts.get("high_price") or 0.0)
            pe_l = float(m_put.get("low_price") or put_opts.get("low_price") or 0.0)
            pe_c = float(m_put.get("close_price") or put_opts.get("close_price") or pe_ltp)

            # Fallback if Bhavcopy did not populate values
            if ce_close == 0.0:
                ce_close = ce_c
            if ce_high == 0.0:
                ce_high = max(ce_h, ce_close)
            if ce_low == 0.0:
                ce_low = ce_l if ce_l > 0 else ce_close

            if pe_close == 0.0:
                pe_close = pe_c
            if pe_high == 0.0:
                pe_high = max(pe_h, pe_close)
            if pe_low == 0.0:
                pe_low = pe_l if pe_l > 0 else pe_close

        if s_val == sniper1_atm_strike:
            s1_atm_ce_val, s1_atm_pe_val = ce_ltp, pe_ltp
        elif s_val == target_s1_ce_strike:
            s1_ce_val = ce_ltp
        elif s_val == target_s1_pe_strike:
            s1_pe_val = pe_ltp

        if s_val == sniper2_atm_strike:
            s2_atm_ce_val, s2_atm_pe_val = ce_ltp, pe_ltp
        elif s_val == target_s2_ce_strike:
            s2_ce_val = ce_ltp
        elif s_val == target_s2_pe_strike:
            s2_pe_val = pe_ltp

    now_ist = datetime.datetime.now(IST)

    payload = {
        "dataStatus": "SUCCESS",
        "currentDate": now_ist.strftime("%d %b %Y").upper(),
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
        
    print("Dashboard data updated successfully.")
    
    if os.path.exists("bhavcopy.csv"):
        os.remove("bhavcopy.csv")

    push_to_github()
