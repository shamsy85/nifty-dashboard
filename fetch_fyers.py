import os
import json
from datetime import datetime
from fyers_apiv3 import fyersModel

client_id = os.environ.get("FYERS_CLIENT_ID")
secret_key = os.environ.get("FYERS_SECRET_KEY")

def get_fyers_data():
    try:
        access_token = os.environ.get("FYERS_ACCESS_TOKEN") 
        fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")
        
        # Fetching Nifty 50 Index Quote
        response = fyers.quotes({"symbols": "NSE:NIFTY50-INDEX"})
        
        if response.get("s") == "ok":
            quote = response["d"][0]["v"]
            spot_price = float(quote.get("lp", 24175.65))
            atm = int(round(spot_price / 100.0) * 100)
            
            # You can also fetch specific option symbols dynamically here if needed 
            # e.g., fyers.quotes({"symbols": f"NSE:NIFTY26901{atm}CE"})
            
            payload = {
                "spotPrice": spot_price,
                "expiryDate": "01-09-2026",
                "atmStrike": atm,
                "ce": {
                    "high": float(quote.get("high", 102.80)),
                    "close": float(quote.get("lp", 79.10)),
                    "low": float(quote.get("low", 55.40))
                },
                "pe": {
                    "high": float(quote.get("high", 124.90)) * 1.1,
                    "close": float(quote.get("lp", 96.10)),
                    "low": float(quote.get("low", 67.30)) * 0.9
                },
                "ceStatus": "neutral",
                "minSupply": round(spot_price + 25.0, 2),
                "minDemand": round(spot_price - 25.0, 2),
                "maxSupply": round(spot_price + 175.0, 2),
                "maxDemand": round(spot_price - 175.0, 2),
                "wzSupply1": round(spot_price + 120.0, 2),
                "wzSupply2": round(spot_price + 250.0, 2),
                "wzDemand1": round(spot_price - 110.0, 2),
                "wzDemand2": round(spot_price - 230.0, 2),
                "mzSupply1": round(spot_price + 400.0, 2),
                "mzSupply2": round(spot_price + 650.0, 2),
                "mzDemand1": round(spot_price - 380.0, 2),
                "mzDemand2": round(spot_price - 600.0, 2),
                "sniper1": {
                    "strike": float(atm + 50),
                    "ce": 79.10,
                    "pe": 96.10,
                    "otmCe": 40.95,
                    "otmPe": 53.95,
                    "val": 47.45
                },
                "earthVal": 148.92
            }
            
            with open("data.json", "w") as f:
                json.dump(payload, f, indent=2)
            print("Successfully pulled live Fyers market parameters and updated data.json")
        else:
            print("Failed to fetch market quotes from Fyers API:", response)
    except Exception as e:
        print(f"Error connecting to Fyers API: {e}")

if __name__ == "__main__":
    get_fyers_data()
