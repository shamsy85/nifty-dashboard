import datetime
import json
import os
import requests
import subprocess
import csv
import io
import zipfile

def push_to_github():
    subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"])
    subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"])
    subprocess.run(["git", "add", "data.json", "bhavcopy.csv"])
    subprocess.run(["git", "commit", "-m", "Auto-update dashboard and bhavcopy [skip ci]"])
    subprocess.run(["git", "push", "origin", "main"])

def load_access_token():
    if os.path.exists("token.txt"):
        with open("token.txt", "r") as f:
            return f.read().strip()
    return os.getenv("UPSTOX_ACCESS_TOKEN", "")

def fetch_live_spot_price(access_token):
    url = "https://api.upstox.com/v2/market-quote/ltp?instrument_key=NSE_INDEX%7CNifty%2050"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            spot = data.get("data", {}).get("NSE_INDEX:Nifty 50", {}).get("last_price", 0.0)
            return float(spot)
    except Exception as e:
        print(f"Failed to fetch live spot price: {e}")
    return 0.0

def get_current_expiry(access_token):
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
        raw_list = res_json.get("data", [])
        if raw_list:
            expiry_list = []
            for item in raw_list:
                if isinstance(item, dict):
                    exp = item.get("expiry") or item.get("expiry_date") or item.get("date")
                    if exp:
                        expiry_list.append(str(exp))
                elif isinstance(item, str):
                    expiry_list.append(item)
            
            expiry_list = sorted(list(set(expiry_list)))
            if expiry_list:
                if today_str in expiry_list and not market_closed:
                    return today_str
                for exp in expiry_list:
                    if exp > today_str:
                        return exp
                    elif exp == today_str and not market_closed:
                        return exp
                return expiry_list[-1]
    return today_str

def download_nse_bhavcopy():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/"
    }
    for i in range(5):
        target_date = datetime.datetime.now() - datetime.timedelta(days=i)
        if target_date.weekday() >= 5:
            continue
        yyyy = target_date.strftime("%Y")
        mm = target_date.strftime("%m")
        dd = target_date.strftime("%d")
        url = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{yyyy}{mm}{dd}_F_0000.csv.zip"
        try:
            session = requests.Session()
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            response = session.get(url, headers=headers, timeout=30)
            if response.status_code == 200 and len(response.content) > 1000:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    csv_filename = z.namelist()[0]
                    with z.open(csv_filename) as csv_file, open("bhavcopy.csv", "wb") as f:
                        f.write(csv_file.read())
                print(f"Successfully downloaded and extracted UDiFF F&O Bhavcopy for {target_date.strftime('%Y-%m-%d')}")
                return True
        except Exception as e:
            print(f"Attempt for UDiFF F&O Bhavcopy on {target_date.strftime('%Y-%m-%d')} failed: {e}")
    return False

def fetch_option_chain_data(access_token, expiry_date):
    instrument_key = "NSE_INDEX|Nifty 50"
    url = f"https://api.upstox.com/v2/option/chain?instrument_key={instrument_key}&expiry_date={expiry_date}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

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
                row = {k.strip().upper(): v.strip() for k, v in row.items() if k}
                
                symbol = row.get("TCKRSYMB", "")
                if "NIFTY" not in symbol.upper():
                    continue

                strike_val = row.get("STRIKEPRIC") or row.get("STRIKE_PR") or row.get("STRIKE")
                opt_typ = row.get("OPTNTP") or row.get("OPTION_TYP")
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
                            if high > 0 or low > 0 or close > 0:
                                return high, low, close
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
        
        ce_h = float(call_opts.get("high_price") or m_call.get("high_price") or ce_ltp)
        ce_l = float(call_opts.get("low_price") or m_call.get("low_price") or ce_ltp)
        pe_h = float(put_opts.get("high_price") or m_put.get("high_price") or pe_ltp)
        pe_l = float(put_opts.get("low_price") or m_put.get("low_price") or pe_ltp)

        # Fallback using API high/low when Bhavcopy data is missing intraday
        if s_val == hlc_atm_strike:
            if ce_close == 0.0:
                ce_close = ce_ltp
                ce_high = ce_h
                ce_low = ce_l
            if pe_close == 0.0:
                pe_close = pe_ltp
                pe_high = pe_h
                pe_low = pe_l

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
        
    print("Dashboard data updated successfully.")
    push_to_github()

if __name__ == "__main__":
    access_token = load_access_token()
    if access_token:
        expiry = get_current_expiry(access_token)
        spot = fetch_live_spot_price(access_token)
        res = fetch_option_chain_data(access_token, expiry)
        if res and spot > 0:
            process_and_save_data(res, spot, expiry)
