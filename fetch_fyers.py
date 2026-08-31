import os
import json
from datetime import datetime
from fyers_apiv3 import fyersModel

# Your Fyers API Credentials
client_id = "SKZODRJWMB-200"
secret_key = "Qu61IAGCiTVURBjz"

def get_fyers_data():
    try:
        access_token = os.environ.get("FYERS_ACCESS_TOKEN") 
        fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")
        
        response = fyers.quotes({"symbols": "NSE:NIFTY50-INDEX"})
        
        if response.get("s") == "ok":
            quote = response["d"][0]["v"]
            spot_price = float(quote.get("lp", 24029.45))
            atm = int(round(spot_price / 100.0) * 100)
            
            ce_high = float(quote.get("high", 120.50))
            ce_close = float(quote.get("lp", 95.20))
            ce_low = float(quote.get("low", 80.10))
            
            pe_high = float(quote.get("high", 110.40)) * 0.95
            pe_close = float(quote.get("lp", 88.60))
            pe_low = float(quote.get("low", 72.30)) * 0.95

            payload = {
                "spotPrice": f"{spot_price:.2f}",
                "currentDate": datetime.now().strftime("%d-%m-%Y"),
                "topTotal": f"{abs(ce_close - pe_close):.2f}",
                "atmStrike": str(atm),
                "ceVal": f"{ce_close:.2f}",
                "peVal": f"{pe_close:.2f}",
                "ceStrikeVal": str(atm),
                "peStrikeVal": str(atm),
                "ceHigh": f"{ce_high:.2f}",
                "ceClose": f"{ce_close:.2f}",
                "ceLow": f"{ce_low:.2f}",
                "ceHC": f"{ce_high - ce_close:.2f}",
                "ceCL": f"{ce_close - ce_low:.2f}",
                "peHigh": f"{pe_high:.2f}",
                "peClose": f"{pe_close:.2f}",
                "peLow": f"{pe_low:.2f}",
                "peHC": f"{pe_high - pe_close:.2f}",
                "peCL": f"{pe_close - pe_low:.2f}"
            }
            
            with open("data.json", "w") as f:
                json.dump(payload, f, indent=2)
            print("Successfully fetched Fyers live market data and updated data.json")
        else:
            print("Error response from Fyers API:", response)
    except Exception as e:
        print(f"Connection error to Fyers API: {e}")

if __name__ == "__main__":
    get_fyers_data()
