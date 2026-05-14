
# streamlit run Dashboard/streamlit/streamlit_app.py


import streamlit as st
import pandas as pd
import pyodbc
import os
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AETHER",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Connection — reads from Streamlit secrets ─────────────────────────────────
@st.cache_resource
def get_conn():
    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server=tcp:{st.secrets['AZURE_SQL_SERVER']},1433;"
        f"Database={st.secrets['AZURE_SQL_DATABASE']};"
        f"Uid={st.secrets['AZURE_SQL_USER']};"
        f"Pwd={st.secrets['AZURE_SQL_PASSWORD']};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)

@st.cache_data(ttl=300)
def query(sql):
    return pd.read_sql(sql, get_conn())

# ── Health category colors ────────────────────────────────────────────────────
COLORS = {
    "Safe Air Day":               "#2ecc71",
    "Moderate Risk Day":          "#f1c40f",
    "High Respiratory Risk Day":  "#e67e22",
    "Mask Recommended Day":       "#e74c3c",
    "Avoid Outdoor Activity Day": "#8e44ad",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.title("AETHER")
st.sidebar.caption("Environmental Health Intelligence")

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "🌿 Environmental Overview", "🫁 Health Intelligence", "🔮 Forecasts"]
)

st.sidebar.divider()

# Date filter
dates = query("SELECT MIN(date) as mn, MAX(date) as mx FROM Gold.EnvironmentalFeatures")
min_date = pd.to_datetime(dates['mn'].values[0])
max_date = pd.to_datetime(dates['mx'].values[0])

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) == 2:
    start, end = date_range
else:
    start, end = min_date, max_date

# ── Filtered data ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_env(start, end):
    return query(f"""
        SELECT * FROM Gold.EnvironmentalFeatures
        WHERE date BETWEEN '{start}' AND '{end}'
        ORDER BY date
    """)

df = get_env(str(start), str(end))

