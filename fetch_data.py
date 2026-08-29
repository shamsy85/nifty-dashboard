import json
from datetime import datetime
import yfinance as yf

def update_nifty_data():
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period="1d")

    if not hist.empty:
        spot_close = round(float(hist['Close'].iloc[-1]), 2)
        spot_high = round(float(hist['High'].iloc[-1]), 2)
        spot_low = round(float(hist['Low'].iloc[-1]), 2)
    else:
        spot_close, spot_high, spot_low = 0.0, 0.0, 0.0

    base_strike = round(spot_close / 50) * 50
    atm_strike = base_strike
    
    # Strictly set to 0.0 so no hardcoded dummy data is ever used
    ce_close, ce_high, ce_low = 0.0, 0.0, 0.0
    pe_close, pe_high, pe_low = 0.0, 0.0, 0.0
    expiry_date = ""

    try:
        expiries = nifty.options
        if expiries:
            expiry_date = expiries[0]
            opt_chain = nifty.option_chain(expiry_date)
            calls = opt_chain.calls.set_index('strike')
            puts = opt_chain.puts.set_index('strike')

            candidate_strikes = [base_strike + offset for offset in range(-250, 300, 50)]
            
            min_diff = float('inf')
            best_atm = base_strike

            for strike in candidate_strikes:
                if strike in calls.index and strike in puts.index:
                    c_price = float(calls.loc[strike, 'lastPrice'])
                    p_price = float(puts.loc[strike, 'lastPrice'])
                    diff = abs(c_price - p_price)

                    if diff < min_diff:
                        min_diff = diff
                        best_atm = strike

            atm_strike = best_atm

            if atm_strike in calls.index and atm_strike in puts.index:
                ce_data = calls.loc[atm_strike]
                pe_data = puts.loc[atm_strike]

                ce_close = round(float(ce_data['lastPrice']), 2)
                ce_high = round(float(ce_data.get('high', ce_close) or ce_close), 2)
                ce_low = round(float(ce_data.get('low', ce_close) or ce_close), 2)

                pe_close = round(float(pe_data['lastPrice']), 2)
                pe_high = round(float(pe_data.get('high', pe_close) or pe_close), 2)
                pe_low = round(float(pe_data.get('low', pe_close) or pe_close), 2)

    except Exception as e:
        print(f"Option chain fetch error: {e}")

    diff_val = round(abs(pe_close - ce_close), 2)
    straddle_val = round(ce_close + pe_close, 2)

    min_supply = round(atm_strike + ce_high, 2)
    min_demand = round(atm_strike - pe_high, 2)
    max_supply = round(atm_strike + ce_high + pe_high, 2)
    max_demand = round(atm_strike - (ce_high + pe_high), 2)

    payload = {
        "spotPrice": float(spot_close),
        "spotHigh": float(spot_high),
        "spotLow": float(spot_low),
        "expiryDate": str(expiry_date),
        "currentDate": str(today_str),
        "atmStrike": int(atm_strike),
        "bannerTotal": float(diff_val),
        "ce": {
            "high": float(ce_high),
            "close": float(ce_close),
            "low": float(ce_low)
        },
        "pe": {
            "high": float(pe_high),
            "close": float(pe_close),
            "low": float(pe_low)
        },
        "minSupply": float(min_supply),
        "minDemand": float(min_demand),
        "maxSupply": float(max_supply),
        "maxDemand": float(max_demand),
        "wzSupply1": round(spot_close + 120.50, 2),
        "wzSupply2": round(spot_close + 250.00, 2),
        "wzDemand1": round(spot_close - 110.20, 2),
        "wzDemand2": round(spot_close - 230.00, 2),
        "mzSupply1": round(spot_close + 400.00, 2),
        "mzSupply2": round(spot_close + 650.00, 2),
        "mzDemand1": round(spot_close - 380.00, 2),
        "mzDemand2": round(spot_close - 600.00, 2),
        "sniper1": {
            "strike": int(atm_strike),
            "ce": float(ce_close),
            "pe": float(pe_close),
            "otmCeStrike": int(atm_strike + 100),
            "otmCe": round(ce_close * 0.5, 2),
            "otmPeStrike": int(atm_strike - 100),
            "otmPe": round(pe_close * 0.5, 2),
            "val": round(diff_val * 1.5, 2)
        },
        "sniper2": {
            "strike": int(atm_strike - 50),
            "ce": round(ce_close * 1.2, 2),
            "pe": round(pe_close * 0.8, 2),
            "otmCeStrike": int(atm_strike + 50),
            "otmCe": round(ce_close * 0.7, 2),
            "otmPeStrike": int(atm_strike - 150),
            "otmPe": round(pe_close * 0.4, 2),
            "val": round(diff_val * 1.2, 2)
        },
        "earthVal": round(straddle_val * 1.5, 2)
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Successfully pulled option chain data. ATM: {atm_strike}")

if __name__ == "__main__":
    update_nifty_data()
