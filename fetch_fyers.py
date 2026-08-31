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
        response = fyers.quotes({"symbols": "NSE:NIFTY50-INDEX"})

        if response.get("s") == "ok":
            quote = response["d"][0]["v"]
            spot_price = quote.get("lp", 24080.40)
            atm = int(round(spot_price / 100.0) * 100)

            payload = {
                "spotPrice": float(spot_price),
                "currentDate": datetime.now().strftime("%d-%m-%Y"),
                "atmStrike": atm,
                "ceVal": 0.00,
                "peVal": 0.00,
                "ceHigh": 0.00,
                "ceClose": 0.00,
                "ceLow": 0.00,
                "peHigh": 0.00,
                "peClose": 0.00,
                "peLow": 0.00,
                "minSupply": 0.00,
                "minDemand": 0.00,
                "maxSupply": 0.00,
                "maxDemand": 0.00,
                "earthVal": 52.22,
                "sniperAtm1CE": 0.00,
                "sniperAtm1PE": 0.00,
                "sniperVal1": 0.00,
                "sniperAtm2CE": 0.00,
                "sniperAtm2PE": 0.00,
                "sniperVal2": 0.00
            }

            with open("data.json", "w") as f:
                json.dump(payload, f, indent=2)
            print("Successfully updated full dashboard data.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_fyers_data()
