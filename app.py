import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

from scanner import scan_watchlist
from market_lists import (
    get_all_symbols,
    get_dax,
    get_nasdaq100,
    get_sp500
)

st.set_page_config(page_title="Davids Trend-Aktien Dashboard", layout="wide")

TOOLTIPS = {
    "Trend-Score": "Bewertet, wie stark der bestehende Aufwärtstrend einer Aktie ist. Grundlage sind u. a. SMA20, SMA50, SMA200, Nähe zum 52-Wochen-Hoch, relative Stärke, RSI und Volumen.",
    "Umkehr-Score": "Bewertet mögliche bullische Trendwenden auf Tages- und 4-Stunden-Basis. Grundlage sind RSI-Reversal, MACD-Reversal, Marktstruktur und relative Stärke.",
    "Umkehr-Phase": "Zeigt, ob sich eine mögliche Trendwende bereits konkretisiert oder nur beobachtet werden sollte.",
    "Handlungsstatus": "Leitet aus Trend-Score, Umkehr-Score, RSI und MACD einen praktischen Status ab: kaufnah prüfen, Watchlist, früh beobachten oder kein Signal.",
    "Trendstatus": "Bewertet den aktuellen Haupttrend der Aktie.",
    "Minervini-Trendcheck": "Prüft vereinfachte Mark-Minervini-Kriterien: Kurs über SMA150/SMA200, SMA150 über SMA200, steigender SMA200 und relative Stärke.",
    "Kaufzonen-Check": "Zeigt, ob die Aktie technisch in einer möglichen Einstiegszone liegt.",
    "RSI": "Relative Strength Index. Werte unter 30 gelten oft als überverkauft, Werte über 70 als überkauft. Spannend ist ein RSI, der aus tieferen Bereichen wieder steigt.",
    "MACD": "Moving Average Convergence Divergence. Zeigt Momentum-Veränderungen. Wichtig sind ein weniger negatives Histogramm, Annäherung an die Signallinie und bullische Crossovers.",
    "SMA": "Simple Moving Average. Ein einfacher gleitender Durchschnitt. SMA50 = Durchschnitt der letzten 50 Handelstage, SMA200 = Durchschnitt der letzten 200 Handelstage.",
    "PVSRA": "PVSRA bewertet Volumen zusammen mit Price Action. Der Scanner sucht nach auffälligem Volumen, großer Kerzenspanne, bullischem Schlusskurs im oberen Kerzenbereich und grüner Kerze. Dadurch wird geprüft, ob eine mögliche Trendwende durch Volumen bestätigt wird.",
    "Relative Stärke": "Vergleicht die Performance der Aktie mit dem S&P500. Positive Werte bedeuten, dass die Aktie den Markt schlägt."
}

st.sidebar.title("Einstellungen")

market = st.sidebar.selectbox(
    "Markt auswählen",
    ["Watchlist", "DAX", "Nasdaq100", "S&P500", "Alle"],
    help="Wähle das Aktienuniversum, das analysiert werden soll."
)

if market == "Alle":
    symbols = get_all_symbols()[:100]
elif market == "Watchlist":
    watchlist = pd.read_csv("watchlist.csv")
    symbols = watchlist["symbol"].tolist()
elif market == "DAX":
    symbols = get_dax()
elif market == "Nasdaq100":
    symbols = get_nasdaq100()
elif market == "S&P500":
    symbols = get_sp500()
else:
    symbols = []

st.title("📈 Davids Trend-Aktien Dashboard")

st.write(
    "Dieses Dashboard analysiert Aktien nach technischer Trendstärke, relativer Stärke "
    "und möglichen bullischen Trendwendesignalen. Der **Trend-Score** zeigt, wie stark "
    "der bestehende Aufwärtstrend ist. Der **Umkehr-Score** zeigt, ob RSI, MACD, "
    "4H-Chart und Tageschart auf eine mögliche neue Aufwärtsbewegung hindeuten."
)

st.sidebar.write(f"Geladene Symbole: {len(symbols)}")


@st.cache_data(ttl=86400)
def load_dashboard_data(symbols_tuple):
    return scan_watchlist(list(symbols_tuple))


if st.sidebar.button("🔄 Jetzt aktualisieren", help="Löscht den Cache und lädt aktuelle Kursdaten neu."):
    st.cache_data.clear()
    st.rerun()


with st.spinner("Lade aktuelle Marktdaten..."):
    df = load_dashboard_data(tuple(symbols))

if df.empty:
    st.warning("Keine Daten geladen. Bitte prüfe die Terminal-Fehlermeldung in VS Code.")
    st.stop()

st.sidebar.subheader("Filter")

min_score = st.sidebar.slider(
    "Minimaler Trend-Score",
    min_value=0,
    max_value=100,
    value=60,
    step=5,
    help=TOOLTIPS["Trend-Score"]
)

min_david = st.sidebar.slider(
    "Minimaler Umkehr-Score",
    min_value=0,
    max_value=100,
    value=0,
    step=5,
    help=TOOLTIPS["Umkehr-Score"]
)

