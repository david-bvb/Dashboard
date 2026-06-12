import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from scanner import scan_watchlist

st.set_page_config(page_title="Trend Dashboard 3.0", layout="wide")

st.title("📈 Trend Aktien Dashboard 3.0")
st.write("Trend-Score mit relativer Stärke, 52W-Hoch, ATH-Abstand, RSI und Kaufzonen.")

watchlist = pd.read_csv("watchlist.csv")
symbols = watchlist["symbol"].tolist()

with st.spinner("Lade aktuelle Marktdaten..."):
    df = scan_watchlist(symbols)

if df.empty:
    st.warning("Keine Daten geladen.")
    st.stop()

top_count = len(df[df["Score"] >= 80])
watch_count = len(df[(df["Score"] >= 60) & (df["Score"] < 80)])
weak_count = len(df[df["Score"] < 60])

col1, col2, col3 = st.columns(3)
col1.metric("🔥 Top-Kandidaten", top_count)
col2.metric("👀 Beobachten", watch_count)
col3.metric("❌ Kein Trend", weak_count)

st.subheader("Score-Übersicht")
st.dataframe(df, use_container_width=True)

st.subheader("🔥 Top-Kandidaten")
top = df[df["Score"] >= 80]

if len(top) > 0:
    st.dataframe(top, use_container_width=True)
else:
    st.info("Aktuell keine Aktie mit Score über 80 gefunden.")

st.subheader("📊 Einzelanalyse")

selected_symbol = st.selectbox(
    "Aktie auswählen",
    df["Symbol"].tolist()
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

    fig.add_trace(go.Scatter(
        x=chart_df.index,
        y=chart_df["Close"],
        mode="lines",
        name="Kurs"
    ))

    fig.add_trace(go.Scatter(
        x=chart_df.index,
        y=chart_df["SMA50"],
        mode="lines",
        name="SMA50"
    ))

    fig.add_trace(go.Scatter(
        x=chart_df.index,
        y=chart_df["SMA200"],
        mode="lines",
        name="SMA200"
    ))

    fig.update_layout(
        title=f"{selected_symbol} Kursverlauf mit SMA50 und SMA200",
        xaxis_title="Datum",
        yaxis_title="Kurs",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Kennzahlen zur ausgewählten Aktie")
    st.dataframe(
        df[df["Symbol"] == selected_symbol],
        use_container_width=True
    )