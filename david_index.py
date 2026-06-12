import pandas as pd
import numpy as np


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def calculate_macd(close):
    ema12 = ema(close, 12)
    ema26 = ema(close, 26)
    macd_line = ema12 - ema26
    signal_line = ema(macd_line, 9)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def rsi_turnaround_score(close, max_points):
    close = close.dropna()
    rsi = calculate_rsi(close).dropna()

    if len(close) < 80 or len(rsi) < 20:
        return 0

    score = 0
    rsi_now = rsi.iloc[-1]

    if rsi_now < 35:
        score += max_points * 0.25
    if rsi_now < 30:
        score += max_points * 0.25
    if rsi_now > rsi.iloc[-3]:
        score += max_points * 0.20
    if rsi_now > rsi.iloc[-5]:
        score += max_points * 0.15

    price_recent_low = close.iloc[-20:].min()
    price_previous_low = close.iloc[-60:-20].min()
    rsi_recent_low = rsi.iloc[-20:].min()
    rsi_previous_low = rsi.iloc[-60:-20].min()

    if price_recent_low < price_previous_low and rsi_recent_low > rsi_previous_low:
        score += max_points * 0.15

    return round(min(score, max_points), 1)


def macd_turnaround_score(close, max_points):
    close = close.dropna()
    macd_line, signal_line, histogram = calculate_macd(close)
    histogram = histogram.dropna()

    if len(histogram) < 20:
        return 0

    score = 0

    if histogram.iloc[-1] > histogram.iloc[-3]:
        score += max_points * 0.30
    if histogram.iloc[-1] > histogram.iloc[-5]:
        score += max_points * 0.25

    macd_distance_now = abs(macd_line.iloc[-1] - signal_line.iloc[-1])
    macd_distance_old = abs(macd_line.iloc[-5] - signal_line.iloc[-5])

    if macd_distance_now < macd_distance_old:
        score += max_points * 0.20

    if macd_line.iloc[-2] < signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]:
        score += max_points * 0.25

    return round(min(score, max_points), 1)


def structure_turnaround_score(close, max_points):
    close = close.dropna()

    if len(close) < 80:
        return 0

    score = 0

    recent_low = close.iloc[-20:].min()
    previous_low = close.iloc[-60:-20].min()
    previous_high = close.iloc[-60:-20].max()
    current_price = close.iloc[-1]

    if recent_low > previous_low:
        score += max_points * 0.35

    if abs(recent_low / previous_low - 1) <= 0.05:
        score += max_points * 0.25

    if current_price > previous_high:
        score += max_points * 0.40

    return round(min(score, max_points), 1)


def pvsra_volume_score(df, max_points):
    """
    PVSRA-Näherung:
    Bewertet, ob auffälliges Volumen zusammen mit bullischer Price Action auftritt.
    Vector Candle Logik:
    - Volumen deutlich über Volumen-MA
    - große Kerze / große Spanne
    - Schlusskurs im oberen Kerzenbereich
    - grüne Kerze
    """

    required_cols = {"Open", "High", "Low", "Close", "Volume"}

    if df is None or df.empty or not required_cols.issubset(df.columns):
        return 0, "Keine PVSRA-Daten"

    data = df.dropna().copy()

    if len(data) < 50:
        return 0, "Zu wenig PVSRA-Daten"

    data["Volume_MA"] = data["Volume"].rolling(20).mean()
    data["Range"] = data["High"] - data["Low"]
    data["Range_MA"] = data["Range"].rolling(20).mean()

    last = data.iloc[-1]

    if last["Volume_MA"] == 0 or pd.isna(last["Volume_MA"]):
        return 0, "Keine Volumenbasis"

    volume_ratio = last["Volume"] / last["Volume_MA"]
    range_ratio = last["Range"] / last["Range_MA"] if last["Range_MA"] > 0 else 0

    close_position = (
        (last["Close"] - last["Low"]) / (last["High"] - last["Low"])
        if last["High"] != last["Low"]
        else 0.5
    )

    bullish_candle = last["Close"] > last["Open"]
    high_volume = volume_ratio >= 1.5
    very_high_volume = volume_ratio >= 2.0
    wide_range = range_ratio >= 1.2
    bullish_close = close_position >= 0.65

    score = 0

    if high_volume:
        score += max_points * 0.30

    if very_high_volume:
        score += max_points * 0.20

    if wide_range:
        score += max_points * 0.20

    if bullish_close:
        score += max_points * 0.15

    if bullish_candle:
        score += max_points * 0.15

    if very_high_volume and bullish_candle and bullish_close:
        signal = "🟢 Bullische PVSRA-Vector-Candle"
    elif high_volume and bullish_close:
        signal = "🟡 PVSRA Volumenbestätigung"
    elif high_volume and not bullish_candle:
        signal = "🟠 Hohes Volumen, aber noch kein bullischer Schluss"
    else:
        signal = "🔴 Keine PVSRA-Bestätigung"

    return round(min(score, max_points), 1), signal