only_minervini = st.sidebar.checkbox("Nur Minervini-Trendcheck ✅", help=TOOLTIPS["Minervini-Trendcheck"])
only_kaufzone = st.sidebar.checkbox("Nur Kaufzonen-Check ✅", help=TOOLTIPS["Kaufzonen-Check"])
only_top = st.sidebar.checkbox("Nur starke Trendaktien 🔥", help="Zeigt nur Aktien mit Trend-Score ab 80.")
only_david = st.sidebar.checkbox("Nur Trendwende-Setups 🟢/🟡", help=TOOLTIPS["Umkehr-Phase"])
only_entry_signal = st.sidebar.checkbox("Nur Handlungsstatus 🟢/🟡", help=TOOLTIPS["Handlungsstatus"])

only_score_and_david = st.sidebar.checkbox(
    "Trend-Score > 75 UND Umkehr-Score > 75",
    help="Strenger Kombinationsfilter für starke Trendaktien mit gleichzeitig starkem Trendwende-Setup."
)

search_text = st.sidebar.text_input(
    "Aktie suchen",
    "",
    help="Suche nach Symbol oder Unternehmensnamen."
)

filtered_df = df.copy()
filtered_df = filtered_df[filtered_df["Score"] >= min_score]
filtered_df = filtered_df[filtered_df["David-Trendwendenscanner"] >= min_david]

if only_minervini:
    filtered_df = filtered_df[filtered_df["Minervini"] == "✅ Ja"]

if only_kaufzone:
    filtered_df = filtered_df[filtered_df["Kaufzone"] == "✅ mögliche Kaufzone"]

if only_top:
    filtered_df = filtered_df[filtered_df["Score"] >= 80]

if only_david:
    filtered_df = filtered_df[
        filtered_df["David Ampel"].isin([
            "🟢 Kaufnahes Trendwende-Setup",
            "🟡 Frühe Trendwende"
        ])
    ]

if only_entry_signal:
    filtered_df = filtered_df[
        filtered_df["Einstiegssignal"].isin([
            "🟢 Kaufnah prüfen",
            "🟡 Auf Watchlist"
        ])
    ]

if only_score_and_david:
    filtered_df = filtered_df[
        (filtered_df["Score"] > 75) &
        (filtered_df["David-Trendwendenscanner"] > 75)
    ]

if search_text.strip():
    search = search_text.lower().strip()
    filtered_df = filtered_df[
        filtered_df["Symbol"].str.lower().str.contains(search, na=False) |
        filtered_df["Unternehmen"].str.lower().str.contains(search, na=False)
    ]

if filtered_df.empty:
    st.warning("Keine Aktien entsprechen den aktuellen Filtern.")
    st.stop()

top_count = len(filtered_df[filtered_df["Score"] >= 80])
watch_count = len(filtered_df[(filtered_df["Score"] >= 60) & (filtered_df["Score"] < 80)])
weak_count = len(filtered_df[filtered_df["Score"] < 60])

david_count = len(
    filtered_df[
        filtered_df["David Ampel"].isin([
            "🟢 Kaufnahes Trendwende-Setup",
            "🟡 Frühe Trendwende"
        ])
    ]
)

entry_count = len(
    filtered_df[
        filtered_df["Einstiegssignal"].isin([
            "🟢 Kaufnah prüfen",
            "🟡 Auf Watchlist"
        ])
    ]
)

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("🔥 Starke Trends", top_count, help=TOOLTIPS["Trend-Score"])
col2.metric("👀 Beobachten", watch_count, help="Aktien mit Trend-Score zwischen 60 und 79.")
col3.metric("❌ Schwach", weak_count, help="Aktien mit Trend-Score unter 60.")
col4.metric("🧭 Trendwenden", david_count, help=TOOLTIPS["Umkehr-Score"])
col5.metric("🎯 Handlungssignale", entry_count, help=TOOLTIPS["Handlungsstatus"])

st.subheader("🏆 Beste Trendaktien aktuell", help=TOOLTIPS["Trend-Score"])

st.caption(
    """
    **Trend-Score** = Stärke des bestehenden Aufwärtstrends.  
    **Umkehr-Score** = Hinweise auf eine mögliche neue bullische Trendwende.  
    **Umkehr-Phase** = technische Einordnung des Trendwendesignals.  
    **Handlungsstatus** = praktische Einordnung: prüfen, Watchlist, beobachten oder kein Signal.
    """
)

top20 = filtered_df.sort_values(by="Score", ascending=False).head(20)

ranking_columns = [
    "Symbol",
    "Unternehmen",
    "Score",
    "David-Trendwendenscanner",
    "David Ampel",
    "Einstiegssignal",
    "Ampel",
    "Minervini",
    "Kaufzone",
    "RSI",
    "Rel. Stärke 1J vs S&P500"
]

