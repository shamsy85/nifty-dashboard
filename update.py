import json
from datetime import datetime
import yfinance as yf

def fetch_and_process():
    print("Fetching NIFTY index data via yfinance...")
    nifty = yf.Ticker("^NSEI")
    
    # Get live spot price
    history = nifty.history(period="5d")
    if history.empty:
        raise Exception("Could not fetch spot price from Yahoo Finance.")
    
    spot = float(history["Close"].iloc[-1])
    atm = int(round(spot / 50.0) * 50)
    print(f"Spot Price: {spot}, ATM Strike: {atm}")

    # Get available expiry dates
    expiries = nifty.options
    if not expiries:
        raise Exception("No option chain expiries found.")
    
    current_expiry = expiries[0]
    print(f"Current Expiry: {current_expiry}")

    # Fetch option chain for nearest expiry
    opt = nifty.option_chain(current_expiry)
    calls = opt.calls
    puts = opt.puts

    def get_strike_info(strike):
        c_row = calls[calls["strike"] == strike]
        p_row = puts[puts["strike"] == strike]

        c_close = float(c_row["lastPrice"].iloc[0]) if not c_row.empty else 0.0
        c_high = float(c_row["high"].iloc[0]) if not c_row.empty and "high" in c_row and not c_row["high"].isnull().all() else c_close
        c_low = float(c_row["low"].iloc[0]) if not c_row.empty and "low" in c_row and not c_row["low"].isnull().all() else c_close

        p_close = float(p_row["lastPrice"].iloc[0]) if not p_row.empty else 0.0
        p_high = float(p_row["high"].iloc[0]) if not p_row.empty and "high" in p_row and not p_row["high"].isnull().all() else p_close
        p_low = float(p_row["low"].iloc[0]) if not p_row.empty and "low" in p_row and not p_row["low"].isnull().all() else p_close

        return {
            "ce_high": c_high, "ce_close": c_close, "ce_low": c_low,
            "pe_high": p_high, "pe_close": p_close, "pe_low": p_low
        }

    atm_data = get_strike_info(atm)
    snip1_otm_ce = get_strike_info(atm + 50)
    snip1_otm_pe = get_strike_info(atm - 50)
    snip2_otm_ce = get_strike_info(atm + 100)
    snip2_otm_pe = get_strike_info(atm - 100)

    output = {
        "currentDate": datetime.now().strftime("%d %b %Y").upper(),
        "expiryDate": str(current_expiry).upper(),
        "spotPrice": round(spot, 2),
        "atmStrike": atm,

        "ce": {
            "high": atm_data["ce_high"],
            "close": atm_data["ce_close"],
            "low": atm_data["ce_low"]
        },
        "pe": {
            "high": atm_data["pe_high"],
            "close": atm_data["pe_close"],
            "low": atm_data["pe_low"]
        },

        "bannerTotal": round(atm_data["ce_close"] + atm_data["pe_close"], 2),
        "spotHigh": round(spot + 50.0, 2),
        "spotLow": round(spot - 50.0, 2),

        "sniper1": {
            "strike": atm,
            "ce": atm_data["ce_close"],
            "pe": atm_data["pe_close"],
            "otmCeStrike": atm + 50,
            "otmPeStrike": atm - 50,
            "otmCe": snip1_otm_ce["ce_close"],
            "otmPe": snip1_otm_pe["pe_close"]
        },

        "sniper2": {
            "strike": atm,
            "ce": atm_data["ce_close"],
            "pe": atm_data["pe_close"],
            "otmCeStrike": atm + 100,
            "otmPeStrike": atm - 100,
            "otmCe": snip2_otm_ce["ce_close"],
            "otmPe": snip2_otm_pe["pe_close"]
        }
    }

    with open("data.json", "w") as f:
        json.dump(output, f, indent=2)

    print("SUCCESS: data.json generated!")

if __name__ == "__main__":
    fetch_and_process()
