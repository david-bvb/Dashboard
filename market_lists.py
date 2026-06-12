import pandas as pd
import requests
from io import StringIO

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def read_tables(url):
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    html = StringIO(response.text)
    return pd.read_html(html, flavor="html5lib")

def clean_symbols(symbols):
    cleaned = []

    for s in symbols:
        s = str(s).strip()
     

        if s and s.lower() != "nan":
            cleaned.append(s)

    return list(dict.fromkeys(cleaned))

def fallback_symbols():
    return [
        "AAPL", "MSFT", "NVDA", "AMD", "GOOGL", "AMZN", "META", "TSLA",
        "AVGO", "NFLX", "COST", "ADBE", "PEP", "CSCO", "INTC",
        "SAP.DE", "RHM.DE", "SIE.DE", "ALV.DE", "DTE.DE", "BAS.DE",
        "ASML.AS"
    ]

def get_sp500():
    try:
        tables = read_tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        df = tables[0]
        return clean_symbols(df["Symbol"].tolist())
    except Exception as e:
        print(f"S&P500 konnte nicht geladen werden: {e}")
        return []

def get_nasdaq100():
    try:
        tables = read_tables("https://en.wikipedia.org/wiki/Nasdaq-100")

        for df in tables:
            columns = [str(c) for c in df.columns]

            if "Ticker" in columns:
                return clean_symbols(df["Ticker"].tolist())

            if "Symbol" in columns:
                return clean_symbols(df["Symbol"].tolist())

        return []

    except Exception as e:
        print(f"Nasdaq100 konnte nicht geladen werden: {e}")
        return []

def get_dax():
    try:
        tables = read_tables("https://en.wikipedia.org/wiki/DAX")

        for df in tables:
            for col in df.columns:
                col_name = str(col)

                if "Ticker" in col_name or "Symbol" in col_name:
                    symbols = []

                    for s in df[col].tolist():
                        s = str(s).strip()

                        if s and s.lower() != "nan":
                            if not s.endswith(".DE"):
                                s = s + ".DE"
                            symbols.append(s)

                    return clean_symbols(symbols)

        return []

    except Exception as e:
        print(f"DAX konnte nicht geladen werden: {e}")
        return []

def get_all_symbols():
    symbols = []

    dax = get_dax()
    nasdaq = get_nasdaq100()
    sp500 = get_sp500()

    print(f"DAX geladen: {len(dax)}")
    print(f"Nasdaq100 geladen: {len(nasdaq)}")
    print(f"S&P500 geladen: {len(sp500)}")

    symbols.extend(dax)
    symbols.extend(nasdaq)
    symbols.extend(sp500)

    symbols = clean_symbols(symbols)

    if len(symbols) == 0:
        print("Nutze Fallback-Liste.")
        return fallback_symbols()

    return symbols