import yfinance as yf
import pandas as pd

BENCHMARK = "^GSPC"

def get_last_value(data):
    if hasattr(data, "dropna"):
        value = data.dropna().iloc[-1]
    else:
        value = data

    if hasattr(value, "iloc"):
        value = value.iloc[0]

    return float(value)

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_series(symbol):
    df = yf.download(symbol, period="2y", interval="1d", progress=False, auto_adjust=True)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def scan_stock(symbol, benchmark_perf_6m, benchmark_perf_1y):
    try:
        df = get_series(symbol)
        if df is None or len(df) < 260:
            return None

        close = df["Close"]
        volume = df["Volume"]

        price = get_last_value(close)
        sma20 = get_last_value(close.rolling(20).mean())
        sma50 = get_last_value(close.rolling(50).mean())
        sma200 = get_last_value(close.rolling(200).mean())
        rsi = get_last_value(calculate_rsi(close))

        high_52w = get_last_value(close.tail(252).max())
        high_alltime = get_last_value(close.max())

        distance_52w = (price / high_52w - 1) * 100
        distance_ath = (price / high_alltime - 1) * 100

        perf_6m = (price / get_last_value(close.iloc[[-126]])) * 100 - 100
        perf_1y = (price / get_last_value(close.iloc[[-252]])) * 100 - 100

        relative_strength_6m = perf_6m - benchmark_perf_6m
        relative_strength_1y = perf_1y - benchmark_perf_1y

        vol_avg50 = get_last_value(volume.rolling(50).mean())
        vol_now = get_last_value(volume)

        score = 0
        score += 15 if price > sma200 else 0
        score += 15 if sma50 > sma200 else 0
        score += 10 if price > sma50 else 0
        score += 10 if price > sma20 else 0
        score += 15 if distance_52w > -10 else 0
        score += 10 if relative_strength_6m > 0 else 0
        score += 10 if relative_strength_1y > 0 else 0
        score += 10 if 50 <= rsi <= 75 else 0
        score += 5 if vol_now > vol_avg50 else 0

        if score >= 80:
            signal = "🔥 Top-Kandidat"
        elif score >= 60:
            signal = "👀 Beobachten"
        else:
            signal = "❌ Kein Trend"

        if price > sma50 > sma200:
            trend = "↑ Aufwärtstrend"
        elif price < sma50 < sma200:
            trend = "↓ Abwärtstrend"
        else:
            trend = "→ Seitwärts/unklar"

        if score >= 80 and -8 <= distance_52w <= 0 and 50 <= rsi <= 70:
            kaufzone = "✅ mögliche Kaufzone"
        elif score >= 80 and rsi > 75:
            kaufzone = "⚠️ heiß gelaufen"
        elif score >= 60:
            kaufzone = "👀 beobachten"
        else:
            kaufzone = "❌ nein"

        return {
            "Symbol": symbol,
            "Kurs": round(price, 2),
            "Score": score,
            "Signal": signal,
            "Trend": trend,
            "Kaufzone": kaufzone,
            "RSI": round(rsi, 1),
            "SMA20": round(sma20, 2),
            "SMA50": round(sma50, 2),
            "SMA200": round(sma200, 2),
            "Abstand 52W Hoch %": round(distance_52w, 1),
            "Abstand ATH %": round(distance_ath, 1),
            "Perf. 6M %": round(perf_6m, 1),
            "Perf. 1J %": round(perf_1y, 1),
            "Rel. Stärke 6M vs S&P500": round(relative_strength_6m, 1),
            "Rel. Stärke 1J vs S&P500": round(relative_strength_1y, 1)
        }

    except Exception as e:
        print(f"Fehler bei {symbol}: {e}")
        return None

def scan_watchlist(symbols):
    benchmark = get_series(BENCHMARK)
    benchmark_close = benchmark["Close"]

    benchmark_price = get_last_value(benchmark_close)
    benchmark_perf_6m = (benchmark_price / get_last_value(benchmark_close.iloc[-126:])) * 100 - 100
    benchmark_perf_1y = (benchmark_price / get_last_value(benchmark_close.iloc[-252:])) * 100 - 100

    results = []

    for symbol in symbols:
        result = scan_stock(symbol, benchmark_perf_6m, benchmark_perf_1y)
        if result is not None:
            results.append(result)

    if len(results) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    return df.sort_values(by="Score", ascending=False)