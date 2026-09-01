import os
import json
import base64
from datetime import datetime
import pyotp
import requests
from urllib.parse import urlparse, parse_qsl
from fyers_apiv3 import fyersModel

def generate_automated_token():
    client_id = "SKZODRJWMB-200"
    secret_key = "Qu61IAGCiTVURBjz"
    pin = "1997"
    totp_key = "WRUOITZF6ROJOTIQVDQCE3ZLLGIMIRMH"
    fy_id = "XM25300"

    redirect_uri = "https://trade.fyers.in/api-login/redirect-uri/index.html"
    
    # 1. Initialize Session Model for auth code
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )
    login_url = session.generate_authcode()

    parsed_url = urlparse(login_url)
    app_id_hash = dict(parse_qsl(parsed_url.query)).get("app_id_hash")

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://trade.fyers.in",
        "Referer": "https://trade.fyers.in/"
    })

    # 2. Send Login OTP
    encoded_fy_id = base64.b64encode(fy_id.encode()).decode()
    r1 = s.post("https://api-t2.fyers.in/vagator/v2/send_login_otp_v2", json={"fy_id": encoded_fy_id, "app_id": "2"})
    if r1.status_code != 200:
        raise Exception(f"Failed to send OTP (Status {r1.status_code}): {r1.text}")
    request_key = r1.json().get("request_key")

    # 3. Verify TOTP
    totp_code = pyotp.TOTP(totp_key).now()
    r2 = s.post("https://api-t2.fyers.in/vagator/v2/verify_otp", json={"request_key": request_key, "otp": totp_code})
    if r2.status_code != 200:
        raise Exception(f"Failed to verify TOTP: {r2.text}")
    request_key_2 = r2.json().get("request_key")

    # 4. Verify PIN
    encoded_pin = base64.b64encode(pin.encode()).decode()
    r3 = s.post("https://api-t2.fyers.in/vagator/v2/verify_pin_v2", json={"request_key": request_key_2, "identity_type": "pin", "identifier": encoded_pin})
    if r3.status_code != 200:
        raise Exception(f"Failed to verify PIN: {r3.text}")
    access_token_base = r3.json().get("data", {}).get("access_token")

    # 5. Get Auth Code via API token exchange
    headers = {
        "authorization": f"Bearer {access_token_base}", 
        "content-type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://trade.fyers.in",
        "Referer": "https://trade.fyers.in/"
    }
    payload = {
        "fyers_id": fy_id,
        "app_id": app_id_hash,
        "redirect_uri": redirect_uri,
        "appType": "100",
        "code_challenge": "",
        "state": "None",
        "scope": "",
        "nonce": "",
        "response_type": "code",
        "create_cookie": True
    }
    r4 = s.post("https://api.fyers.in/api/v2/token", json=payload, headers=headers)
    if r4.status_code != 200:
        raise Exception(f"Failed to fetch authorization code: {r4.text}")
    
    response_data = r4.json()
    if "Url" not in response_data:
        raise Exception(f"Token exchange response missing Url: {response_data}")
        
    auth_code = response_data.get("Url").split("auth_code=")[1].split("&")[0]

    # 6. Generate Final Access Token
    session.set_token(auth_code)
    response = session.generate_token()
    access_token = response.get("access_token")
    
    return client_id, access_token