top20_anzeige = top20[ranking_columns].rename(
    columns={
        "Score": "Trend-Score",
        "David-Trendwendenscanner": "Umkehr-Score",
        "David Ampel": "Umkehr-Phase",
        "Einstiegssignal": "Handlungsstatus",
        "Ampel": "Trendstatus",
        "Minervini": "Minervini-Trendcheck",
        "Kaufzone": "Kaufzonen-Check",
        "Rel. Stärke 1J vs S&P500": "Relative Stärke 1J"
    }
)

st.dataframe(top20_anzeige, use_container_width=True)

st.subheader("🧭 Beste Trendwende-Setups", help=TOOLTIPS["Umkehr-Score"])

st.caption(
    """
    Diese Tabelle ist **separat nach Umkehr-Score sortiert**.  
    Sie verändert nicht das Haupt-Ranking nach Trend-Score.
    """
)

david_columns = [
    "Symbol",
    "Unternehmen",
    "Score",
    "David-Trendwendenscanner",
    "David Ampel",
    "Einstiegssignal",
    "David-Trendwende Ampel",
    "David RSI 1D Score",
    "David RSI 4H Score",
    "David MACD 1D Score",
    "David MACD 4H Score",
    "David Struktur 1D Score",
    "David Struktur 4H Score",
    "David PVSRA 1D Score",
    "David PVSRA 4H Score",
    "David PVSRA 1D Signal",
    "David PVSRA 4H Signal",
    "David Relative Stärke Score",
    "David RS 3M vs S&P500"
]

david_table = filtered_df.sort_values(
    by="David-Trendwendenscanner",
    ascending=False
).head(30)

david_anzeige = david_table[david_columns].rename(
    columns={
        "Score": "Trend-Score",
        "David-Trendwendenscanner": "Umkehr-Score",
        "David Ampel": "Umkehr-Phase",
        "Einstiegssignal": "Handlungsstatus",
        "David-Trendwende Ampel": "Umkehr-Einschätzung",
        "David RSI 1D Score": "RSI 1D",
        "David RSI 4H Score": "RSI 4H",
        "David MACD 1D Score": "MACD 1D",
        "David MACD 4H Score": "MACD 4H",
        "David Struktur 1D Score": "Struktur 1D",
        "David Struktur 4H Score": "Struktur 4H",
        "David Relative Stärke Score": "Relative Stärke Score",
        "David RS 3M vs S&P500": "Relative Stärke 3M"
    }
)

st.dataframe(david_anzeige, use_container_width=True)

st.subheader("📋 Gesamttabelle", help="Alle berechneten technischen Kennzahlen und Scores.")

gesamt_anzeige = filtered_df.rename(
    columns={
        "Score": "Trend-Score",
        "David-Trendwendenscanner": "Umkehr-Score",
        "David Ampel": "Umkehr-Phase",
        "Einstiegssignal": "Handlungsstatus",
        "Ampel": "Trendstatus",
        "Minervini": "Minervini-Trendcheck",
        "Kaufzone": "Kaufzonen-Check"
    }
)

st.dataframe(gesamt_anzeige, use_container_width=True)

st.subheader("📘 Erklärungen zu Scores & Indikatoren")

with st.expander("Erklärungen anzeigen"):
    for key, value in TOOLTIPS.items():
        st.markdown(f"**{key}:** {value}")

st.subheader("📊 Einzelanalyse")

selected_symbol = st.selectbox(
    "Aktie auswählen",
    filtered_df["Symbol"].tolist(),
    help="Wähle eine Aktie für Chart und Einzelanalyse."
)

chart_df = yf.download(
    selected_symbol,
    period="2y",
    interval="1d",
    progress=False,
    auto_adjust=True
)

if not chart_df.empty:
    if isinstance(chart_df.columns, pd.MultiIndex):
        chart_df.columns = chart_df.columns.get_level_values(0)

    chart_df["SMA50"] = chart_df["Close"].rolling(50).mean()
    chart_df["SMA200"] = chart_df["Close"].rolling(200).mean()

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["Close"], mode="lines", name="Kurs"))
    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["SMA50"], mode="lines", name="SMA50"))
    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["SMA200"], mode="lines", name="SMA200"))

    fig.update_layout(
        title=f"{selected_symbol} Kursverlauf mit SMA50 und SMA200",
        xaxis_title="Datum",
        yaxis_title="Kurs",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Kennzahlen zur ausgewählten Aktie")

    selected_df = filtered_df[filtered_df["Symbol"] == selected_symbol].rename(
        columns={
            "Score": "Trend-Score",
            "David-Trendwendenscanner": "Umkehr-Score",
            "David Ampel": "Umkehr-Phase",
            "Einstiegssignal": "Handlungsstatus",
            "Ampel": "Trendstatus",
            "Minervini": "Minervini-Trendcheck",
            "Kaufzone": "Kaufzonen-Check"
        }
    )

    st.dataframe(selected_df, use_container_width=True)

else:
    st.warning("Für diese Aktie konnten keine Chartdaten geladen werden.")