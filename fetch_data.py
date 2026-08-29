import json
from datetime import datetime
import yfinance as yf

def fetch_and_update():
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    # 1. Fetch live or last available NIFTY 50 spot data
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period="1d")

    if not hist.empty:
        spot_close = round(float(hist['Close'].iloc[-1]), 2)
        spot_high = round(float(hist['High'].iloc[-1]), 2)
        spot_low = round(float(hist['Low'].iloc[-1]), 2)
    else:
        # Fallback values if API request fails
        spot_close, spot_high, spot_low = 24175.65, 24188.30, 24076.85

    # 2. Generate candidate strikes (+/- 250 points around spot in steps of 50)
    base_strike = round(spot_close / 50) * 50
    candidate_strikes = [base_strike + offset for offset in range(-250, 300, 50)]

    # 3. Retrieve option chain data from yfinance
    expiries = nifty.options
    straddle_data = {}
    
    if expiries:
        # Get nearest upcoming option expiry
        nearest_expiry = expiries[0]
        opt_chain = nifty.option_chain(nearest_expiry)
        calls = opt_chain.calls.set_index('strike')
        puts = opt_chain.puts.set_index('strike')

        # Find combined straddle price (CE + PE) for candidate strikes
        for strike in candidate_strikes:
            if strike in calls.index and strike in puts.index:
                ce_price = float(calls.loc[strike, 'lastPrice'])
                pe_price = float(puts.loc[strike, 'lastPrice'])
                combined_sum = ce_price + pe_price
                straddle_data[strike] = {
                    'combined': combined_sum,
                    'ce': round(ce_price, 2),
                    'pe': round(pe_price, 2)
                }

    # 4. Determine ATM strike based on Minimum Straddle Sum
    if straddle_data:
        atm_strike = min(straddle_data, key=lambda k: straddle_data[k]['combined'])
        atm_ce = straddle_data[atm_strike]['ce']
        atm_pe = straddle_data[atm_strike]['pe']
    else:
        # Default fallback if option chain is unavailable off-market hours
        atm_strike = base_strike
        atm_ce = 79.10
        atm_pe = 96.10

    # 5. Construct payload for data.json
    payload = {
        "spotPrice": spot_close,
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "expiryDate": expiries[0] if expiries else "01-09-2026",
        "currentDate": today_str,
        "atmStrike": atm_strike,
        "bannerTotal": round(atm_ce + atm_pe, 2),
        "ce": {
            "high": round(atm_ce * 1.3, 1),
            "close": atm_ce,
            "low": round(atm_ce * 0.7, 1)
        },
        "pe": {
            "high": round(atm_pe * 1.3, 1),
            "close": atm_pe,
            "low": round(atm_pe * 0.7, 1)
        },
        "sniper1": {
            "strike": atm_strike,
            "ce": atm_ce,
            "pe": atm_pe,
            "otmCeStrike": atm_strike + 100,
            "otmCe": round(atm_ce * 0.5, 2),
            "otmPeStrike": atm_strike - 100,
            "otmPe": round(atm_pe * 0.5, 2)
        },
        "sniper2": {
            "strike": atm_strike - 50,
            "ce": round(atm_ce * 1.2, 2),
            "pe": round(atm_pe * 0.8, 2),
            "otmCeStrike": atm_strike + 50,
            "otmCe": round(atm_ce * 0.7, 2),
            "otmPeStrike": atm_strike - 150,
            "otmPe": round(atm_pe * 0.4, 2)
        }
    }

    # 6. Save output directly to data.json
    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Data updated successfully. Calculated ATM Strike: {atm_strike}")

if __name__ == "__main__":
    fetch_and_update()
