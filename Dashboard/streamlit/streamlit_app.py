import streamlit as st
import pandas as pd
import pyodbc
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── 1. PAGE CONFIG & STYLING ──────────────────────────────────────────────────
st.set_page_config(
    page_title="AETHER",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

COLORS = {
    "Safe Air Day":                "#2ecc71",
    "Moderate Risk Day":           "#f1c40f",
    "High Respiratory Risk Day":   "#e67e22",
    "Mask Recommended Day":        "#e74c3c",
    "Avoid Outdoor Activity Day":  "#8e44ad",
}

# ── 2. ROBUST CONNECTION LOGIC ────────────────────────────────────────────────
def get_secret(key):
    try: return st.secrets[key]
    except: return os.getenv(key)

@st.cache_resource
def get_conn():
    """High timeout connection to handle Azure Serverless 'Wake-up' time."""
    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server=tcp:{get_secret('AZURE_SQL_SERVER')},1433;"
        f"Database={get_secret('AZURE_SQL_DATABASE')};"
        f"Uid={get_secret('AZURE_SQL_USER')};"
        f"Pwd={get_secret('AZURE_SQL_PASSWORD')};"
        "Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=120;"
    )
    return pyodbc.connect(conn_str)

@st.cache_data(ttl=300)
def run_query(sql):
    with get_conn() as conn:
        return pd.read_sql(sql, conn)

# ── 3. SIDEBAR & NAVIGATION ───────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.title("AETHER")
st.sidebar.caption("Environmental Health Intelligence")

if st.sidebar.button("🔄 Force Refresh / Wake DB"):
    st.cache_data.clear()
    st.rerun()

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "🌿 Environmental Overview", "🫁 Health Intelligence", "🔮 Forecasts"]
)

# ── 4. DB AVAILABILITY & DATE FILTER ─────────────────────────────────────────
def get_date_bounds():
    try:
        df_dates = run_query("SELECT MIN(date) as mn, MAX(date) as mx FROM Gold.EnvironmentalFeatures")
        if df_dates.empty or pd.isna(df_dates['mn'].values[0]):
            return None, None
        return pd.to_datetime(df_dates['mn'].values[0]).date(), pd.to_datetime(df_dates['mx'].values[0]).date()
    except Exception:
        return None, None

min_db, max_db = get_date_bounds()

if min_db is None:
    st.error("📡 Database is waking up or empty. Please wait 30 seconds and click 'Force Refresh'.")
    st.stop()

date_range = st.sidebar.date_input("Select Range", value=(min_db, max_db), min_value=min_db, max_value=max_db)
start, end = date_range if (isinstance(date_range, (list, tuple)) and len(date_range) == 2) else (min_db, max_db)

# ── 5. DASHBOARD PAGES ────────────────────────────────────────────────────────

# Common Data Load
df = run_query(f"SELECT * FROM Gold.EnvironmentalFeatures WHERE date BETWEEN '{start}' AND '{end}' ORDER BY date")

# --- PAGE: HOME ---
if page == "🏠 Home":
    st.title("🌍 AETHER — Environmental Health Intelligence")
    st.caption("Air Quality & Respiratory Risk Platform — Cairo, Egypt")
    st.divider()

    if not df.empty:
        latest = df.iloc[-1]
        c1, c2, c3, c4, c5 = st.columns(5)
        
        c1.metric("📅 Date", str(latest['date'].date() if hasattr(latest['date'], 'date') else latest['date']))
        c2.metric("💨 AQI", round(float(latest['aqi']), 1))
        c3.metric("🌫️ PM2.5", round(float(latest['pm25']), 1))
        c4.metric("🌡️ Temp (°C)", round(float(latest['temperature']), 1))
        c5.metric("🔥 Heat Index", round(float(latest['heat_index']), 1))

        cat = latest['health_category']
        color = COLORS.get(cat, "#95a5a6")
        st.markdown(f"<div style='background:{color};padding:20px;border-radius:12px;text-align:center;'><h2 style='color:white;margin:0;'>Current Status: {cat}</h2></div>", unsafe_allow_html=True)

        recs = {
            "Safe Air Day": "✅ Air quality is good. Safe for all outdoor activities.",
            "Moderate Risk Day": "⚠️ Acceptable air quality. Sensitive groups should limit exertion.",
            "High Respiratory Risk Day": "🟠 Elevated risk. People with respiratory conditions should stay indoors.",
            "Mask Recommended Day": "😷 Wear a mask outdoors. Minimize exposure.",
            "Avoid Outdoor Activity Day": "🚫 Hazardous conditions. Stay indoors.",
        }
        st.info(recs.get(cat, "Monitor conditions closely."))

        st.subheader("AQI Trend — Last 30 Days")
        fig = px.line(df.tail(30), x="date", y="aqi", color_discrete_sequence=["#3498db"])
        st.plotly_chart(fig, use_container_width=True)

