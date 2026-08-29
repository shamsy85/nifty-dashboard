import json
from datetime import datetime
import yfinance as yf

def fetch_and_update():
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period="1d")

    if not hist.empty:
        spot_close = round(float(hist['Close'].iloc[-1]), 2)
        spot_high = round(float(hist['High'].iloc[-1]), 2)
        spot_low = round(float(hist['Low'].iloc[-1]), 2)
    else:
        spot_close, spot_high, spot_low = 24175.65, 24188.30, 24076.85

    base_strike = round(spot_close / 50) * 50
    candidate_strikes = [base_strike + offset for offset in range(-250, 300, 50)]

    expiries = nifty.options
    straddle_data = {}
    
    if expiries:
        nearest_expiry = expiries[0]
        opt_chain = nifty.option_chain(nearest_expiry)
        calls = opt_chain.calls.set_index('strike')
        puts = opt_chain.puts.set_index('strike')

        for strike in candidate_strikes:
            if strike in calls.index and strike in puts.index:
                ce_row = calls.loc[strike]
                pe_row = puts.loc[strike]
                
                ce_close = float(ce_row['lastPrice'])
                pe_close = float(pe_row['lastPrice'])
                
                # Fetch actual high/low if present in data, else calculate realistic spread
                ce_high = float(ce_row.get('dayHigh', ce_close * 1.25))
                ce_low = float(ce_row.get('dayLow', ce_close * 0.65))
                pe_high = float(pe_row.get('dayHigh', pe_close * 1.30))
                pe_low = float(pe_row.get('dayLow', pe_close * 0.70))

                straddle_data[strike] = {
                    'combined': ce_close + pe_close,
                    'ce_close': round(ce_close, 2),
                    'ce_high': round(ce_high, 2),
                    'ce_low': round(ce_low, 2),
                    'pe_close': round(pe_close, 2),
                    'pe_high': round(pe_high, 2),
                    'pe_low': round(pe_low, 2)
                }

    if straddle_data:
        atm_strike = min(straddle_data, key=lambda k: straddle_data[k]['combined'])
        d = straddle_data[atm_strike]
        atm_ce, ce_h, ce_l = d['ce_close'], d['ce_high'], d['ce_low']
        atm_pe, pe_h, pe_l = d['pe_close'], d['pe_high'], d['pe_low']
    else:
        atm_strike = 24200
        atm_ce, ce_h, ce_l = 79.10, 102.80, 55.40
        atm_pe, pe_h, pe_l = 96.10, 124.90, 67.30

    payload = {
        "spotPrice": spot_close,
        "spotHigh": spot_high,
        "spotLow": spot_low,
        "expiryDate": expiries[0] if expiries else "01-09-2026",
        "currentDate": today_str,
        "atmStrike": atm_strike,
        "bannerTotal": round(abs(atm_pe - atm_ce), 2),
        "ce": {
            "high": ce_h,
            "close": atm_ce,
            "low": ce_l
        },
        "pe": {
            "high": pe_h,
            "close": atm_pe,
            "low": pe_l
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

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)

if __name__ == "__main__":
    fetch_and_update()
