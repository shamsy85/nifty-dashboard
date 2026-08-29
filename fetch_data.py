import json
from datetime import datetime
import yfinance as yf

def fetch_and_update():
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    # 1. Fetch live NIFTY 50 spot data
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period="1d")

    if not hist.empty:
        spot_close = round(float(hist['Close'].iloc[-1]), 2)
        spot_high = round(float(hist['High'].iloc[-1]), 2)
        spot_low = round(float(hist['Low'].iloc[-1]), 2)
    else:
        spot_close, spot_high, spot_low = 24175.65, 24188.30, 24076.85

    base_strike = round(spot_close / 50) * 50
    expiries = nifty.options
    
    ce_close, ce_high, ce_low = 79.10, 108.50, 52.30
    pe_close, pe_high, pe_low = 96.10, 131.20, 61.40
    atm_strike = base_strike if base_strike else 24200

    if expiries:
        try:
            nearest_expiry = expiries[0]
            opt_chain = nifty.option_chain(nearest_expiry)
            calls = opt_chain.calls.set_index('strike')
            puts = opt_chain.puts.set_index('strike')

            if atm_strike in calls.index and atm_strike in puts.index:
                ce_data = calls.loc[atm_strike]
                pe_data = puts.loc[atm_strike]

                ce_close = round(float(ce_data['lastPrice']), 2)
                ce_high = round(float(ce_data.get('highPrice', ce_close * 1.35)), 2)
                ce_low = round(float(ce_data.get('lowPrice', ce_close * 0.65)), 2)

                pe_close = round(float(pe_data['lastPrice']), 2)
                pe_high = round(float(pe_data.get('highPrice', pe_close * 1.30)), 2)
                pe_low = round(float(pe_data.get('lowPrice', pe_close * 0.70)), 2)
        except Exception as e:
            print(f"Option chain extraction error: {e}")

    # Derived Calculations
    straddle_val = round(ce_close + pe_close, 2)
    diff_val = round(abs(pe_close - ce_close), 2)
    
    min_supply = round(spot_close + (ce_close * 0.5), 2)
    min_demand = round(spot_close - (pe_close * 0.5), 2)
    max_supply = round(spot_close + straddle_val, 2)
    max_demand = round(spot_close - straddle_val, 2)

    # 2. Construct Payload
    payload = {
        "spotPrice": spot_close,
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "expiryDate": expiries[0] if expiries else "01-09-2026",
        "currentDate": today_str,
        "atmStrike": atm_strike,
        "bannerTotal": diff_val,
        "ce": {
            "high": ce_high,
            "close": ce_close,
            "low": ce_low
        },
        "pe": {
            "high": pe_high,
            "close": pe_close,
            "low": pe_low
        },
        "minSupply": min_supply,
        "minDemand": min_demand,
        "maxSupply": max_supply,
        "maxDemand": max_demand,
        "wzSupply1": round(spot_close + 120.50, 2),
        "wzSupply2": round(spot_close + 250.00, 2),
        "wzDemand1": round(spot_close - 110.20, 2),
        "wzDemand2": round(spot_close - 230.00, 2),
        "mzSupply1": round(spot_close + 400.00, 2),
        "mzSupply2": round(spot_close + 650.00, 2),
        "mzDemand1": round(spot_close - 380.00, 2),
        "mzDemand2": round(spot_close - 600.00, 2),
        "sniper1": {
            "strike": atm_strike,
            "ce": ce_close,
            "pe": pe_close,
            "otmCeStrike": atm_strike + 100,
            "otmCe": round(ce_close * 0.5, 2),
            "otmPeStrike": atm_strike - 100,
            "otmPe": round(pe_close * 0.5, 2),
            "val": round(diff_val * 1.5, 2)
        },
        "sniper2": {
            "strike": atm_strike - 50,
            "ce": round(ce_close * 1.2, 2),
            "pe": round(pe_close * 0.8, 2),
            "otmCeStrike": atm_strike + 50,
            "otmCe": round(ce_close * 0.7, 2),
            "otmPeStrike": atm_strike - 150,
            "otmPe": round(pe_close * 0.4, 2),
            "val": round(diff_val * 1.2, 2)
        },
        "earthVal": round(straddle_val * 0.85, 2)
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print("Data updated with asymmetrical High and Low values.")

if __name__ == "__main__":
    fetch_and_update()
