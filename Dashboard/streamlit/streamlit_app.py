import streamlit as st
import pandas as pd
import pyodbc
import os
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
# 1. PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AETHER Intelligence",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════════════════
# 2. CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
COLORS = {
    "Safe Air Day":               "#2ecc71",
    "Moderate Risk Day":          "#f1c40f",
    "High Respiratory Risk Day":  "#e67e22",
    "Mask Recommended Day":       "#e74c3c",
    "Avoid Outdoor Activity Day": "#8e44ad",
}

RECOMMENDATIONS = {
    "Safe Air Day":               "✅ Air quality is good. Safe for all outdoor activities.",
    "Moderate Risk Day":          "⚠️ Acceptable quality. Sensitive groups should limit prolonged exertion.",
    "High Respiratory Risk Day":  "🟠 Elevated risk. People with respiratory conditions should stay indoors.",
    "Mask Recommended Day":       "😷 Wear a mask outdoors. Minimize outdoor exposure.",
    "Avoid Outdoor Activity Day": "🚫 Hazardous conditions. Stay indoors with windows closed.",
}

# ══════════════════════════════════════════════════════════════════════════════
# 3. HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt(val):
    try:
        return round(float(val), 1) if pd.notna(val) else "N/A"
    except Exception:
        return "N/A"

def get_secret(key):
    """Read from st.secrets[database] → st.secrets → os.getenv fallback."""
    try:
        return st.secrets["database"][key]
    except Exception:
        try:
            return st.secrets[key]
        except Exception:
            return os.getenv(key)

# ══════════════════════════════════════════════════════════════════════════════
# 4. DATABASE CONNECTION  (no cache — required for serverless wake-up)
# ══════════════════════════════════════════════════════════════════════════════
def get_conn():
    conn_str = (
        f"DRIVER={{{get_secret('DRIVER')}}};"
        f"SERVER=tcp:{get_secret('SERVER')},1433;"
        f"DATABASE={get_secret('DATABASE')};"
        f"UID={get_secret('USERNAME')};"
        f"PWD={get_secret('PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=60;"
    )
    return pyodbc.connect(conn_str)

def run_query(sql):
    try:
        conn = get_conn()
        df   = pd.read_sql(sql, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════════════════════
# 5. SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.image(
    "https://img.icons8.com/fluency/96/wind.png", width=55
)
st.sidebar.title("AETHER")
st.sidebar.caption("Environmental Health Intelligence — Cairo, Egypt")
st.sidebar.divider()

if st.sidebar.button("🔄 Force Refresh / Wake DB"):
    st.rerun()

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "🌿 Environmental Overview", "🫁 Health Intelligence", "🔮 Forecasts"]
)

# ══════════════════════════════════════════════════════════════════════════════
# 6. WAKE-UP CHECK
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("🔌 Connecting to Azure database..."):
    date_info = run_query(
        "SELECT MIN(date) as mn, MAX(date) as mx FROM Gold.EnvironmentalFeatures"
    )

if date_info.empty or pd.isna(date_info['mn'].iloc[0]):
    st.warning(
        "⏳ Database is waking up (Azure serverless mode). "
        "Wait **30 seconds** then click **Force Refresh / Wake DB**."
    )
    st.info(
        "This only happens on the first visit after inactivity. "
        "All subsequent loads are instant."
    )
    st.stop()

min_db = pd.to_datetime(date_info['mn'].iloc[0]).date()
max_db = pd.to_datetime(date_info['mx'].iloc[0]).date()

st.sidebar.divider()
date_range = st.sidebar.date_input(
    "📅 Date Range",
    value=(min_db, max_db),
    min_value=min_db,
    max_value=max_db
)
start_date, end_date = (
    (date_range[0], date_range[1])
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2
    else (min_db, max_db)
)

