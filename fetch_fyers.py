import os
import json
from fyers_apiv3 import fyersModel

client_id = os.environ.get("FYERS_CLIENT_ID")
secret_key = os.environ.get("FYERS_SECRET_KEY")

def get_fyers_data():
    try:
        access_token = os.environ.get("FYERS_ACCESS_TOKEN") 
        fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")
        response = fyers.quotes({"symbols": "NSE:NIFTY50-INDEX"})

        if response.get("s") == "ok":
            quote = response["d"][0]["v"]
            spot_price = quote.get("lp", 24080.40)

            payload = {
                "spotPrice": float(spot_price),
                "currentDate": "31-08-2026",
                "atmStrike": int(round(spot_price / 100.0) * 100),
                "earthVal": 35.27
            }

            with open("data.json", "w") as f:
                json.dump(payload, f, indent=2)
            print("Successfully updated data from FYERS API.")
    except Exception as e:
        print(f"Error connecting to FYERS: {e}")

if __name__ == "__main__":
    get_fyers_data()
