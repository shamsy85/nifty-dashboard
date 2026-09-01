import os
import json
from datetime import datetime
from fyers_apiv3 import fyersModel

def fetch_market_data():
    client_id = os.environ.get("SKZODRJWMB-200")
    access_token = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCcWxsM2Z1Smt1WnRuUEF6QXU0NWhNSU1PRVJRYTNNVU9ZME5YZlJyVGtRd3hRZjVWb19iUE5BNnBBdXM5aElveElHWHRGV2s5THRtUVBuRlFITk9mY2FJMWZFbWF1blpiRjMtYVJzSDZwaFVMTTk3bz0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiIwY2RjMzgzMGYyZmZiYmRkZjM2NTk4N2M3YjI1ZTFjMzM4ZWRiODEwZWI3MTU1NjYyNjAyM2JiNCIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiWE0yNTMwMCIsImFwcFR5cGUiOjIwMCwiZXhwIjoxNzg4MzA5MDAwLCJpYXQiOjE3ODgyMzkzMjcsImlzcyI6ImFwaS5meWVycy5pbiIsIm5iZiI6MTc4ODIzOTMyNywic3ViIjoiYWNjZXNzX3Rva2VuIn0.nUUSH07RLHNVKiN9XljVwhuyBbq6DT2-MArav4NJu80")

    if not client_id or not access_token:
        raise ValueError("Missing FYERS credentials or access token in environment variables.")

    fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")

    # 1. Fetch Nifty Spot Price
    spot_data = {"symbol": "NSE:NIFTY50-INDEX", "resolution": "D", "date_format": "1", "range_from": datetime.now().strftime("%Y-%m-%d"), "range_to": datetime.now().strftime("%Y-%m-%d"), "cont_flag": "1"}
    spot_response = fyers.history(data=spot_data)
    
    # Fallback or extract spot close/ltp
    spot_price = 24800.00 # Replace or extract dynamically from spot_response if available
    
    # 2. Determine Expiry Date format required by your broker/symbols (e.g., '2690324800CE')
    # Assuming you have your active expiry string, e.g., "26SEP"
    current_expiry = "26SEP" 
    base_atm = round(spot_price / 50) * 50
    strike_range = [base_atm + (i * 50) for i in range(-3, 4)]
    
    best_strike = base_atm
    min_diff = float('inf')
    best_ce_data = {}
    best_pe_data = {}

    # Find ATM strike based on smallest CE and PE close difference
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
                    best_pe_data = {"high": pe_q.get('high', 0), "close": pe_close, "low": pe_q.get('low', 0)}

    # 3. Compile Dashboard Payload
    dashboard_payload = {
        "spotPrice": spot_price,
        "expiryDate": current_expiry,
        "currentDate": datetime.now().strftime("%d %b %Y"),
        "atmStrike": best_strike,
        "bannerTotal": best_ce_data.get("close", 0) + best_pe_data.get("close", 0),
        "ce": best_ce_data,
        "pe": best_pe_data,
        "sniper1": {"strike": best_strike, "ce": best_ce_data.get("close", 0), "pe": best_pe_data.get("close", 0), "otmCeStrike": best_strike+100, "otmCe": 0, "otmPeStrike": best_strike-100, "otmPe": 0},
        "sniper2": {"strike": best_strike, "ce": best_ce_data.get("close", 0), "pe": best_pe_data.get("close", 0), "otmCeStrike": best_strike+200, "otmCe": 0, "otmPeStrike": best_strike-200, "otmPe": 0}
    }

    with open("data.json", "w") as f:
        json.dump(dashboard_payload, f, indent=4)
    print("Successfully calculated optimal ATM and saved data.json")

if __name__ == "__main__":
    fetch_market_data()