# ════════════════════════════════════════════════════════════════════════════════
# PAGE 1 — HOME
# ════════════════════════════════════════════════════════════════════════════════
if page == "🏠 Home":
    st.title("🌍 AETHER — Environmental Health Intelligence")
    st.caption("Air Quality & Respiratory Risk Platform — Cairo, Egypt")
    st.divider()

    latest = df.iloc[-1] if not df.empty else None

    if latest is not None:
        # ── KPI row ───────────────────────────────────────────────────────────
        c1, c2, c3, c4, c5 = st.columns(5)

        aqi_val   = round(float(latest['aqi']),   1) if pd.notna(latest['aqi'])   else "N/A"
        pm25_val  = round(float(latest['pm25']),  1) if pd.notna(latest['pm25'])  else "N/A"
        temp_val  = round(float(latest['temperature']), 1) if pd.notna(latest['temperature']) else "N/A"
        hi_val    = round(float(latest['heat_index']),  1) if pd.notna(latest['heat_index'])  else "N/A"
        cat       = latest['health_category'] if pd.notna(latest['health_category']) else "Unknown"

        c1.metric("📅 Latest Date",      str(latest['date']))
        c2.metric("💨 AQI",              aqi_val)
        c3.metric("🌫️ PM2.5",           pm25_val)
        c4.metric("🌡️ Temperature (°C)", temp_val)
        c5.metric("🔥 Heat Index",       hi_val)

        st.divider()

        # ── Health category banner ────────────────────────────────────────────
        color = COLORS.get(cat, "#95a5a6")
        st.markdown(f"""
            <div style="background:{color};padding:20px;border-radius:12px;text-align:center;">
                <h2 style="color:white;margin:0;">Current Status: {cat}</h2>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ── Recommendations ───────────────────────────────────────────────────
        recommendations = {
            "Safe Air Day":               "✅ Air quality is good. Safe for all outdoor activities.",
            "Moderate Risk Day":          "⚠️ Acceptable air quality. Sensitive groups should limit prolonged exertion.",
            "High Respiratory Risk Day":  "🟠 Elevated risk. People with respiratory conditions should stay indoors.",
            "Mask Recommended Day":       "😷 Wear a mask outdoors. Minimize outdoor exposure.",
            "Avoid Outdoor Activity Day": "🚫 Hazardous conditions. Stay indoors with windows closed.",
        }
        st.info(recommendations.get(cat, "Monitor conditions closely."))

        # ── Mini trend chart ──────────────────────────────────────────────────
        st.subheader("AQI Trend — Last 30 Days")
        last30 = df.tail(30)
        fig = px.line(last30, x="date", y="aqi", color_discrete_sequence=["#3498db"])
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=250)
        st.plotly_chart(fig, use_container_width=True)
        
        

# ════════════════════════════════════════════════════════════════════════════════
# PAGE 2 — ENVIRONMENTAL OVERVIEW
# ════════════════════════════════════════════════════════════════════════════════
elif page == "🌿 Environmental Overview":
    st.title("🌿 Environmental Overview")
    st.divider()

    c1, c2 = st.columns(2)

    # AQI trend
    with c1:
        st.subheader("AQI Over Time")
        fig = px.line(df, x="date", y="aqi", color_discrete_sequence=["#e74c3c"])
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

    # PM2.5 trend
    with c2:
        st.subheader("PM2.5 Over Time")
        fig = px.line(df, x="date", y="pm25", color_discrete_sequence=["#e67e22"])
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    # Temperature & Heat Index
    with c3:
        st.subheader("Temperature vs Heat Index")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['date'], y=df['temperature'], name='Temperature', line=dict(color='#f39c12')))
        fig.add_trace(go.Scatter(x=df['date'], y=df['heat_index'],  name='Heat Index',  line=dict(color='#e74c3c')))
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

    # Health category donut
    with c4:
        st.subheader("Health Category Distribution")
        cat_counts = df['health_category'].value_counts().reset_index()
        cat_counts.columns = ['category', 'count']
        fig = px.pie(
            cat_counts, names='category', values='count',
            color='category',
            color_discrete_map=COLORS,
            hole=0.4
        )
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

    # Monthly AQI
    st.subheader("Monthly Average AQI")
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M').astype(str)
    monthly = df.groupby('month')['aqi'].mean().reset_index()
    fig = px.bar(monthly, x='month', y='aqi', color_discrete_sequence=["#3498db"])
    fig.update_layout(height=300, margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# PAGE 3 — HEALTH INTELLIGENCE
# ════════════════════════════════════════════════════════════════════════════════
elif page == "🫁 Health Intelligence":
    st.title("🫁 Health Intelligence")
    st.divider()

    # Risk predictions
    preds = query(f"""
        SELECT TOP 30 p.date, p.health_category, p.aqi, p.pm25, p.predicted_at
        FROM Gold.RiskPredictions p
        ORDER BY p.date DESC
    """)

    c1, c2 = st.columns([1, 2])

    with c1:
        st.subheader("Latest Prediction")
        if not preds.empty:
            latest_pred = preds.iloc[0]
            cat = latest_pred['health_category']
            color = COLORS.get(cat, "#95a5a6")
            st.markdown(f"""
                <div style="background:{color};padding:15px;border-radius:10px;text-align:center;">
                    <h3 style="color:white;margin:0;">{cat}</h3>
                </div>
            """, unsafe_allow_html=True)
            st.metric("AQI",   round(float(latest_pred['aqi']),  1) if pd.notna(latest_pred['aqi'])  else "N/A")
            st.metric("PM2.5", round(float(latest_pred['pm25']), 1) if pd.notna(latest_pred['pm25']) else "N/A")

    with c2:
        st.subheader("Prediction History")
        st.dataframe(preds, use_container_width=True, height=300)

    # Respiratory stress scatter
    st.subheader("Respiratory Stress vs AQI")
    fig = px.scatter(
        df, x="aqi", y="respiratory_stress",
        color="health_category",
        color_discrete_map=COLORS,
        opacity=0.6
    )
    fig.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# PAGE 4 — FORECASTS
# ════════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Forecasts":
    st.title("🔮 Environmental Forecasts")
    st.divider()

    forecasts = query("""
        SELECT forecast_date, forecast_horizon, predicted_category, confidence, model_version
        FROM Gold.ForecastPredictions
        ORDER BY forecast_date DESC
    """)

    if forecasts.empty:
        st.warning("No forecast data available yet.")
    else:
        # Forecast cards
        st.subheader("Upcoming Forecast")
        upcoming = forecasts.head(7)

        cols = st.columns(min(len(upcoming), 7))
        for i, (_, row) in enumerate(upcoming.iterrows()):
            with cols[i % 7]:
                cat   = row['predicted_category']
                color = COLORS.get(cat, "#95a5a6")
                conf  = round(float(row['confidence']) * 100, 1) if pd.notna(row['confidence']) else "N/A"
                st.markdown(f"""
                    <div style="background:{color};padding:10px;border-radius:8px;text-align:center;margin-bottom:8px;">
                        <small style="color:white;">{row['forecast_date']}</small>
                        <p style="color:white;font-weight:bold;margin:4px 0;font-size:12px;">{cat}</p>
                        <small style="color:white;">Conf: {conf}%</small>
                    </div>
                """, unsafe_allow_html=True)

        st.divider()

        # Confidence over time
        st.subheader("Forecast Confidence Over Time")
        fig = px.bar(
            forecasts, x="forecast_date", y="confidence",
            color="predicted_category",
            color_discrete_map=COLORS
        )
        fig.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Full Forecast Table")
        st.dataframe(forecasts, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.caption("AETHER v1.0 | Cairo, Egypt")
st.sidebar.caption("Built by Nada Hosny | Marketing Data Analyst")