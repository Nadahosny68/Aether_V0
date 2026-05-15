import streamlit as st
import pandas as pd
import pyodbc
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── 1. PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AETHER Intelligence",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 2. CONSTANTS & HELPER FUNCTIONS ───────────────────────────────────────────
COLORS = {
    "Safe Air Day":                "#2ecc71",
    "Moderate Risk Day":           "#f1c40f",
    "High Respiratory Risk Day":   "#e67e22",
    "Mask Recommended Day":        "#e74c3c",
    "Avoid Outdoor Activity Day":  "#8e44ad",
}

def fmt(val):
    """Helper to format metrics safely across all pages."""
    try:
        return round(float(val), 1) if pd.notna(val) else "N/A"
    except:
        return "N/A"

# ── 3. CONNECTION LOGIC ───────────────────────────────────────────────────────
def get_secret(key):
    try: return st.secrets[key]
    except: return os.getenv(key)

@st.cache_resource
def get_conn():
    conn_str = (
        f"DRIVER={{{st.secrets['DRIVER']}}};"
        f"SERVER=tcp:{st.secrets['SERVER']},1433;"
        f"DATABASE={st.secrets['DATABASE']};"
        f"UID={st.secrets['USERNAME']};"
        f"PWD={st.secrets['PASSWORD']};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)

@st.cache_data(ttl=300)
def run_query(sql):
    with get_conn() as conn:
        return pd.read_sql(sql, conn)

# ── 4. SIDEBAR NAVIGATION ─────────────────────────────────────────────────────
st.sidebar.title("🌍 AETHER")
st.sidebar.caption("Environmental Health Intelligence — Cairo")

if st.sidebar.button("🔄 Force Refresh / Wake DB"):
    st.cache_data.clear()
    st.rerun()

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "🌿 Environmental Overview", "🫁 Health Intelligence", "🔮 Forecasts"]
)

# Get Date Bounds
date_info = run_query("SELECT MIN(date) as mn, MAX(date) as mx FROM Gold.EnvironmentalFeatures")
if not date_info.empty and pd.notna(date_info['mn'].iloc[0]):
    min_db = pd.to_datetime(date_info['mn'].iloc[0]).date()
    max_db = pd.to_datetime(date_info['mx'].iloc[0]).date()
else:
    st.warning("📡 Connecting to Azure... Dashboard will load shortly.")
    st.stop()

st.sidebar.divider()
date_range = st.sidebar.date_input("Date Range", value=(min_db, max_db), min_value=min_db, max_value=max_db)
start_date, end_date = date_range if (isinstance(date_range, (list, tuple)) and len(date_range) == 2) else (min_db, max_db)

# ── 5. DATA LOADING ───────────────────────────────────────────────────────────
df = run_query(f"SELECT * FROM Gold.EnvironmentalFeatures WHERE date BETWEEN '{start_date}' AND '{end_date}' ORDER BY date")

# ── 6. PAGES ──────────────────────────────────────────────────────────────────

# --- PAGE 1: HOME ---
if page == "🏠 Home":
    st.title("🌍 AETHER — Intelligence Hub")
    if not df.empty:
        latest = df.iloc[-1]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📅 Date", str(latest['date'].date() if hasattr(latest['date'], 'date') else latest['date']))
        c2.metric("💨 AQI", fmt(latest['aqi']))
        c3.metric("🌫️ PM2.5", fmt(latest['pm25']))
        c4.metric("🌡️ Temp", f"{fmt(latest['temperature'])}°C")
        c5.metric("🔥 Heat Index", fmt(latest['heat_index']))

        st.divider()
        cat = latest['health_category']
        color = COLORS.get(cat, "#95a5a6")
        st.markdown(f"<div style='background:{color};padding:25px;border-radius:15px;text-align:center;'><h2 style='color:white;margin:0;'>CURRENT STATUS: {cat}</h2></div>", unsafe_allow_html=True)
        
        st.subheader("AQI Trend (Selection)")
        st.plotly_chart(px.area(df.tail(30), x="date", y="aqi", color_discrete_sequence=["#3498db"]), use_container_width=True)

