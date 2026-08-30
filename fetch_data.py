import json
from datetime import datetime
import yfinance as yf

def update_nifty_data():
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period="1d")

    if not hist.empty:
        spot_close = round(float(hist['Close'].iloc[-1]), 2)
        spot_high = round(float(hist['High'].iloc[-1]), 2)
        spot_low = round(float(hist['Low'].iloc[-1]), 2)
        today_str = hist.index[-1].strftime("%d-%m-%Y")
    else:
        spot_close, spot_high, spot_low = 0.0, 0.0, 0.0
        today_str = datetime.now().strftime("%d-%m-%Y")

    ce_close, ce_high, ce_low = 0.0, 0.0, 0.0
    pe_close, pe_high, pe_low = 0.0, 0.0, 0.0
    expiry_date = ""
    atm_strike = 0

    calls = None
    puts = None

    try:
        expiries = nifty.options
        if expiries:
            expiry_date = expiries[0]
            opt_chain = nifty.option_chain(expiry_date)
            calls = opt_chain.calls.set_index('strike')
            puts = opt_chain.puts.set_index('strike')

            common_strikes = sorted(list(set(calls.index).intersection(set(puts.index))))
            
            if common_strikes:
                min_diff = float('inf')
                best_atm = common_strikes[0]

                for strike in common_strikes:
                    c_price = float(calls.loc[strike, 'lastPrice'])
                    p_price = float(puts.loc[strike, 'lastPrice'])
                    diff = abs(c_price - p_price)

                    if diff < min_diff:
                        min_diff = diff
                        best_atm = strike

                atm_strike = int(best_atm)

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

    diff_val = round(ce_close - pe_close, 2)

    min_supply = round(atm_strike + ce_close, 2) if atm_strike else 0.0
    min_demand = round(atm_strike - pe_close, 2) if atm_strike else 0.0
    max_supply = round(atm_strike + (ce_close + pe_close), 2) if atm_strike else 0.0
    max_demand = round(atm_strike - (pe_close + ce_close), 2) if atm_strike else 0.0

    sniper_atm_100 = int(round(atm_strike / 100.0) * 100) if atm_strike else 0
    s1_strike = sniper_atm_100
    otm_ce_s1 = s1_strike + 100
    otm_pe_s1 = s1_strike - 100
    
    otm_ce_val_s1 = round(ce_close * 0.5, 2)
    otm_pe_val_s1 = round(pe_close * 0.5, 2)

    s2_strike = sniper_atm_100 - 50 if sniper_atm_100 else 0
    otm_ce_s2 = s2_strike + 100
    otm_pe_s2 = s2_strike - 100
    
    otm_ce_val_s2 = round(ce_close * 0.7, 2)
    otm_pe_val_s2 = round(pe_close * 0.4, 2)

    try:
        if calls is not None and puts is not None:
            if otm_ce_s1 in calls.index:
                otm_ce_val_s1 = round(float(calls.loc[otm_ce_s1, 'lastPrice']), 2)
            if otm_pe_s1 in puts.index:
                otm_pe_val_s1 = round(float(puts.loc[otm_pe_s1, 'lastPrice']), 2)

            if otm_ce_s2 in calls.index:
                otm_ce_val_s2 = round(float(calls.loc[otm_ce_s2, 'lastPrice']), 2)
            if otm_pe_s2 in puts.index:
                otm_pe_val_s2 = round(float(puts.loc[otm_pe_s2, 'lastPrice']), 2)
    except Exception as ex:
        print(f"Sniper chain lookup error: {ex}")

    s1_sniper_val = round((otm_ce_val_s1 + otm_pe_val_s1) / 2.0, 2)
    s2_sniper_val = round((otm_ce_val_s2 + otm_pe_val_s2) / 2.0, 2)

    earth_val = round((spot_high - spot_low) * 0.2611, 2) if spot_high and spot_low else 0.0

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
            "strike": int(s1_strike),
            "ce": float(otm_ce_val_s1),
            "pe": float(otm_pe_val_s1),
            "otmCeStrike": int(otm_ce_s1),
            "otmCe": float(otm_ce_val_s1),
            "otmPeStrike": int(otm_pe_s1),
            "otmPe": float(otm_pe_val_s1),
            "val": float(s1_sniper_val)
        },
        "sniper2": {
            "strike": int(s2_strike),
            "ce": float(otm_ce_val_s2),
            "pe": float(otm_pe_val_s2),
            "otmCeStrike": int(otm_ce_s2),
            "otmCe": float(otm_ce_val_s2),
            "otmPeStrike": int(otm_pe_s2),
            "otmPe": float(otm_pe_val_s2),
            "val": float(s2_sniper_val)
        },
        "earthVal": float(earth_val)
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Successfully processed option chain for {today_str}. ATM: {atm_strike}, Earth: {earth_val}")

if __name__ == "__main__":
    update_nifty_data()
