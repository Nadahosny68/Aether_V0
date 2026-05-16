import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
import urllib.parse
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import date, timedelta

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
# 2. CUSTOM CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    /* Metric cards */
    [data-testid="metric-container"] {
        background: #1C1F26;
        border: 1px solid #2d3139;
        border-radius: 12px;
        padding: 16px;
    }
    [data-testid="metric-container"] label {
        color: #8b949e !important;
        font-size: 13px !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #0E1117;
        border-right: 1px solid #2d3139;
    }
    /* Headers */
    h1 { color: #ffffff !important; }
    h2, h3 { color: #e0e0e0 !important; }
    /* Divider */
    hr { border-color: #2d3139 !important; }
    /* Selectbox */
    .stSelectbox > div { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 3. CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
COLORS = {
    "Safe Air Day":               "#2ecc71",
    "Moderate Risk Day":          "#f1c40f",
    "High Respiratory Risk Day":  "#e67e22",
    "Mask Recommended Day":       "#e74c3c",
    "Avoid Outdoor Activity Day": "#8e44ad",
}

RECOMMENDATIONS = {
    "Safe Air Day":               "✅ Air quality is good. Safe for all outdoor activities including exercise.",
    "Moderate Risk Day":          "⚠️ Acceptable air quality. Sensitive groups should limit prolonged outdoor exertion.",
    "High Respiratory Risk Day":  "🟠 Elevated respiratory risk. People with asthma or heart disease should stay indoors.",
    "Mask Recommended Day":       "😷 Wear a mask outdoors. Minimize time outside. Keep windows closed.",
    "Avoid Outdoor Activity Day": "🚫 Hazardous conditions. Everyone should stay indoors with windows closed.",
}

# AQI scale for reference bar
AQI_SCALE = [
    (0,   50,  "#2ecc71", "Good"),
    (51,  100, "#f1c40f", "Moderate"),
    (101, 150, "#e67e22", "Unhealthy for Sensitive"),
    (151, 200, "#e74c3c", "Unhealthy"),
    (201, 300, "#8e44ad", "Very Unhealthy"),
    (301, 500, "#7b241c", "Hazardous"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 4. HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt(val, decimals=1):
    try:
        return round(float(val), decimals) if pd.notna(val) else "N/A"
    except Exception:
        return "N/A"

def get_aqi_color(aqi_val):
    try:
        v = float(aqi_val)
        for lo, hi, color, _ in AQI_SCALE:
            if lo <= v <= hi:
                return color
    except Exception:
        pass
    return "#95a5a6"

def get_secret(key):
    try:
        return st.secrets["database"][key]
    except Exception:
        try:
            return st.secrets[key]
        except Exception:
            return os.getenv(key)

# ══════════════════════════════════════════════════════════════════════════════
# 5. DATABASE
# ══════════════════════════════════════════════════════════════════════════════
def get_engine():
    server   = get_secret('SERVER')
    database = get_secret('DATABASE')
    username = get_secret('USERNAME')
    password = urllib.parse.quote_plus(get_secret('PASSWORD'))
    return create_engine(
        f"mssql+pymssql://{username}:{password}@{server}/{database}"
    )

def run_query(sql):
    try:
        df = pd.read_sql(sql, get_engine())
        return df
    except Exception as e:
        st.error(f"❌ DB Error: {e}")
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════════════════════
# 6. SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=52)
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
# 7. WAKE-UP CHECK
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("🔌 Connecting to database..."):
    date_info = run_query(
        "SELECT MIN(date) as mn, MAX(date) as mx FROM Gold.EnvironmentalFeatures"
    )

if date_info.empty or pd.isna(date_info['mn'].iloc[0]):
    st.warning("⏳ Database is waking up. Wait **30 seconds** then click **Force Refresh / Wake DB**.")
    st.info("This only happens on first visit after inactivity. All subsequent loads are instant.")
    st.stop()

min_db = pd.to_datetime(date_info['mn'].iloc[0]).date()
max_db = pd.to_datetime(date_info['mx'].iloc[0]).date()

# ══════════════════════════════════════════════════════════════════════════════
# 8. DATE FILTER — Quick select + manual range
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.divider()
st.sidebar.subheader("📅 Date Filter")

quick = st.sidebar.selectbox(
    "Quick select",
    ["All Time", "Last 7 Days", "Last 30 Days",
     "Last 3 Months", "Last 6 Months", "Last Year", "Custom Range"],
    key="quick_select"
)

today = max_db

if quick == "Last 7 Days":
    start_date, end_date = today - timedelta(days=7), today
elif quick == "Last 30 Days":
    start_date, end_date = today - timedelta(days=30), today
elif quick == "Last 3 Months":
    start_date, end_date = today - timedelta(days=90), today
elif quick == "Last 6 Months":
    start_date, end_date = today - timedelta(days=180), today
elif quick == "Last Year":
    start_date, end_date = today - timedelta(days=365), today
elif quick == "Custom Range":
    date_range = st.sidebar.date_input(
        "Select range",
        value=(min_db, max_db),
        min_value=min_db,
        max_value=max_db
    )
    start_date, end_date = (
        (date_range[0], date_range[1])
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2
        else (min_db, max_db)
    )
else:  # All Time
    start_date, end_date = min_db, max_db

st.sidebar.caption(f"📆 {start_date} → {end_date}")

if st.sidebar.button("🔁 Reset to All Time"):
    st.session_state["quick_select"] = "All Time"
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 9. LOAD DATA
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
        st.warning("No data available for selected range.")
        st.stop()

    latest = df.iloc[-1]
    aqi_val  = fmt(latest['aqi'])
    aqi_color = get_aqi_color(latest['aqi'])

    # ── KPI cards with units ──────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📅 Date",
        str(latest['date'].date() if hasattr(latest['date'], 'date') else latest['date'])
    )
    c2.metric("💨 AQI (US EPA)",    f"{aqi_val} / 500")
    c3.metric("🌫️ PM2.5",           f"{fmt(latest['pm25'])} μg/m³")
    c4.metric("🌡️ Temperature",     f"{fmt(latest['temperature'])} °C")
    c5.metric("🔥 Heat Index",      f"{fmt(latest['heat_index'])} °C")

    st.divider()

    # ── AQI scale bar ─────────────────────────────────────────────────────────
    st.subheader("AQI Scale Reference")
    scale_cols = st.columns(6)
    labels = ["Good\n0-50", "Moderate\n51-100", "Unhealthy*\n101-150",
              "Unhealthy\n151-200", "Very Unhealthy\n201-300", "Hazardous\n301+"]
    scale_colors = ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#8e44ad", "#7b241c"]
    for i, (col, label, color) in enumerate(zip(scale_cols, labels, scale_colors)):
        border = "3px solid white" if i == next(
            (j for j, (lo, hi, c, _) in enumerate(AQI_SCALE) if lo <= float(aqi_val or 0) <= hi),
            -1
        ) else "none"
        col.markdown(f"""
            <div style="background:{color};padding:10px;border-radius:8px;
                        text-align:center;color:white;font-size:11px;
                        font-weight:bold;border:{border};">
                {label.replace(chr(10), '<br>')}
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Health status banner ──────────────────────────────────────────────────
    cat   = latest['health_category'] if pd.notna(latest['health_category']) else "Unknown"
    color = COLORS.get(cat, "#95a5a6")
    st.markdown(f"""
        <div style="background:{color};padding:25px;border-radius:14px;text-align:center;">
            <h2 style="color:white;margin:0;">CURRENT STATUS: {cat}</h2>
            <p style="color:white;margin:8px 0 0 0;opacity:0.9;">
                {RECOMMENDATIONS.get(cat, "")}
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Secondary KPIs with units ─────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("💧 Humidity",           f"{fmt(latest['humidity'])} %")
    k2.metric("🌬️ Wind Speed",         f"{fmt(latest['wind'])} km/h")
    k3.metric("🫁 Respiratory Stress", f"{fmt(latest['respiratory_stress'])}")
    k4.metric("🌫️ Pollution Level",    f"{fmt(latest['pollution_level'])}")
    k5.metric("☁️ PM10",               f"{fmt(latest['pm10'])} μg/m³")
    k6.metric("🌡️ Pressure",           f"{fmt(latest['pressure'])} hPa")

    st.divider()

    # ── AQI trend ─────────────────────────────────────────────────────────────
    st.subheader(f"AQI Trend — {quick}")
    fig = px.area(df, x="date", y="aqi",
                  color_discrete_sequence=[aqi_color],
                  labels={"aqi": "AQI (US Standard)", "date": "Date"})
    fig.add_hline(y=50,  line_dash="dot", line_color="#2ecc71",
                  annotation_text="Good threshold (50)")
    fig.add_hline(y=100, line_dash="dot", line_color="#f1c40f",
                  annotation_text="Moderate threshold (100)")
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="white")
    st.plotly_chart(fig, use_container_width=True)

    # ── Data note ─────────────────────────────────────────────────────────────
    st.caption(
        "ℹ️ **Note:** AQI values are calculated from historical OpenWeatherMap & Open-Meteo API data. "
        "Minor differences from real-time monitors are expected due to data source variation and "
        "nearest-station averaging. AQI follows US EPA standard."
    )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — ENVIRONMENTAL OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌿 Environmental Overview":
    st.title("🌿 Environmental Overview")
    st.caption(f"Showing data: {start_date} → {end_date}  |  {len(df)} records")
    st.divider()

    # ── Summary KPIs ──────────────────────────────────────────────────────────
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("📊 Avg AQI",    f"{fmt(df['aqi'].mean())}",
              delta=f"Max: {fmt(df['aqi'].max())}")
    s2.metric("🌫️ Avg PM2.5",  f"{fmt(df['pm25'].mean())} μg/m³",
              delta=f"Max: {fmt(df['pm25'].max())} μg/m³")
    s3.metric("🌡️ Avg Temp",   f"{fmt(df['temperature'].mean())} °C",
              delta=f"Max: {fmt(df['temperature'].max())} °C")
    s4.metric("💧 Avg Humidity", f"{fmt(df['humidity'].mean())} %")
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("AQI Over Time")
        fig = px.line(df, x="date", y="aqi",
                      labels={"aqi": "AQI (US)", "date": "Date"},
                      color_discrete_sequence=["#e74c3c"])
        fig.add_hline(y=100, line_dash="dot", line_color="#f1c40f",
                      annotation_text="WHO guideline")
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          font_color="white")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("PM2.5 Over Time")
        fig = px.line(df, x="date", y="pm25",
                      labels={"pm25": "PM2.5 (μg/m³)", "date": "Date"},
                      color_discrete_sequence=["#e67e22"])
        fig.add_hline(y=15, line_dash="dot", line_color="#f1c40f",
                      annotation_text="WHO annual guideline (15 μg/m³)")
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          font_color="white")
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Temperature vs Heat Index")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['date'], y=df['temperature'],
                                 name='Temperature (°C)', line=dict(color='#f39c12')))
        fig.add_trace(go.Scatter(x=df['date'], y=df['heat_index'],
                                 name='Heat Index (°C)', line=dict(color='#e74c3c')))
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          font_color="white",
                          yaxis_title="°C")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.subheader("Health Category Distribution")
        cat_counts = df['health_category'].value_counts().reset_index()
        cat_counts.columns = ['category', 'count']
        fig = px.pie(cat_counts, names='category', values='count',
                     color='category', color_discrete_map=COLORS, hole=0.45)
        fig.update_traces(textinfo='percent+label')
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0),
                          paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Average AQI (μg/m³ equivalent)")
    df_m          = df.copy()
    df_m['month'] = pd.to_datetime(df_m['date']).dt.to_period('M').astype(str)
    monthly       = df_m.groupby('month').agg(
        avg_aqi=('aqi', 'mean'),
        avg_pm25=('pm25', 'mean')
    ).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly['month'], y=monthly['avg_aqi'],
                         name='Avg AQI', marker_color='#3498db'))
    fig.add_trace(go.Bar(x=monthly['month'], y=monthly['avg_pm25'],
                         name='Avg PM2.5 (μg/m³)', marker_color='#e67e22'))
    fig.update_layout(height=320, barmode='group',
                      margin=dict(l=0,r=0,t=30,b=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="white", yaxis_title="Value")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("PM2.5 vs Ozone Relationship")
    fig = px.scatter(df, x="pm25", y="ozone",
                     color="health_category", color_discrete_map=COLORS,
                     opacity=0.6,
                     labels={"pm25": "PM2.5 (μg/m³)", "ozone": "Ozone (μg/m³)"})
    fig.update_layout(height=320, margin=dict(l=0,r=0,t=0,b=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="white")
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — HEALTH INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🫁 Health Intelligence":
    st.title("🫁 Health Intelligence")
    st.caption(f"Showing data: {start_date} → {end_date}")
    st.divider()

    preds = run_query("""
        SELECT TOP 30 date, health_category, aqi, pm25, predicted_at
        FROM Gold.RiskPredictions
        ORDER BY date DESC
    """)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Latest ML Prediction")
        if not preds.empty:
            lp    = preds.iloc[0]
            cat   = lp['health_category']
            color = COLORS.get(cat, "#95a5a6")
            st.markdown(f"""
                <div style="background:{color};padding:20px;border-radius:12px;
                            text-align:center;color:white;">
                    <h3 style="margin:0;">{cat}</h3>
                </div>
            """, unsafe_allow_html=True)
            st.metric("Predicted AQI",        f"{fmt(lp['aqi'])}")
            st.metric("Predicted PM2.5",      f"{fmt(lp['pm25'])} μg/m³")
            st.caption(f"Model run: {lp['predicted_at']}")
        else:
            st.info("No predictions available.")

    with c2:
        st.subheader("Recent Prediction History")
        if not preds.empty:
            display_preds = preds.copy()
            display_preds['aqi']  = display_preds['aqi'].apply(lambda x: f"{fmt(x)}")
            display_preds['pm25'] = display_preds['pm25'].apply(lambda x: f"{fmt(x)} μg/m³")
            display_preds.columns = ['Date', 'Health Category', 'AQI', 'PM2.5', 'Predicted At']
            st.dataframe(display_preds, use_container_width=True, height=280)

    st.divider()

    st.subheader("Respiratory Stress vs AQI")
    st.caption("Higher respiratory stress indicates greater health impact from pollution")
    fig = px.scatter(df, x="aqi", y="respiratory_stress",
                     color="health_category", color_discrete_map=COLORS,
                     opacity=0.65,
                     labels={
                         "aqi": "AQI (US Standard)",
                         "respiratory_stress": "Respiratory Stress Index"
                     })
    fig.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="white")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Health Risk Breakdown")
    df_r          = df.copy()
    df_r['month'] = pd.to_datetime(df_r['date']).dt.to_period('M').astype(str)
    risk_monthly  = (
        df_r.groupby(['month', 'health_category'])
            .size().reset_index(name='days')
    )
    fig = px.bar(risk_monthly, x='month', y='days',
                 color='health_category', color_discrete_map=COLORS,
                 barmode='stack',
                 labels={"days": "Number of Days", "month": "Month"})
    fig.update_layout(height=320, margin=dict(l=0,r=0,t=30,b=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="white")
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — FORECASTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Forecasts":
    st.title("🔮 Environmental Forecasts")
    st.divider()

    forecasts = run_query("""
        SELECT forecast_date, forecast_horizon,
               predicted_category, confidence, aqi, pm25
        FROM Gold.ForecastPredictions
        ORDER BY forecast_date ASC
    """)

    if forecasts.empty:
        st.warning("No forecast data available yet.")
        st.stop()

    # ── 7-day cards ───────────────────────────────────────────────────────────
    st.subheader("Upcoming Forecast")
    upcoming = forecasts.head(7)
    cols     = st.columns(min(len(upcoming), 7))

    for i, (_, row) in enumerate(upcoming.iterrows()):
        with cols[i % 7]:
            cat   = row['predicted_category']
            color = COLORS.get(cat, "#95a5a6")
            try:
                day_label = pd.to_datetime(row['forecast_date']).strftime('%a\n%d %b')
            except Exception:
                day_label = str(row['forecast_date'])
            conf = (
                f"{round(float(row['confidence']) * 100, 0):.0f}%"
                if pd.notna(row['confidence']) else "N/A"
            )
            aqi_f = fmt(row['aqi']) if 'aqi' in row and pd.notna(row.get('aqi')) else "—"
            st.markdown(f"""
                <div style="background:{color};padding:14px;border-radius:12px;
                            text-align:center;color:white;min-height:130px;">
                    <div style="font-size:13px;font-weight:bold;">
                        {day_label.replace(chr(10),'<br>')}
                    </div>
                    <div style="font-size:11px;margin-top:6px;font-weight:bold;">
                        {cat}
                    </div>
                    <div style="font-size:11px;margin-top:4px;opacity:0.85;">
                        AQI: {aqi_f}
                    </div>
                    <div style="font-size:11px;opacity:0.85;">
                        Conf: {conf}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.subheader("Forecast Confidence Over Time")
    fig = px.bar(forecasts, x="forecast_date", y="confidence",
                 color="predicted_category", color_discrete_map=COLORS,
                 labels={
                     "confidence": "Confidence Score (0–1)",
                     "forecast_date": "Forecast Date"
                 })
    fig.update_layout(height=320, margin=dict(l=0,r=0,t=0,b=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="white")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Full Forecast Log")
    if not forecasts.empty:
        display_fc = forecasts.copy()
        if 'confidence' in display_fc.columns:
            display_fc['confidence'] = display_fc['confidence'].apply(
                lambda x: f"{round(float(x)*100,1)}%" if pd.notna(x) else "N/A"
            )
        if 'aqi' in display_fc.columns:
            display_fc['aqi'] = display_fc['aqi'].apply(
                lambda x: f"{fmt(x)}" if pd.notna(x) else "N/A"
            )
        st.dataframe(display_fc, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.divider()
st.sidebar.caption("AETHER v2.0 · Cairo, Egypt")
st.sidebar.caption("Nada Hosny")
st.sidebar.caption("Data: OpenWeatherMap · Open-Meteo · WAQI")