# --- PAGE 2: ENVIRONMENTAL OVERVIEW (All 5 Charts) ---
elif page == "🌿 Environmental Overview":
    st.title("🌿 Environmental Analysis")
    
    # Row 1: Air Quality
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("AQI Over Time")
        st.plotly_chart(px.line(df, x="date", y="aqi", color_discrete_sequence=["#e74c3c"]), use_container_width=True)
    with c2:
        st.subheader("PM2.5 Over Time")
        st.plotly_chart(px.line(df, x="date", y="pm25", color_discrete_sequence=["#e67e22"]), use_container_width=True)

    # Row 2: Climate & Categories
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Temperature vs Heat Index")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['date'], y=df['temperature'], name='Temp', line=dict(color='#f39c12')))
        fig.add_trace(go.Scatter(x=df['date'], y=df['heat_index'], name='Heat Index', line=dict(color='#e74c3c')))
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        st.subheader("Health Category Mix")
        cat_counts = df['health_category'].value_counts().reset_index()
        fig = px.pie(cat_counts, names='health_category', values='count', color='health_category', color_discrete_map=COLORS, hole=0.5)
        st.plotly_chart(fig, use_container_width=True)

    # Row 3: Monthly Aggregate
    st.subheader("Monthly Average AQI")
    df_m = df.copy()
    df_m['month'] = pd.to_datetime(df_m['date']).dt.to_period('M').astype(str)
    monthly = df_m.groupby('month')['aqi'].mean().reset_index()
    st.plotly_chart(px.bar(monthly, x='month', y='aqi', color_discrete_sequence=["#3498db"]), use_container_width=True)

# --- PAGE 3: HEALTH INTELLIGENCE ---
elif page == "🫁 Health Intelligence":
    st.title("🫁 Risk Intelligence")
    preds = run_query("SELECT TOP 30 date, health_category, aqi, pm25 FROM Gold.RiskPredictions ORDER BY date DESC")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        if not preds.empty:
            lp = preds.iloc[0]
            st.markdown(f"<div style='background:{COLORS.get(lp['health_category'], '#95a5a6')};padding:20px;border-radius:10px;text-align:center;color:white;'><h3>Latest Prediction</h3><p>{lp['health_category']}</p></div>", unsafe_allow_html=True)
            st.metric("Predicted AQI", fmt(lp['aqi']))
            st.metric("Predicted PM2.5", fmt(lp['pm25']))
    with c2:
        st.dataframe(preds, use_container_width=True)

    st.subheader("Respiratory Stress Analysis")
    st.plotly_chart(px.scatter(df, x="aqi", y="respiratory_stress", color="health_category", color_discrete_map=COLORS, opacity=0.7), use_container_width=True)

# --- PAGE 4: FORECASTS ---
elif page == "🔮 Forecasts":
    st.title("🔮 Predictive Forecasts")
    f_df = run_query("SELECT forecast_date, predicted_category, confidence FROM Gold.ForecastPredictions ORDER BY forecast_date DESC")
    
    if not f_df.empty:
        st.subheader("7-Day Outlook")
        upcoming = f_df.head(7)
        cols = st.columns(7)
        for i, (_, row) in enumerate(upcoming.iterrows()):
            with cols[i]:
                color = COLORS.get(row['predicted_category'], "#95a5a6")
                st.markdown(f"<div style='background:{color};padding:10px;border-radius:10px;text-align:center;color:white;min-height:100px;'><small>{row['forecast_date'].strftime('%a %d')}</small><br><b>{row['predicted_category']}</b></div>", unsafe_allow_html=True)
        st.divider()
        st.subheader("Detailed Forecast Log")
        st.dataframe(f_df, use_container_width=True)

# ── 7. FOOTER ─────────────────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.caption("AETHER v1.2 | Cairo, Egypt")
st.sidebar.caption("Built by Nada Hosny")