# ══════════════════════════════════════════════════════════════════════════════
# 7. LOAD MAIN DATA
# ══════════════════════════════════════════════════════════════════════════════
df = run_query(f"""
    SELECT * FROM Gold.EnvironmentalFeatures
    WHERE date BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY date
""")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — HOME
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Home":
    st.title("🌍 AETHER — Environmental Health Intelligence")
    st.caption("Air Quality & Respiratory Risk Platform — Cairo, Egypt")
    st.divider()

    if df.empty:
        st.warning("No data available for the selected range.")
        st.stop()

    latest = df.iloc[-1]

    # ── KPI row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(
        "📅 Date",
        str(latest['date'].date() if hasattr(latest['date'], 'date') else latest['date'])
    )
    c2.metric("💨 AQI",           fmt(latest['aqi']))
    c3.metric("🌫️ PM2.5",         fmt(latest['pm25']))
    c4.metric("🌡️ Temperature",   f"{fmt(latest['temperature'])} °C")
    c5.metric("🔥 Heat Index",    fmt(latest['heat_index']))

    st.divider()

    # ── Health banner ─────────────────────────────────────────────────────────
    cat   = latest['health_category'] if pd.notna(latest['health_category']) else "Unknown"
    color = COLORS.get(cat, "#95a5a6")
    st.markdown(f"""
        <div style="background:{color};padding:25px;border-radius:14px;text-align:center;">
            <h2 style="color:white;margin:0;">CURRENT STATUS: {cat}</h2>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Recommendation ────────────────────────────────────────────────────────
    st.info(RECOMMENDATIONS.get(cat, "Monitor conditions closely."))

    # ── AQI trend ─────────────────────────────────────────────────────────────
    st.subheader("AQI Trend — Last 30 Days")
    fig = px.area(
        df.tail(30), x="date", y="aqi",
        color_discrete_sequence=["#3498db"]
    )
    fig.update_layout(height=280, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # ── Extra KPI row ─────────────────────────────────────────────────────────
    st.divider()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💧 Humidity",         f"{fmt(latest['humidity'])} %")
    k2.metric("🌬️ Wind Speed",       f"{fmt(latest['wind'])} km/h")
    k3.metric("🧪 Respiratory Stress", fmt(latest['respiratory_stress']))
    k4.metric("🌫️ Pollution Level",   fmt(latest['pollution_level']))

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — ENVIRONMENTAL OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌿 Environmental Overview":
    st.title("🌿 Environmental Overview")
    st.divider()

    # ── Row 1: AQI + PM2.5 ───────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("AQI Over Time")
        fig = px.line(df, x="date", y="aqi", color_discrete_sequence=["#e74c3c"])
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("PM2.5 Over Time")
        fig = px.line(df, x="date", y="pm25", color_discrete_sequence=["#e67e22"])
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Temperature + Donut ────────────────────────────────────────────
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Temperature vs Heat Index")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['temperature'],
            name='Temperature', line=dict(color='#f39c12')
        ))
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['heat_index'],
            name='Heat Index', line=dict(color='#e74c3c')
        ))
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        st.subheader("Health Category Distribution")
        cat_counts = df['health_category'].value_counts().reset_index()
        cat_counts.columns = ['category', 'count']
        fig = px.pie(
            cat_counts, names='category', values='count',
            color='category', color_discrete_map=COLORS, hole=0.45
        )
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Monthly AQI bar ────────────────────────────────────────────────
    st.subheader("Monthly Average AQI")
    df_m          = df.copy()
    df_m['month'] = pd.to_datetime(df_m['date']).dt.to_period('M').astype(str)
    monthly       = df_m.groupby('month')['aqi'].mean().reset_index()
    fig = px.bar(monthly, x='month', y='aqi', color_discrete_sequence=["#3498db"])
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # ── Row 4: Pollution scatter ──────────────────────────────────────────────
    st.subheader("PM2.5 vs Ozone Relationship")
    fig = px.scatter(
        df, x="pm25", y="ozone",
        color="health_category", color_discrete_map=COLORS,
        opacity=0.6, size_max=8
    )
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — HEALTH INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🫁 Health Intelligence":
    st.title("🫁 Health Intelligence")
    st.divider()

    preds = run_query("""
        SELECT TOP 30 date, health_category, aqi, pm25, predicted_at
        FROM Gold.RiskPredictions
        ORDER BY date DESC
    """)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Latest Prediction")
        if not preds.empty:
            lp    = preds.iloc[0]
            cat   = lp['health_category']
            color = COLORS.get(cat, "#95a5a6")
            st.markdown(f"""
                <div style="background:{color};padding:18px;border-radius:12px;
                            text-align:center;color:white;">
                    <h3 style="margin:0;">{cat}</h3>
                </div>
            """, unsafe_allow_html=True)
            st.metric("Predicted AQI",   fmt(lp['aqi']))
            st.metric("Predicted PM2.5", fmt(lp['pm25']))
            st.caption(f"Predicted at: {lp['predicted_at']}")
        else:
            st.info("No predictions available.")

    with c2:
        st.subheader("Prediction History")
        st.dataframe(preds, use_container_width=True, height=300)

    # ── Respiratory stress scatter ─────────────────────────────────────────────
    st.subheader("Respiratory Stress vs AQI")
    fig = px.scatter(
        df, x="aqi", y="respiratory_stress",
        color="health_category", color_discrete_map=COLORS, opacity=0.65
    )
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # ── Monthly risk breakdown ────────────────────────────────────────────────
    st.subheader("Monthly Health Risk Breakdown")
    df_r          = df.copy()
    df_r['month'] = pd.to_datetime(df_r['date']).dt.to_period('M').astype(str)
    risk_monthly  = (
        df_r.groupby(['month', 'health_category'])
            .size()
            .reset_index(name='count')
    )
    fig = px.bar(
        risk_monthly, x='month', y='count',
        color='health_category', color_discrete_map=COLORS,
        barmode='stack'
    )
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — FORECASTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Forecasts":
    st.title("🔮 Environmental Forecasts")
    st.divider()

    forecasts = run_query("""
        SELECT forecast_date, forecast_horizon,
               predicted_category, confidence, model_version
        FROM Gold.ForecastPredictions
        ORDER BY forecast_date ASC
    """)

    if forecasts.empty:
        st.warning("No forecast data available yet.")
        st.stop()

    # ── 7-day cards ───────────────────────────────────────────────────────────
    st.subheader("7-Day Outlook")
    upcoming = forecasts.head(7)
    cols     = st.columns(min(len(upcoming), 7))

    for i, (_, row) in enumerate(upcoming.iterrows()):
        with cols[i % 7]:
            cat   = row['predicted_category']
            color = COLORS.get(cat, "#95a5a6")
            try:
                day_label = pd.to_datetime(row['forecast_date']).strftime('%a %d')
            except Exception:
                day_label = str(row['forecast_date'])
            conf = (
                f"{round(float(row['confidence']) * 100, 1)}%"
                if pd.notna(row['confidence']) else "N/A"
            )
            st.markdown(f"""
                <div style="background:{color};padding:12px;border-radius:10px;
                            text-align:center;color:white;min-height:110px;">
                    <small>{day_label}</small><br>
                    <b style="font-size:12px;">{cat}</b><br>
                    <small>Conf: {conf}</small>
                </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── Confidence chart ──────────────────────────────────────────────────────
    st.subheader("Forecast Confidence Over Time")
    fig = px.bar(
        forecasts, x="forecast_date", y="confidence",
        color="predicted_category", color_discrete_map=COLORS
    )
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # ── Full table ────────────────────────────────────────────────────────────
    st.subheader("Full Forecast Log")
    st.dataframe(forecasts, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.divider()
st.sidebar.caption("AETHER v1.0 · Cairo, Egypt")
st.sidebar.caption("Nada Hosny")
