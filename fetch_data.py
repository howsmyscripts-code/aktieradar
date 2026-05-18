import yfinance as yf
import json
from datetime import datetime, timezone, timedelta

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
    "005930.KS", "005380.KS", "000660.KS",
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

def calc_macd(closes):
    """MACD = EMA12 - EMA26, Signal = EMA9 of MACD"""
    import math
    if len(closes) < 26:
        return None, None
    # Filter out NaN/None values
    closes = [c for c in closes if c and not math.isnan(float(c))]
    if len(closes) < 26:
        return None, None
    def ema(data, period):
        k = 2 / (period + 1)
        result = [data[0]]
        for p in data[1:]:
            val = p * k + result[-1] * (1 - k)
            result.append(val if not math.isnan(val) else result[-1])
        return result
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    signal_line = ema(macd_line, 9)
    v1, v2 = macd_line[-1], signal_line[-1]
    if math.isnan(v1) or math.isnan(v2):
        return None, None
    return v1, v2

def calc_bollinger(closes, period=20):
    """Returns position within Bollinger Bands: 0=lower, 0.5=middle, 1=upper"""
    if len(closes) < period:
        return None
    recent = closes[-period:]
    mean = sum(recent) / period
    std = (sum((x - mean)**2 for x in recent) / period) ** 0.5
    if std == 0:
        return 0.5
    upper = mean + 2 * std
    lower = mean - 2 * std
    pos = (closes[-1] - lower) / (upper - lower)
    return round(max(0, min(1, pos)), 2)

def calc_52w_position(closes):
    """Position within 52-week range: 0=low, 1=high"""
    if len(closes) < 2:
        return None
    high = max(closes[-252:]) if len(closes) >= 252 else max(closes)
    low = min(closes[-252:]) if len(closes) >= 252 else min(closes)
    if high == low:
        return 0.5
    return round((closes[-1] - low) / (high - low), 2)

def calc_trend_strength(closes, period=20):
    """How many of last N days have been positive"""
    if len(closes) < period + 1:
        return None
    ups = sum(1 for i in range(-period, 0) if closes[i] > closes[i-1])
    return round(ups / period, 2)

def calc_volume_signal(volumes, closes):
    """Rising price + high volume = bullish, falling price + high volume = bearish"""
    if not volumes or len(volumes) < 20:
        return 0
    avg_vol = sum(volumes[-20:]) / 20
    latest_vol = volumes[-1]
    vol_ratio = latest_vol / avg_vol if avg_vol > 0 else 1
    price_change = (closes[-1] - closes[-2]) / closes[-2] if len(closes) > 1 else 0
    if vol_ratio > 1.5 and price_change > 0:
        return 1  # Bullish: high volume + rising price
    elif vol_ratio > 1.5 and price_change < 0:
        return -1  # Bearish: high volume + falling price
    return 0

def compute_signal(rsi, ma50, ma200, change, macd=None, macd_signal=None,
                   bollinger=None, w52_pos=None, trend=None, vol_signal=0):
    score = 5.0

    # 1. RSI (oversold/overbought)
    if rsi is not None:
        if rsi < 25: score += 3
        elif rsi < 35: score += 2
        elif rsi < 45: score += 1
        elif rsi > 80: score -= 3
        elif rsi > 70: score -= 2
        elif rsi > 60: score -= 1

    # 2. MA50 vs MA200 (trend direction)
    if ma50 and ma200:
        gap = ((ma50 - ma200) / ma200) * 100
        if gap > 5: score += 2
        elif gap > 0: score += 1
        elif gap < -5: score -= 2
        else: score -= 1

    # 3. MACD (momentum)
    if macd is not None and macd_signal is not None:
        if macd > macd_signal and macd > 0: score += 1.5
        elif macd > macd_signal: score += 0.5
        elif macd < macd_signal and macd < 0: score -= 1.5
        elif macd < macd_signal: score -= 0.5

    # 4. Bollinger Bands (relative position)
    if bollinger is not None:
        if bollinger < 0.2: score += 1.5   # Near lower band = oversold
        elif bollinger < 0.35: score += 0.5
        elif bollinger > 0.8: score -= 1.5  # Near upper band = overbought
        elif bollinger > 0.65: score -= 0.5

    # 5. 52-week position
    if w52_pos is not None:
        if w52_pos < 0.15: score += 1.5   # Near 52-week low = possible value
        elif w52_pos < 0.3: score += 0.5
        elif w52_pos > 0.85: score -= 1    # Near 52-week high = stretched
        elif w52_pos > 0.7: score -= 0.5

    # 6. Trend strength (momentum)
    if trend is not None:
        if trend > 0.7: score += 1
        elif trend > 0.6: score += 0.5
        elif trend < 0.3: score -= 1
        elif trend < 0.4: score -= 0.5

    # 7. Volume signal
    score += vol_signal * 0.5

    # 8. Daily change (momentum confirmation)
    if change:
        if change > 4: score += 0.5
        elif change < -4: score -= 0.5

    score = max(1, min(10, round(score)))
    signal = "KOP" if score >= 7 else "SALJ" if score <= 4 else "HALL"
    return signal, score

results = {}
for sym in STOCKS:
    try:
        ticker = yf.Ticker(sym)
        hist = ticker.history(period="1y")
        if len(hist) < 20:
            raise ValueError("Too little data")
        import math
        closes = [c for c in hist["Close"].tolist() if c and not math.isnan(float(c))]
        volumes = [v for v in hist["Volume"].tolist() if v and not math.isnan(float(v))] if "Volume" in hist.columns else []
        price = round(closes[-1], 2)
        change = round(((closes[-1] - closes[-2]) / closes[-2]) * 100, 2) if len(closes) > 1 else 0
        rsi = calc_rsi(closes)
        ma50 = calc_ma(closes, 50)
        ma200 = calc_ma(closes, 200)
        macd, macd_sig = calc_macd(closes)
        bollinger = calc_bollinger(closes)
        w52_pos = calc_52w_position(closes)
        trend = calc_trend_strength(closes)
        vol_signal = calc_volume_signal(volumes, closes)
        signal, styrka = compute_signal(
            rsi, ma50, ma200, change,
            macd=macd, macd_signal=macd_sig,
            bollinger=bollinger, w52_pos=w52_pos,
            trend=trend, vol_signal=vol_signal
        )
        import math
        def safe(v): return None if v is None or (isinstance(v, float) and math.isnan(v)) else v
        results[sym] = {
            "price": price, "change": change,
            "rsi": safe(rsi), "ma50": safe(ma50), "ma200": safe(ma200),
            "macd": round(macd, 3) if macd and not math.isnan(macd) else None,
            "bollinger": safe(bollinger),
            "w52": safe(w52_pos),
            "trend": safe(trend),
            "signal": signal, "styrka": styrka, "ok": True
        }
        print(f"OK {sym}: {price} {signal} (RSI:{rsi} BB:{bollinger} 52w:{w52_pos} Trend:{trend})")
    except Exception as e:
        results[sym] = {"ok": False, "error": str(e)}
        print(f"FAIL {sym}: {e}")

output = {
    "updated": (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M svensk tid"),
    "stocks": results
}

with open("data.json", "w") as f:
    json.dump(output, f)

print(f"\nDone: {sum(1 for v in results.values() if v.get('ok'))} / {len(results)} succeeded")
