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
    straddle_data = {}
    
    if expiries:
        try:
            nearest_expiry = expiries[0]
            opt_chain = nifty.option_chain(nearest_expiry)
            calls = opt_chain.calls.set_index('strike')
            puts = opt_chain.puts.set_index('strike')

            candidate_strikes = [base_strike + offset for offset in range(-250, 300, 50)]

            for strike in candidate_strikes:
                if strike in calls.index and strike in puts.index:
                    ce_price = float(calls.loc[strike, 'lastPrice'])
                    pe_price = float(puts.loc[strike, 'lastPrice'])
                    straddle_data[strike] = {
                        'combined': ce_price + pe_price,
                        'ce': round(ce_price, 2),
                        'pe': round(pe_price, 2)
                    }
        except Exception as e:
            print(f"Option chain fetch error: {e}")

    # Determine ATM Values
    if straddle_data:
        atm_strike = min(straddle_data, key=lambda k: straddle_data[k]['combined'])
        atm_ce = straddle_data[atm_strike]['ce']
        atm_pe = straddle_data[atm_strike]['pe']
    else:
        atm_strike = 24200
        atm_ce, atm_pe = 79.10, 96.10

    ce_high, ce_low = round(atm_ce + 23.70, 2), round(atm_ce - 23.70, 2)
    pe_high, pe_low = round(atm_pe + 28.80, 2), round(atm_pe - 28.80, 2)

    # Derived Calculations for Supply, Demand & Zones
    straddle_val = round(atm_ce + atm_pe, 2)
    diff_val = round(abs(atm_pe - atm_ce), 2)
    
    min_supply = round(spot_close + (atm_ce * 0.5), 2)
    min_demand = round(spot_close - (atm_pe * 0.5), 2)
    max_supply = round(spot_close + straddle_val, 2)
    max_demand = round(spot_close - straddle_val, 2)

    s1_val = round(diff_val * 1.5, 2)
    s2_val = round(diff_val * 1.2, 2)
    earth_val = round(straddle_val * 0.85, 2)

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
            "close": atm_ce,
            "low": ce_low
        },
        "pe": {
            "high": pe_high,
            "close": atm_pe,
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
            "ce": atm_ce,
            "pe": atm_pe,
            "otmCeStrike": atm_strike + 100,
            "otmCe": round(atm_ce * 0.5, 2),
            "otmPeStrike": atm_strike - 100,
            "otmPe": round(atm_pe * 0.5, 2),
            "val": s1_val
        },
        "sniper2": {
            "strike": atm_strike - 50,
            "ce": round(atm_ce * 1.2, 2),
            "pe": round(atm_pe * 0.8, 2),
            "otmCeStrike": atm_strike + 50,
            "otmCe": round(atm_ce * 0.7, 2),
            "otmPeStrike": atm_strike - 150,
            "otmPe": round(atm_pe * 0.4, 2),
            "val": s2_val
        },
        "earthVal": earth_val
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Data updated successfully with all zone metrics.")

if __name__ == "__main__":
    fetch_and_update()
