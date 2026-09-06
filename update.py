import csv
import datetime
import io
import json
import os
import subprocess
import zipfile
import requests

# Define Indian Standard Time (IST) offset
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def push_to_github():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        
        # Force stage both data.json and bhavcopy.csv so it stays visible in GitHub
        subprocess.run(["git", "add", "-f", "data.json"], check=False)
        if os.path.exists("bhavcopy.csv"):
            subprocess.run(["git", "add", "-f", "bhavcopy.csv"], check=False)
        
        # Check if staged files have actual diffs against HEAD
        diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        
        if diff_check.returncode != 0:
            subprocess.run(["git", "commit", "-m", "Auto-update dashboard and bhavcopy [skip ci]"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("Changes pushed to GitHub successfully.")
        else:
            print("No changes detected in repository. Skipping commit.")
    except Exception as e:
        print(f"Git push failed: {e}")


def load_access_token():
    if os.path.exists("token.txt"):
        with open("token.txt", "r") as f:
            token = f.read().strip()
            if token:
                return token
    return os.getenv("UPSTOX_ACCESS_TOKEN", "")


def fetch_live_spot_price(access_token):
    url = "https://api.upstox.com/v2/market-quote/ltp?instrument_key=NSE_INDEX%7CNifty%2050"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
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
    now_ist = datetime.datetime.now(IST)
    today_str = now_ist.strftime("%Y-%m-%d")
    market_closed = now_ist.hour > 15 or (now_ist.hour == 15 and now_ist.minute >= 30)
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
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
    except Exception as e:
        print(f"Error fetching option contract expiry: {e}")
        
    return today_str


def download_nse_bhavcopy():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/"
    }
    now_ist = datetime.datetime.now(IST)
    
    for i in range(5):
        target_date = now_ist - datetime.timedelta(days=i)
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
                # Delete existing old bhavcopy file before saving the new one
                if os.path.exists("bhavcopy.csv"):
                    try:
                        os.remove("bhavcopy.csv")
                    except Exception as e:
                        print(f"Notice: Could not remove old bhavcopy: {e}")

                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    csv_filename = z.namelist()[0]
                    with z.open(csv_filename) as csv_file, open("bhavcopy.csv", "wb") as f:
                        f.write(csv_file.read())
                print(f"Successfully downloaded new UDiFF F&O Bhavcopy for {target_date.strftime('%Y-%m-%d')}")
                return True
        except Exception as e:
            print(f"Attempt for UDiFF F&O Bhavcopy on {target_date.strftime('%Y-%m-%d')} failed: {e}")
    return False


def load_bhavcopy_dict(target_expiry_str):
    """Loads Bhavcopy into a dictionary: { (int_strike, option_type): (high, low, close) }"""
    bhav_map = {}
    if not os.path.exists("bhavcopy.csv"):
        return bhav_map

    possible_expiries = set()
    possible_expiries.add(target_expiry_str.upper())
    
    try:
        dt_obj = datetime.datetime.strptime(target_expiry_str, "%Y-%m-%d")
        possible_expiries.add(dt_obj.strftime("%Y-%m-%d"))
        possible_expiries.add(dt_obj.strftime("%d-%b-%Y").upper())
        possible_expiries.add(dt_obj.strftime("%d-%B-%Y").upper())
        possible_expiries.add(dt_obj.strftime("%d%b%Y").upper())
        possible_expiries.add(dt_obj.strftime("%d%b%y").upper())
    except Exception:
        pass

    try:
        with open("bhavcopy.csv", mode="r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned_row = {k.strip().upper(): (v.strip() if v else "") for k, v in row.items() if k}
                
                symbol = cleaned_row.get("TCKRSYMB") or cleaned_row.get("SYMBOL") or cleaned_row.get("FININSTNM") or ""
                if "NIFTY" not in symbol.upper():
                    continue

                strike_raw = (cleaned_row.get("STRIKEPRIC") or cleaned_row.get("STRIKE_PR") or 
                              cleaned_row.get("STRIKE") or cleaned_row.get("STRK_PRC") or "0")
                try:
                    row_strike = int(round(float(strike_raw)))
                except ValueError:
                    continue

                opt_type_raw = (cleaned_row.get("OPTNTP") or cleaned_row.get("OPTION_TYP") or 
                                cleaned_row.get("OPTIONTYPE") or cleaned_row.get("OPT_TP") or "")
                opt_type = ""
                if "CE" in opt_type_raw.upper() or symbol.upper().endswith("CE"):
                    opt_type = "CE"
                elif "PE" in opt_type_raw.upper() or symbol.upper().endswith("PE"):
                    opt_type = "PE"

                if not opt_type:
                    continue

                expiry_raw = (cleaned_row.get("XPRYDT") or cleaned_row.get("EXPIRY_DT") or 
                              cleaned_row.get("EXPIRY") or cleaned_row.get("XPRY_DT") or "").upper()
                
                matches_expiry = True
                if expiry_raw:
                    matches_expiry = any(exp in expiry_raw for exp in possible_expiries)

                if matches_expiry:
                    high = float(cleaned_row.get("HGHPRC") or cleaned_row.get("HIGH") or cleaned_row.get("HIGH_PRICE") or cleaned_row.get("HGST_PRC") or 0.0)
                    low = float(cleaned_row.get("LWPRC") or cleaned_row.get("LOW") or cleaned_row.get("LOW_PRICE") or cleaned_row.get("LWST_PRC") or 0.0)
                    close = float(cleaned_row.get("CLSPRC") or cleaned_row.get("CLOSE") or cleaned_row.get("CLOSE_PRICE") or cleaned_row.get("SETTLE_PR") or cleaned_row.get("CLSG_PRC") or 0.0)

                    if high > 0 or low > 0 or close > 0:
                        val_high = max(high, close)
                        val_low = min(low, close) if low > 0 else close
                        bhav_map[(row_strike, opt_type)] = (val_high, val_low, close)
    except Exception as e:
        print(f"Error reading bhavcopy into dict: {e}")

    return bhav_map


def fetch_option_chain_data(access_token, expiry_date):
    instrument_key = "NSE_INDEX|Nifty 50"
    url = f"https://api.upstox.com/v2/option/chain?instrument_key={instrument_key}&expiry_date={expiry_date}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Failed to fetch option chain data: {e}")
    return None


def process_and_save_data(res_json, spot, expiry_date_str):
    data = res_json.get("data", [])
    if not data or spot <= 0:
        print("Invalid data or spot price received.")
        return

    # Download latest Bhavcopy (deletes old bhavcopy.csv automatically)
    download_nse_bhavcopy()
    bhav_map = load_bhavcopy_dict(expiry_date_str)

    min_diff = float('inf')
    hlc_atm_strike = int(round(spot / 50.0) * 50)

    # Compute minimum price difference using Bhavcopy Close (with live LTP fallback)
    for item in data:
        item_strike = item.get("strike_price")
        if item_strike is None:
            continue
        
        s_val = int(round(float(item_strike)))
        if abs(s_val - spot) > 500:
            continue

        call_opts = item.get("call_options", {})
        put_opts = item.get("put_options", {})
        
        ce_close = bhav_map.get((s_val, "CE"), (0.0, 0.0, 0.0))[2]
        pe_close = bhav_map.get((s_val, "PE"), (0.0, 0.0, 0.0))[2]

        if ce_close == 0.0:
            ce_close = float(call_opts.get("last_price") or call_opts.get("market_data", {}).get("ltp") or 0.0)
        if pe_close == 0.0:
            pe_close = float(put_opts.get("last_price") or put_opts.get("market_data", {}).get("ltp") or 0.0)

        if ce_close > 0 and pe_close > 0:
            diff = abs(ce_close - pe_close)
            if diff < min_diff:
                min_diff = diff
                hlc_atm_strike = s_val

    print(f"Calculated HLC ATM Strike: {hlc_atm_strike} (Min Diff: {round(min_diff, 2)})")

    sniper1_atm_strike = int(round(spot / 100.0) * 100)
    sniper2_atm_strike = hlc_atm_strike

    target_s1_ce_strike = sniper1_atm_strike + 100
    target_s1_pe_strike = sniper1_atm_strike - 100
    target_s2_ce_strike = sniper2_atm_strike + 100
    target_s2_pe_strike = sniper2_atm_strike - 100

    # Extract High, Low, Close directly from Bhavcopy
    ce_high, ce_low, ce_close = bhav_map.get((int(hlc_atm_strike), "CE"), (0.0, 0.0, 0.0))
    pe_high, pe_low, pe_close = bhav_map.get((int(hlc_atm_strike), "PE"), (0.0, 0.0, 0.0))

    s1_atm_ce_val, s1_atm_pe_val = 0.0, 0.0
    s2_atm_ce_val, s2_atm_pe_val = 0.0, 0.0
    s1_ce_val, s1_pe_val = 0.0, 0.0
    s2_ce_val, s2_pe_val = 0.0, 0.0

    for item in data:
        item_strike = item.get("strike_price")
        if item_strike is None:
            continue
        s_val = int(round(float(item_strike)))
        
        call_opts = item.get("call_options", {})
        put_opts = item.get("put_options", {})
        
        m_call = call_opts.get("market_data", {})
        m_put = put_opts.get("market_data", {})
        
        ce_ltp = float(call_opts.get("last_price") or m_call.get("ltp") or 0.0)
        pe_ltp = float(put_opts.get("last_price") or m_put.get("ltp") or 0.0)

        # STRICT FALLBACK ONLY: If Bhavcopy values were missing (0.0), fill from API
        if s_val == hlc_atm_strike:
            ce_h = float(m_call.get("high_price") or call_opts.get("high_price") or 0.0)
            ce_l = float(m_call.get("low_price") or call_opts.get("low_price") or 0.0)
            ce_c = float(m_call.get("close_price") or call_opts.get("close_price") or ce_ltp)

            pe_h = float(m_put.get("high_price") or put_opts.get("high_price") or 0.0)
            pe_l = float(m_put.get("low_price") or put_opts.get("low_price") or 0.0)
            pe_c = float(m_put.get("close_price") or put_opts.get("close_price") or pe_ltp)

            if ce_close == 0.0:
                ce_close = ce_c
            if ce_high == 0.0:
                ce_high = ce_h if ce_h > 0 else ce_close
            if ce_low == 0.0:
                ce_low = ce_l if ce_l > 0 else ce_close

            if pe_close == 0.0:
                pe_close = pe_c
            if pe_high == 0.0:
                pe_high = pe_h if pe_h > 0 else pe_close
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

    push_to_github()


if __name__ == "__main__":
    access_token = load_access_token()
    if access_token:
        expiry = get_current_expiry(access_token)
        spot = fetch_live_spot_price(access_token)
        res = fetch_option_chain_data(access_token, expiry)
        if res and spot > 0:
            process_and_save_data(res, spot, expiry)
    else:
        print("No valid Upstox access token found.")