def relative_strength_score(close, benchmark_perf_3m, max_points):
    close = close.dropna()

    if len(close) < 70:
        return 0, 0

    price = close.iloc[-1]
    perf_3m = (price / close.iloc[-63] - 1) * 100
    relative_strength = perf_3m - benchmark_perf_3m

    if relative_strength > 10:
        score = max_points
    elif relative_strength > 0:
        score = max_points * 0.6
    else:
        score = 0

    return round(score, 1), round(relative_strength, 1)


def calculate_david_index(daily_df, h4_df, benchmark_perf_3m):
    daily_close = daily_df["Close"].dropna()

    if h4_df is not None and not h4_df.empty and "Close" in h4_df.columns:
        h4_close = h4_df["Close"].dropna()
    else:
        h4_close = pd.Series(dtype=float)

    if len(daily_close) < 260:
        return empty_david_index()

    rsi_1d = rsi_turnaround_score(daily_close, 20)
    rsi_4h = rsi_turnaround_score(h4_close, 12) if len(h4_close) >= 100 else 0

    macd_1d = macd_turnaround_score(daily_close, 18)
    macd_4h = macd_turnaround_score(h4_close, 12) if len(h4_close) >= 100 else 0

    structure_1d = structure_turnaround_score(daily_close, 10)
    structure_4h = structure_turnaround_score(h4_close, 5) if len(h4_close) >= 100 else 0

    pvsra_1d, pvsra_signal_1d = pvsra_volume_score(daily_df, 13)
    pvsra_4h, pvsra_signal_4h = pvsra_volume_score(h4_df, 7) if h4_df is not None else (0, "Keine PVSRA-Daten")

    relative_score, relative_strength_3m = relative_strength_score(
        daily_close,
        benchmark_perf_3m,
        3
    )

    scanner_score = (
        rsi_1d
        + rsi_4h
        + macd_1d
        + macd_4h
        + structure_1d
        + structure_4h
        + pvsra_1d
        + pvsra_4h
        + relative_score
    )

    scanner_score = round(min(scanner_score, 100), 1)

    if scanner_score < 30:
        interpretation = "🔴 Keine Trendwende"
    elif scanner_score < 50:
        interpretation = "🟡 Erste Beobachtung"
    elif scanner_score < 70:
        interpretation = "🟠 Mögliche Trendwende"
    elif scanner_score < 85:
        interpretation = "🟢 Starkes Trendwende-Setup"
    else:
        interpretation = "🔥 Top-Trendwende-Kandidat"

    return {
        "David-Trendwendenscanner": scanner_score,
        "David-Trendwende Ampel": interpretation,
        "David RSI 1D Score": rsi_1d,
        "David RSI 4H Score": rsi_4h,
        "David MACD 1D Score": macd_1d,
        "David MACD 4H Score": macd_4h,
        "David Struktur 1D Score": structure_1d,
        "David Struktur 4H Score": structure_4h,
        "David PVSRA 1D Score": pvsra_1d,
        "David PVSRA 4H Score": pvsra_4h,
        "David PVSRA 1D Signal": pvsra_signal_1d,
        "David PVSRA 4H Signal": pvsra_signal_4h,
        "David Relative Stärke Score": relative_score,
        "David RS 3M vs S&P500": relative_strength_3m
    }


def empty_david_index():
    return {
        "David-Trendwendenscanner": 0,
        "David-Trendwende Ampel": "🔴 Keine Trendwende",
        "David RSI 1D Score": 0,
        "David RSI 4H Score": 0,
        "David MACD 1D Score": 0,
        "David MACD 4H Score": 0,
        "David Struktur 1D Score": 0,
        "David Struktur 4H Score": 0,
        "David PVSRA 1D Score": 0,
        "David PVSRA 4H Score": 0,
        "David PVSRA 1D Signal": "Keine PVSRA-Daten",
        "David PVSRA 4H Signal": "Keine PVSRA-Daten",
        "David Relative Stärke Score": 0,
        "David RS 3M vs S&P500": 0
    }