# --- PAGE: ENVIRONMENTAL OVERVIEW ---
elif page == "🌿 Environmental Overview":
    st.title("🌿 Environmental Overview")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("AQI Over Time")
        st.plotly_chart(px.line(df, x="date", y="aqi", color_discrete_sequence=["#e74c3c"]), use_container_width=True)
    with c2:
        st.subheader("PM2.5 Over Time")
        st.plotly_chart(px.line(df, x="date", y="pm25", color_discrete_sequence=["#e67e22"]), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Temperature vs Heat Index")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['date'], y=df['temperature'], name='Temp', line=dict(color='#f39c12')))
        fig.add_trace(go.Scatter(x=df['date'], y=df['heat_index'], name='Heat Index', line=dict(color='#e74c3c')))
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        st.subheader("Health Category Distribution")
        cat_counts = df['health_category'].value_counts().reset_index()
        fig = px.pie(cat_counts, names='health_category', values='count', color='health_category', color_discrete_map=COLORS, hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

# --- PAGE: HEALTH INTELLIGENCE ---
elif page == "🫁 Health Intelligence":
    st.title("🫁 Health Intelligence")
    preds = run_query("SELECT TOP 30 date, health_category, aqi, pm25 FROM Gold.RiskPredictions ORDER BY date DESC")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if not preds.empty:
            l_p = preds.iloc[0]
            st.markdown(f"<div style='background:{COLORS.get(l_p['health_category'], '#95a5a6')};padding:15px;border-radius:10px;text-align:center;'><h3 style='color:white;margin:0;'>{l_p['health_category']}</h3></div>", unsafe_allow_html=True)
            st.metric("Predicted AQI", round(l_p['aqi'], 1))
    with col2:
        st.dataframe(preds, use_container_width=True)

    st.subheader("Respiratory Stress vs AQI")
    st.plotly_chart(px.scatter(df, x="aqi", y="respiratory_stress", color="health_category", color_discrete_map=COLORS), use_container_width=True)

# --- PAGE: FORECASTS ---
elif page == "🔮 Forecasts":
    st.title("🔮 Environmental Forecasts")
    f_df = run_query("SELECT forecast_date, predicted_category, confidence FROM Gold.ForecastPredictions ORDER BY forecast_date DESC")
    
    if not f_df.empty:
        st.subheader("Upcoming Forecast")
        upcoming = f_df.head(7)
        cols = st.columns(len(upcoming))
        for i, (_, row) in enumerate(upcoming.iterrows()):
            with cols[i]:
                color = COLORS.get(row['predicted_category'], "#95a5a6")
                st.markdown(f"<div style='background:{color};padding:10px;border-radius:8px;text-align:center;color:white;'><small>{row['forecast_date'].date()}</small><br><b>{row['predicted_category']}</b></div>", unsafe_allow_html=True)
        st.divider()
        st.dataframe(f_df, use_container_width=True)
    else:
        st.warning("No forecast data available.")

# ── 6. FOOTER ─────────────────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.caption("AETHER v1.2 | Cairo, Egypt")
st.sidebar.caption("Built by Nada Hosny")