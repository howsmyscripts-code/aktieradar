import yfinance as yf
import json
import urllib.request
import urllib.parse
import re
import time
from datetime import datetime, timezone, timedelta

# Company names for news search
COMPANY_NAMES = {
    "INVE-B.ST": "Investor B aktie",
    "ATCO-B.ST": "Atlas Copco aktie",
    "SWED-A.ST": "Swedbank aktie",
    "SAAB-B.ST": "Saab aktie",
    "ERIC-B.ST": "Ericsson aktie",
    "VOLV-B.ST": "Volvo aktie",
    "EQT.ST":    "EQT aktie",
    "HM-B.ST":   "H&M aktie",
    "SEB-A.ST":  "SEB bank aktie",
    "TEL2-B.ST": "Tele2 aktie",
    "ASML":      "ASML stock",
    "SAP":       "SAP SE stock",
    "NVO":       "Novo Nordisk stock",
    "LVMUY":     "LVMH stock",
    "SHEL":      "Shell stock",
    "SIEGY":     "Siemens stock",
    "NSRGY":     "Nestle stock",
    "EADSY":     "Airbus stock",
    "AZN":       "AstraZeneca stock",
    "RELX":      "RELX stock",
    "BAESY":     "BAE Systems stock",
    "NVDA":      "Nvidia stock",
    "AAPL":      "Apple stock",
    "MSFT":      "Microsoft stock",
    "AMZN":      "Amazon stock",
    "GOOGL":     "Alphabet Google stock",
    "META":      "Meta Platforms stock",
    "TSLA":      "Tesla stock",
    "JPM":       "JPMorgan stock",
    "BRK-B":     "Berkshire Hathaway stock",
    "LLY":       "Eli Lilly stock",
    "BABA":      "Alibaba stock",
    "TCEHY":     "Tencent stock",
    "PDD":       "PDD Holdings stock",
    "BYDDF":     "BYD stock",
    "JD":        "JD.com stock",
    "TSM":       "TSMC Taiwan Semiconductor stock",
    "CAMT":      "Camtek stock",
    "TM":        "Toyota stock",
    "SONY":      "Sony stock",
    "MUFG":      "Mitsubishi UFJ stock",
    "005930.KS": "Samsung Electronics stock",
    "005380.KS": "Hyundai Motor stock",
    "000660.KS": "SK Hynix stock",
    "CL=F":      "crude oil price",
    "GC=F":      "gold price",
    "SI=F":      "silver price",
    "BTC-USD":   "Bitcoin price",
    "ETH-USD":   "Ethereum price",
}

def fetch_news_headlines(sym, max_headlines=5):
    """Fetch latest news headlines from Google News RSS"""
    query = COMPANY_NAMES.get(sym, sym)
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=sv&gl=SE&ceid=SE:sv"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            xml = r.read().decode("utf-8", errors="ignore")
        titles = re.findall(r"<title><![CDATA[(.*?)]]></title>", xml)
        if not titles:
            titles = re.findall(r"<title>(.*?)</title>", xml)
        # Skip first title (feed title)
        headlines = [t for t in titles[1:max_headlines+1] if t]
        return headlines
    except Exception as e:
        print(f"  News fetch failed for {sym}: {e}")
        return []

def analyze_news_sentiment(sym, headlines, signal, styrka):
    """Use Claude API to analyze news sentiment and adjust signal"""
    if not headlines:
        return 0, []
    
    headlines_text = "\n".join(f"- {h}" for h in headlines)
    company = COMPANY_NAMES.get(sym, sym)
    
    prompt = f"""Du är en finansanalytiker. Analysera dessa nyhetsrubriker för {company} och bedöm hur de påverkar aktiekursen på kort sikt (1-5 dagar).

Nyhetsrubriker:
{headlines_text}

Aktuell teknisk signal: {signal} (styrka {styrka}/10)

Svara ENDAST med ett JSON-objekt i detta exakta format, inget annat:
{{"sentiment": 1, "reason": "kort förklaring på svenska", "headlines": ["relevant rubrik 1", "relevant rubrik 2"]}}

Sentiment-värden:
2 = Mycket positivt (stor order, starkt resultat, genombrott)
1 = Positivt (mindre positiv nyhet)  
0 = Neutralt eller blandat
-1 = Negativt (varning, nedgång, förlust)
-2 = Mycket negativt (kris, stor förlust, skandal)"""

    try:
        import urllib.request
        import json as _json
        
        data = _json.dumps({
            "model": "claude-opus-4-5",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")
        
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": __import__("os").environ.get("ANTHROPIC_API_KEY", "")
            }
        )
        
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = _json.loads(r.read().decode())
        
        text = resp["content"][0]["text"].strip()
        # Clean up any markdown
        text = re.sub(r"```json|```", "", text).strip()
        result = _json.loads(text)
        
        sentiment = int(result.get("sentiment", 0))
        reason = result.get("reason", "")
        rel_headlines = result.get("headlines", headlines[:2])
        
        print(f"  News sentiment {sym}: {sentiment} — {reason}")
        return sentiment, rel_headlines, reason
        
    except Exception as e:
        print(f"  Claude API error for {sym}: {e}")
        return 0, headlines[:2], ""


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
    # Råvaror & Krypto
    "CL=F", "GC=F", "SI=F", "BTC-USD", "ETH-USD",
    "VALOUR-BTCST-SEK.ST", "VALOUR-TAO-SEK.ST", "VALOUR-APTO-SEK.ST",
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
        min_bars = 2 if sym.startswith("VALOUR-") else 20
        if len(hist) < min_bars:
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

        # Fetch ATH using daily High prices for market symbols
        ath = None
        if sym in ["CL=F", "GC=F", "SI=F", "BTC-USD", "ETH-USD"]:
            try:
                hist_max = ticker.history(period="max")
                if len(hist_max) > 0 and "High" in hist_max.columns:
                    all_highs = [h for h in hist_max["High"].tolist() if h and not math.isnan(float(h))]
                    ath = round(max(all_highs), 2) if all_highs else None
            except:
                ath = None

        results[sym] = {
            "price": price, "change": change,
            "rsi": safe(rsi), "ma50": safe(ma50), "ma200": safe(ma200),
            "macd": round(macd, 3) if macd and not math.isnan(macd) else None,
            "bollinger": safe(bollinger),
            "w52": safe(w52_pos),
            "trend": safe(trend),
            "signal": signal, "styrka": styrka, "ok": True,
            "ath": ath,
            "news_sentiment": news_sentiment,
            "news_reason": news_reason,
            "news_headlines": news_headlines[:3]
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