def fetch_market_data():
    client_id, access_token = generate_automated_token()
    fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")

    # 1. Fetch Nifty Spot Price
    spot_data = {
        "symbol": "NSE:NIFTY50-INDEX", 
        "resolution": "D", 
        "date_format": "1", 
        "range_from": datetime.now().strftime("%Y-%m-%d"), 
        "range_to": datetime.now().strftime("%Y-%m-%d"), 
        "cont_flag": "1"
    }
    spot_response = fyers.history(data=spot_data)
    
    spot_price = 24800.00
    if spot_response.get("s") == "ok" and spot_response.get("candles"):
        spot_price = spot_response["candles"][-1][4]

    # 2. Determine Optimal ATM based on smallest CE and PE close difference
    current_expiry = "26SEP"
    base_atm = round(spot_price / 50) * 50
    strike_range = [base_atm + (i * 50) for i in range(-3, 4)]
    
    best_strike = base_atm
    min_diff = float('inf')
    best_ce_data = {"high": 0, "close": 0, "low": 0}
    best_pe_data = {"high": 0, "close": 0, "low": 0}

    for strike in strike_range:
        ce_symbol = f"NSE:NIFTY{current_expiry}{strike}CE"
        pe_symbol = f"NSE:NIFTY{current_expiry}{strike}PE"
        
        quotes_response = fyers.quotes(data={"symbols": f"{ce_symbol},{pe_symbol}"})
        if quotes_response.get("s") == "ok":
            q_list = quotes_response.get("d", [])
            ce_q = next((item['v'] for item in q_list if item['name'] == ce_symbol), None)
            pe_q = next((item['v'] for item in q_list if item['name'] == pe_symbol), None)
            
            if ce_q and pe_q:
                ce_close = ce_q.get('lp', 0)
                pe_close = pe_q.get('lp', 0)
                diff = abs(ce_close - pe_close)
                
                if diff < min_diff:
                    min_diff = diff
                    best_strike = strike
                    best_ce_data = {"high": ce_q.get('high', 0), "close": ce_close, "low": ce_q.get('low', 0)}
                    best_pe_data = {"high": pe_q.get('high', 0), "close": pe_close, "low": pe_close}

    # 3. Calculate and verify final day close prices for the optimal ATM strike
    opt_ce_symbol = f"NSE:NIFTY{current_expiry}{best_strike}CE"
    opt_pe_symbol = f"NSE:NIFTY{current_expiry}{best_strike}PE"
    
    close_quotes_response = fyers.quotes(data={"symbols": f"{opt_ce_symbol},{opt_pe_symbol}"})
    if close_quotes_response.get("s") == "ok":
        q_list = close_quotes_response.get("d", [])
        ce_q = next((item['v'] for item in q_list if item['name'] == opt_ce_symbol), None)
        pe_q = next((item['v'] for item in q_list if item['name'] == opt_pe_symbol), None)
        
        if ce_q and pe_q:
            best_ce_data["close"] = ce_q.get('lp', best_ce_data["close"])
            best_pe_data["close"] = pe_q.get('lp', best_pe_data["close"])
            print(f"Optimal Strike {best_strike} Day Close Verified -> CE: {best_ce_data['close']}, PE: {best_pe_data['close']}")

    # 4. Compile Dashboard Payload
    dashboard_payload = {
        "spotPrice": spot_price,
        "expiryDate": current_expiry,
        "currentDate": datetime.now().strftime("%d %b %Y"),
        "atmStrike": best_strike,
        "bannerTotal": best_ce_data.get("close", 0) + best_pe_data.get("close", 0),
        "ce": best_ce_data,
        "pe": best_pe_data,
        "sniper1": {
            "strike": best_strike, 
            "ce": best_ce_data.get("close", 0), 
            "pe": best_pe_data.get("close", 0), 
            "otmCeStrike": best_strike + 100, 
            "otmCe": 0, 
            "otmPeStrike": best_strike - 100, 
            "otmPe": 0
        },
        "sniper2": {
            "strike": best_strike, 
            "ce": best_ce_data.get("close", 0), 
            "pe": best_pe_data.get("close", 0), 
            "otmCeStrike": best_strike + 200, 
            "otmCe": 0, 
            "otmPeStrike": best_strike - 200, 
            "otmPe": 0
        }
    }

    with open("data.json", "w") as f:
        json.dump(dashboard_payload, f, indent=4)
    print("Successfully generated token, calculated ATM day close prices, and saved data.json")

if __name__ == "__main__":
    fetch_market_data()
