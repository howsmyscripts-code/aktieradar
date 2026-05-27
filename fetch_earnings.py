import yfinance as yf
import json
import math
from datetime import datetime, timezone, timedelta

# Swedish stocks - hardcoded quarterly dates (updated each quarter)
# Format: "SYM": ["YYYY-MM-DD", ...]  -- next known report dates
SWEDISH_EARNINGS = {
    "INVE-B.ST":  "2026-07-18",
    "ATCO-B.ST":  "2026-07-17",
    "SWED-A.ST":  "2026-07-17",
    "SAAB-B.ST":  "2026-07-18",
    "ERIC-B.ST":  "2026-07-15",
    "VOLV-B.ST":  "2026-07-22",
    "KINV-B.ST":  "2026-08-20",
    "HM-B.ST":    "2026-06-25",
    "SEB-A.ST":   "2026-07-17",
    "TEL2-B.ST":  "2026-07-21",
    "BEAMMW-B.ST":"2026-08-14",
    "XACT.ST":    None,
    "XACTHDIV.ST":None,
}

# Global stocks - fetch from Yahoo Finance
GLOBAL_STOCKS = [
    "ASML", "SAP", "NVO", "LVMUY", "SHEL", "SIEGY", "NSRGY", "EADSY", "AZN", "RELX", "BAESY",
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "JPM", "BRK-B", "LLY",
    "BABA", "TCEHY", "PDD", "BYDDF", "JD", "TSM", "CAMT", "TM", "SONY", "MUFG",
    "005930.KS", "005380.KS", "000660.KS",
]

earnings = {}

# Add Swedish stocks
for sym, date in SWEDISH_EARNINGS.items():
    earnings[sym] = date

# Fetch global stocks from Yahoo Finance
today = datetime.now(timezone.utc).date()
for sym in GLOBAL_STOCKS:
    try:
        t = yf.Ticker(sym)
        ed = None
        
        # Try calendar first
        try:
            cal = t.calendar
            if cal is not None and not cal.empty:
                dates = list(cal.columns) if hasattr(cal, 'columns') else []
                if dates:
                    d = dates[0]
                    if hasattr(d, 'strftime'):
                        ed = d.strftime("%Y-%m-%d")
                    else:
                        ed = str(d)[:10]
        except:
            pass
        
        # Try info
        if not ed:
            info = t.info
            raw = info.get("earningsDate") or info.get("nextEarningsDate")
            if raw:
                if isinstance(raw, (int, float)) and not math.isnan(raw):
                    ed = datetime.fromtimestamp(raw).strftime("%Y-%m-%d")
                elif isinstance(raw, str):
                    ed = raw[:10]
        
        # Only save future dates
        if ed:
            try:
                if datetime.strptime(ed, "%Y-%m-%d").date() >= today:
                    earnings[sym] = ed
                    print(f"✓ {sym}: {ed}")
                else:
                    earnings[sym] = None
                    print(f"  {sym}: {ed} (past)")
            except:
                earnings[sym] = None
        else:
            earnings[sym] = None
            print(f"  {sym}: no data")
            
    except Exception as e:
        earnings[sym] = None
        print(f"✗ {sym}: {e}")

output = {
    "updated": (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M svensk tid"),
    "earnings": earnings
}

with open("earnings.json", "w") as f:
    json.dump(output, f, indent=2)

found = sum(1 for v in earnings.values() if v)
print(f"\nDone: {found}/{len(earnings)} earnings dates found")
