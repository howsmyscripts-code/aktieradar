import yfinance as yf
import json
from datetime import datetime

STOCKS = [
    # Sverige
    "INVE-B.ST", "ATCO-B.ST", "SWED-A.ST", "SAAB-B.ST", "ERIC-B.ST",
    "VOLV-B.ST", "EQT.ST", "HM-B.ST", "SEB-A.ST", "TEL2-B.ST",
    # Europa
    "ASML", "SAP", "NVO", "LVMUY", "SHEL", "SIEGY", "NSRGY", "EADSY", "AZN", "RELX", "BAESY",
    # USA
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "JPM", "BRK-B", "LLY",
    # Asien - Kina
    "BABA", "TCEHY", "PDD", "BYDDF", "JD",
    # Asien - Taiwan
    "TSM", "CAMT",
    # Asien - Japan
    "TM", "SONY", "NTDOY", "FANUY", "MUFG",
    # Asien - Sydkorea
    "SSNLF", "005380.KS", "000660.KS",
]

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = 0, 0
    for i in range(len(closes) - period, len(closes)):
        d = closes[i] - closes[i-1]
        if d > 0: gains += d
        else: losses -= d
    ag, al = gains/period, losses/period
    return round(100 - 100/(1 + ag/al), 1) if al != 0 else 100

def calc_ma(closes, period):
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 2)

def compute_signal(rsi, ma50, ma200, change):
    score = 5
    if rsi is not None:
        if rsi < 30: score += 3
        elif rsi < 40: score += 2
        elif rsi < 45: score += 1
        elif rsi > 75: score -= 3
        elif rsi > 65: score -= 2
        elif rsi > 58: score -= 1
    if ma50 and ma200:
        gap = ((ma50 - ma200) / ma200) * 100
        if gap > 3: score += 2
        elif gap > 0: score += 1
        elif gap < -3: score -= 2
        else: score -= 1
    if change:
        if change > 3: score += 1
        elif change < -3: score -= 1
    score = max(1, min(10, score))
    signal = "KOP" if score >= 7 else "SALJ" if score <= 4 else "HALL"
    return signal, score

results = {}
for sym in STOCKS:
    try:
        ticker = yf.Ticker(sym)
        hist = ticker.history(period="1y")
        if len(hist) < 20:
            raise ValueError("Too little data")
        closes = hist["Close"].tolist()
        price = round(closes[-1], 2)
        change = round(((closes[-1] - closes[-2]) / closes[-2]) * 100, 2) if len(closes) > 1 else 0
        rsi = calc_rsi(closes)
        ma50 = calc_ma(closes, 50)
        ma200 = calc_ma(closes, 200)
        signal, styrka = compute_signal(rsi, ma50, ma200, change)
        results[sym] = {
            "price": price, "change": change,
            "rsi": rsi, "ma50": ma50, "ma200": ma200,
            "signal": signal, "styrka": styrka, "ok": True
        }
        print(f"OK {sym}: {price} {signal}")
    except Exception as e:
        results[sym] = {"ok": False, "error": str(e)}
        print(f"FAIL {sym}: {e}")

output = {
    "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "stocks": results
}

with open("data.json", "w") as f:
    json.dump(output, f)

print(f"\nDone: {sum(1 for v in results.values() if v.get('ok'))} / {len(results)} succeeded")
