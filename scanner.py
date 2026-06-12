import yfinance as yf
import pandas as pd
from david_index import calculate_david_index

BENCHMARK = "^GSPC"


def get_company_name(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return info.get("shortName") or info.get("longName") or symbol
    except Exception:
        return symbol


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


def get_series(symbol, period="2y", interval="1d"):
    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True
    )

    if df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df


def scan_stock(symbol, benchmark_perf_6m, benchmark_perf_1y, benchmark_perf_3m):
    try:
        df = get_series(symbol, period="2y", interval="1d")

        if df is None or len(df) < 260:
            return None

        h4_df = get_series(symbol, period="6mo", interval="4h")

        company_name = get_company_name(symbol)

        close = df["Close"]
        volume = df["Volume"]

        price = get_last_value(close)
        sma20 = get_last_value(close.rolling(20).mean())
        sma50 = get_last_value(close.rolling(50).mean())
        sma150 = get_last_value(close.rolling(150).mean())
        sma200 = get_last_value(close.rolling(200).mean())
        sma200_20_days_ago = get_last_value(close.rolling(200).mean().iloc[[-20]])

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

        minervini = (
            price > sma150
            and price > sma200
            and sma150 > sma200
            and sma200 > sma200_20_days_ago
            and distance_ath > -25
            and relative_strength_1y > 0
        )

        minervini_check = "✅ Ja" if minervini else "❌ Nein"
        ampel = "🟢 Stark" if score >= 80 else "🟡 Beobachten" if score >= 60 else "🔴 Schwach"

        david_data = calculate_david_index(df, h4_df, benchmark_perf_3m)
        david_score = david_data["David-Trendwendenscanner"]

        rsi_reversal_points = (
            david_data["David RSI 1D Score"] +
            david_data["David RSI 4H Score"]
        )

        macd_reversal_points = (
            david_data["David MACD 1D Score"] +
            david_data["David MACD 4H Score"]
        )

        if david_score >= 65 and score >= 60:
            david_ampel = "🟢 Kaufnahes Trendwende-Setup"
        elif david_score >= 50:
            david_ampel = "🟡 Frühe Trendwende"
        elif david_score >= 35:
            david_ampel = "👀 Beobachten"
        else:
            david_ampel = "🔴 Keine Trendwende"

        if (
            david_score >= 65
            and score >= 60
            and rsi_reversal_points >= 15
            and macd_reversal_points >= 10
        ):
            einstiegssignal = "🟢 Kaufnah prüfen"

        elif (
            david_score >= 50
            and rsi_reversal_points >= 10
            and macd_reversal_points >= 8
        ):
            einstiegssignal = "🟡 Auf Watchlist"

        elif (
            david_score >= 35
            and (rsi_reversal_points >= 10 or macd_reversal_points >= 10)
        ):
            einstiegssignal = "👀 Früh beobachten"

        else:
            einstiegssignal = "🔴 Kein Einstiegssignal"

        return {
            "Symbol": symbol,
            "Unternehmen": company_name,
            "Kurs": round(price, 2),
            "Score": score,
            "Signal": signal,
            "Ampel": ampel,
            "Minervini": minervini_check,
            "Trend": trend,
            "Kaufzone": kaufzone,
            "RSI": round(rsi, 1),
            "SMA20": round(sma20, 2),
            "SMA50": round(sma50, 2),
            "SMA150": round(sma150, 2),
            "SMA200": round(sma200, 2),
            "Abstand 52W Hoch %": round(distance_52w, 1),
            "Abstand ATH %": round(distance_ath, 1),
            "Perf. 6M %": round(perf_6m, 1),
            "Perf. 1J %": round(perf_1y, 1),
            "Rel. Stärke 6M vs S&P500": round(relative_strength_6m, 1),
            "Rel. Stärke 1J vs S&P500": round(relative_strength_1y, 1),

            "David-Trendwendenscanner": david_score,
            "David Ampel": david_ampel,
            "Einstiegssignal": einstiegssignal,
            "David-Trendwende Ampel": david_data["David-Trendwende Ampel"],
            "David RSI 1D Score": david_data["David RSI 1D Score"],
            "David RSI 4H Score": david_data["David RSI 4H Score"],
            "David MACD 1D Score": david_data["David MACD 1D Score"],
            "David MACD 4H Score": david_data["David MACD 4H Score"],
            "David Struktur 1D Score": david_data["David Struktur 1D Score"],
            "David Struktur 4H Score": david_data["David Struktur 4H Score"],
            "David PVSRA 1D Score": david_data["David PVSRA 1D Score"],
            "David PVSRA 4H Score": david_data["David PVSRA 4H Score"],
            "David PVSRA 1D Signal": david_data["David PVSRA 1D Signal"],
            "David PVSRA 4H Signal": david_data["David PVSRA 4H Signal"],
            "David Relative Stärke Score": david_data["David Relative Stärke Score"],
            "David RS 3M vs S&P500": david_data["David RS 3M vs S&P500"]
        }

    except Exception as e:
        print(f"Fehler bei {symbol}: {e}")
        return None


def scan_watchlist(symbols):
    benchmark = get_series(BENCHMARK)

    if benchmark is None or len(benchmark) < 260:
        print("Benchmark konnte nicht geladen werden.")
        return pd.DataFrame()

    benchmark_close = benchmark["Close"]
    benchmark_price = get_last_value(benchmark_close)

    benchmark_perf_3m = (benchmark_price / get_last_value(benchmark_close.iloc[[-63]])) * 100 - 100
    benchmark_perf_6m = (benchmark_price / get_last_value(benchmark_close.iloc[[-126]])) * 100 - 100
    benchmark_perf_1y = (benchmark_price / get_last_value(benchmark_close.iloc[[-252]])) * 100 - 100

    results = []

    for symbol in symbols:
        result = scan_stock(
            symbol,
            benchmark_perf_6m,
            benchmark_perf_1y,
            benchmark_perf_3m
        )

        if result is not None:
            results.append(result)

    if len(results) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    return df.sort_values(by="Score", ascending=False)