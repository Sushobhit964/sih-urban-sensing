import os
import textwrap
from datetime import datetime

import pandas as pd
import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# ============================================================
# PAGE
# ============================================================
st.set_page_config(
    page_title="Urban AI Command Center",
    page_icon="🚍",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INCIDENT_FILE = os.path.join(OUTPUT_DIR, "incidents.csv")
ALERT_FILE = os.path.join(OUTPUT_DIR, "alerts.csv")


def render_html(html):
    st.markdown(textwrap.dedent(html).strip(), unsafe_allow_html=True)


def load_csv(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def safe_text(value, default="N/A"):
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    return str(value)


def clean_gps(df):
    if df.empty or "Latitude" not in df.columns or "Longitude" not in df.columns:
        return pd.DataFrame()
    x = df.copy()
    x["Latitude"] = pd.to_numeric(x["Latitude"], errors="coerce")
    x["Longitude"] = pd.to_numeric(x["Longitude"], errors="coerce")
    x = x.dropna(subset=["Latitude", "Longitude"])
    return x[x["Latitude"].between(-90, 90) & x["Longitude"].between(-180, 180)]


def value_count(df, col, value):
    if df.empty or col not in df.columns:
        return 0
    return int(df[col].astype(str).str.upper().eq(value.upper()).sum())


def make_map(df, mode="incidents", height=480):
    gps = clean_gps(df)
    if gps.empty:
        center = [23.83, 80.40]
    else:
        center = [float(gps["Latitude"].mean()), float(gps["Longitude"].mean())]

    m = folium.Map(location=center, zoom_start=12, control_scale=True, tiles="CartoDB positron")
    points = []

    for _, row in gps.iterrows():
        lat, lon = float(row["Latitude"]), float(row["Longitude"])
        severity = safe_text(row.get("Severity", "LOW")).upper()
        typ = safe_text(row.get("Type", "INCIDENT"))
        color = {"HIGH": "red", "MEDIUM": "orange", "LOW": "green"}.get(severity, "blue")
        weight = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}.get(severity, 0.5)
        points.append([lat, lon, weight])

        popup = f"""
        <div style='width:240px;font-family:Arial'>
        <b style='font-size:15px'>{typ}</b><br><br>
        <b>Severity:</b> {severity}<br>
        <b>Object:</b> {safe_text(row.get('Object_Type'))}<br>
        <b>Confidence:</b> {safe_text(row.get('Confidence'))}<br>
        <b>Time:</b> {safe_text(row.get('Video_Time'))}
        </div>
        """
        folium.CircleMarker(
            [lat, lon], radius=7 if mode == "incidents" else 5,
            color=color, fill=True, fill_opacity=0.85,
            popup=folium.Popup(popup, max_width=300), tooltip=typ
        ).add_to(m)

    if points:
        HeatMap(points, radius=28 if mode == "heat" else 20, blur=22, min_opacity=0.25).add_to(m)
    return m, gps


# ============================================================
# DATA
# ============================================================
incidents = load_csv(INCIDENT_FILE)
alerts = load_csv(ALERT_FILE)
congestion = load_csv(os.path.join(OUTPUT_DIR, "congestion.csv"))
violations = load_csv(os.path.join(OUTPUT_DIR, "violations.csv"))
registry = load_csv(os.path.join(OUTPUT_DIR, "vehicle_registry.csv"))

if not alerts.empty and "Alert_Level" in alerts.columns:
    alerts["Alert_Level"] = alerts["Alert_Level"].fillna("INFORMATION").astype(str).str.upper()

# ============================================================
# CSS — organized command-center design
# ============================================================
render_html("""
<style>
:root { --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --panel:#ffffff; --bg:#f6f8fc; }
.stApp { background:var(--bg); }
.block-container { max-width:1550px; padding-top:1.1rem; padding-bottom:2.5rem; }
section[data-testid="stSidebar"] { background:#0b1220; }
section[data-testid="stSidebar"] * { color:#e5edf7 !important; }

.hero { position:relative; overflow:hidden; background:linear-gradient(115deg,#08111f,#12243a 55%,#17314a); border-radius:22px; padding:30px 34px; margin-bottom:18px; box-shadow:0 16px 40px rgba(15,23,42,.16); }
.hero:after { content:""; position:absolute; width:260px; height:260px; right:-70px; top:-120px; border:1px solid rgba(255,255,255,.10); border-radius:50%; box-shadow:0 0 0 35px rgba(255,255,255,.025),0 0 0 70px rgba(255,255,255,.02); }
.hero-title { color:#fff; font-size:32px; font-weight:850; letter-spacing:-.8px; }
.hero-sub { color:#a9b9cc; margin-top:7px; font-size:14px; }
.hero-meta { display:flex; gap:9px; flex-wrap:wrap; margin-top:17px; }
.pill { display:inline-block; border:1px solid rgba(255,255,255,.13); background:rgba(255,255,255,.06); color:#dbeafe; padding:6px 10px; border-radius:999px; font-size:11px; font-weight:700; }
.pill.live { background:rgba(16,185,129,.13); color:#86efac; border-color:rgba(16,185,129,.25); }

.section { margin:28px 0 12px; display:flex; align-items:center; gap:10px; }
.section h2 { margin:0; color:var(--ink); font-size:21px; font-weight:850; letter-spacing:-.35px; }
.section .line { height:1px; background:var(--line); flex:1; }
.section small { color:var(--muted); font-size:11px; font-weight:700; }

.kpi { background:var(--panel); border:1px solid var(--line); border-radius:17px; padding:17px 18px; min-height:112px; box-shadow:0 5px 18px rgba(15,23,42,.045); }
.kpi-label { color:var(--muted); font-size:10px; font-weight:850; letter-spacing:.65px; text-transform:uppercase; }
.kpi-value { color:var(--ink); font-size:29px; font-weight:850; margin-top:7px; }
.kpi-foot { color:#94a3b8; font-size:10px; margin-top:4px; }
.red {color:#dc2626}.amber{color:#d97706}.blue{color:#2563eb}.green{color:#059669}.violet{color:#7c3aed}

.panel { background:#fff; border:1px solid var(--line); border-radius:18px; padding:17px; box-shadow:0 5px 18px rgba(15,23,42,.045); }
.panel-title { color:var(--ink); font-size:14px; font-weight:850; margin-bottom:3px; }
.panel-sub { color:var(--muted); font-size:11px; margin-bottom:12px; }
.status { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #eef2f7; padding:11px 0; }
.status:last-child{border-bottom:0}.status-name{font-size:12px;font-weight:750;color:var(--ink)}.status-desc{font-size:10px;color:var(--muted)}
.ok {color:#059669;font-size:10px;font-weight:850}.warn{color:#d97706;font-size:10px;font-weight:850}
.alert { border:1px solid var(--line); border-left:4px solid #dc2626; background:#fff; border-radius:13px; padding:12px 13px; margin-bottom:9px; }
.alert.warning{border-left-color:#f59e0b}.alert.info{border-left-color:#2563eb}
.alert-head{display:flex;justify-content:space-between;gap:8px}.badge{font-size:9px;font-weight:900;padding:4px 7px;border-radius:999px}.critical{background:#fee2e2;color:#b91c1c}.warning-b{background:#fef3c7;color:#a16207}.info-b{background:#dbeafe;color:#1d4ed8}
.alert-title{font-size:12px;font-weight:850;color:var(--ink);margin-top:8px}.alert-meta{font-size:10px;color:var(--muted);line-height:1.7;margin-top:3px}

.map-card { background:#fff;border:1px solid var(--line);border-radius:18px;padding:12px;box-shadow:0 5px 18px rgba(15,23,42,.045); }
.map-head{display:flex;justify-content:space-between;align-items:center;padding:4px 5px 10px}.map-title{font-size:14px;font-weight:850;color:var(--ink)}.map-note{font-size:10px;color:var(--muted)}
.empty-map{height:410px;border-radius:12px;background:linear-gradient(145deg,#eef3f8,#f8fafc);display:flex;align-items:center;justify-content:center;text-align:center;color:#64748b;font-size:12px}

.metric-strip { background:#fff;border:1px solid var(--line);border-radius:16px;padding:12px 15px; }
.footer { text-align:center;color:#94a3b8;font-size:11px;padding:28px 0 8px; }
</style>
""")

# ============================================================
# HERO
# ============================================================
now = datetime.now().strftime("%d %b %Y  •  %H:%M")
render_html(f"""
<div class='hero'>
  <div class='hero-title'>🚍 Urban AI Command Center</div>
  <div class='hero-sub'>AI-powered onboard intelligence for road safety, traffic monitoring, infrastructure health and centralized response.</div>
  <div class='hero-meta'>
    <span class='pill live'>● PLATFORM ONLINE</span><span class='pill'>EDGE AI</span><span class='pill'>GIS INTELLIGENCE</span><span class='pill'>ANPR</span><span class='pill'>CENTRAL ALERTS</span><span class='pill'>{now}</span>
  </div>
</div>
""")

# ============================================================
# SIDEBAR / FILTERS
# ============================================================
with st.sidebar:
    st.markdown("# 🎛️ Control Room")
    st.caption("Urban sensing operations")
    st.divider()
    st.markdown("### Filters")
    types = ["ALL"] + (sorted(incidents["Type"].dropna().astype(str).unique().tolist()) if not incidents.empty and "Type" in incidents else [])
    selected_type = st.selectbox("Incident type", types)
    selected_severity = st.selectbox("Severity", ["ALL", "HIGH", "MEDIUM", "LOW"])
    st.divider()
    st.markdown("### Modules")
    for x in ["🕳️ Road hazards", "🛣️ Infrastructure", "🚗 Vehicle tracking", "🚦 Traffic intelligence", "🚶 Pedestrian safety", "🌊 Waterlogging", "🪪 ANPR / registration", "🗺️ GIS + heatmaps"]:
        st.caption(x)
    st.divider()
    if st.button("🔄 Refresh dashboard", use_container_width=True):
        st.rerun()

filtered = incidents.copy()
if not filtered.empty and selected_type != "ALL" and "Type" in filtered:
    filtered = filtered[filtered["Type"].astype(str) == selected_type]
if not filtered.empty and selected_severity != "ALL" and "Severity" in filtered:
    filtered = filtered[filtered["Severity"].astype(str).str.upper() == selected_severity]

critical = value_count(alerts, "Alert_Level", "CRITICAL")
warning = value_count(alerts, "Alert_Level", "WARNING")
high_inc = value_count(filtered, "Severity", "HIGH")
potholes = int(filtered["Type"].astype(str).str.upper().str.contains("POTHOLE", na=False).sum()) if not filtered.empty and "Type" in filtered else 0
traffic_events = int(filtered["Type"].astype(str).str.upper().str.contains("TRAFFIC|CONGESTION|RASH|WRONG", regex=True, na=False).sum()) if not filtered.empty and "Type" in filtered else 0
readable_plates = 0
if not registry.empty and "License_Plate" in registry:
    p = registry["License_Plate"].astype(str).str.upper()
    readable_plates = int((~p.isin(["", "UNKNOWN", "NAN", "N/A", "NOT_FOUND"])).sum())

# ============================================================
# OVERVIEW KPIs
# ============================================================
render_html("<div class='section'><h2>Operations Overview</h2><div class='line'></div><small>FILTERED VIEW</small></div>")
k = st.columns(6)
items = [
    ("CRITICAL ALERTS", critical, "Immediate attention", "red"),
    ("WARNINGS", warning, "Needs review", "amber"),
    ("TOTAL INCIDENTS", len(filtered), "Detected events", "blue"),
    ("HIGH SEVERITY", high_inc, "Priority hazards", "red"),
    ("TRAFFIC EVENTS", traffic_events, "Traffic intelligence", "green"),
    ("READABLE PLATES", readable_plates, "ANPR observations", "violet"),
]
for col, (label, val, foot, cls) in zip(k, items):
    with col:
        render_html(f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-value {cls}'>{val}</div><div class='kpi-foot'>{foot}</div></div>")

# ============================================================
# LIVE OPERATIONS
# ============================================================
render_html("<div class='section'><h2>Live Operations</h2><div class='line'></div><small>ONBOARD CAMERA → EDGE AI → CONTROL ROOM</small></div>")
input_dir = os.path.join(BASE_DIR, "data", "input")
videos = [os.path.join(input_dir, n) for n in sorted(os.listdir(input_dir)) if n.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))] if os.path.isdir(input_dir) else []
left, mid, right = st.columns([1.45, .85, .85], gap="large")
with left:
    st.markdown("#### 🎥 Camera Feed")
    if videos:
        idx = st.selectbox("Source", range(len(videos)), format_func=lambda i: os.path.basename(videos[i]), label_visibility="collapsed")
        with open(videos[idx], "rb") as f:
            st.video(f.read())
    else:
        st.info("No recorded camera source found in data/input/")
with mid:
    render_html("<div class='panel'><div class='panel-title'>🛰️ System Health</div><div class='panel-sub'>Subsystem availability</div><div class='status'><div><div class='status-name'>CAM-01</div><div class='status-desc'>Onboard camera</div></div><span class='ok'>● ONLINE</span></div><div class='status'><div><div class='status-name'>EDGE-AI</div><div class='status-desc'>Detection + tracking</div></div><span class='ok'>● ACTIVE</span></div><div class='status'><div><div class='status-name'>ALERT BUS</div><div class='status-desc'>Incident pipeline</div></div><span class='ok'>● ACTIVE</span></div><div class='status'><div><div class='status-name'>GIS</div><div class='status-desc'>Spatial intelligence</div></div><span class='ok'>● ONLINE</span></div></div>")
with right:
    render_html(f"<div class='panel'><div class='panel-title'>📡 Telemetry</div><div class='panel-sub'>Current processing snapshot</div><div class='status'><div><div class='status-name'>Frames</div><div class='status-desc'>Congestion records</div></div><b>{len(congestion):,}</b></div><div class='status'><div><div class='status-name'>Incidents</div><div class='status-desc'>Filtered events</div></div><b>{len(filtered):,}</b></div><div class='status'><div><div class='status-name'>High priority</div><div class='status-desc'>Requires attention</div></div><b>{high_inc:,}</b></div><div class='status'><div><div class='status-name'>Violations</div><div class='status-desc'>Recorded events</div></div><b>{len(violations):,}</b></div></div>")

# ============================================================
# ALERTS + INCIDENT FEED
# ============================================================
render_html("<div class='section'><h2>Alert Command Center</h2><div class='line'></div><small>PRIORITY RESPONSE</small></div>")
a, b = st.columns([1, 1.5], gap="large")
with a:
    st.markdown("#### 🚨 Priority Alerts")
    if alerts.empty:
        st.success("No alerts recorded.")
    else:
        for _, row in alerts.tail(6).iloc[::-1].iterrows():
            level = safe_text(row.get("Alert_Level"), "INFORMATION").upper()
            cls = "alert" if level == "CRITICAL" else "alert warning" if level == "WARNING" else "alert info"
            badge = "critical" if level == "CRITICAL" else "warning-b" if level == "WARNING" else "info-b"
            render_html(f"<div class='{cls}'><div class='alert-head'><span class='badge {badge}'>{level}</span><span class='alert-meta'>{safe_text(row.get('Video_Time'))}</span></div><div class='alert-title'>🚨 {safe_text(row.get('Incident_Type'), 'UNKNOWN')}</div><div class='alert-meta'>ID {safe_text(row.get('Incident_ID'))} · {safe_text(row.get('Object_Type'))} · Confidence {safe_text(row.get('Confidence'))}</div></div>")
with b:
    st.markdown("#### 📋 Incident Stream")
    if filtered.empty:
        st.info("No incidents match the current filters.")
    else:
        cols = [c for c in ["Incident_ID", "Type", "Severity", "Object_Type", "Confidence", "Video_Time"] if c in filtered.columns]
        st.dataframe(filtered[cols].tail(12).iloc[::-1], use_container_width=True, hide_index=True, height=355)

# ============================================================
# GIS INTELLIGENCE — TWO MAPS
# ============================================================
render_html("<div class='section'><h2>GIS Intelligence</h2><div class='line'></div><small>SPATIAL INCIDENT ANALYSIS</small></div>")
map1, map2 = st.columns(2, gap="large")
with map1:
    st.markdown("#### 📍 Incident Map")
    st.caption("Individual detected events with severity markers")
    m1, gps = make_map(filtered, "incidents")
    st_folium(m1, width=None, height=430, returned_objects=[], key="incident_map")
    if gps.empty:
        st.caption("No valid GPS coordinates are currently stored; map remains in monitoring-region mode.")
with map2:
    st.markdown("#### 🔥 Incident Density Heatmap")
    st.caption("Weighted spatial concentration of detected events")
    m2, gps2 = make_map(filtered, "heat")
    st_folium(m2, width=None, height=430, returned_objects=[], key="incident_density_heatmap")
    if gps2.empty:
        st.caption("Heatmap activates automatically when incidents contain valid latitude/longitude.")

# ============================================================
# ANALYTICS DASHBOARD — MORE VISUAL, LESS CLUTTER
# ============================================================
render_html("<div class='section'><h2>AI Detection Analytics</h2><div class='line'></div><small>PATTERNS • SEVERITY • HOTSPOTS</small></div>")

c1, c2, c3 = st.columns(3, gap="large")
with c1:
    st.markdown("#### Incident Mix")
    if not filtered.empty and "Type" in filtered:
        st.bar_chart(filtered["Type"].value_counts(), height=260)
    else: st.info("No incident data.")
with c2:
    st.markdown("#### Severity Profile")
    if not filtered.empty and "Severity" in filtered:
        s = filtered["Severity"].astype(str).str.upper().value_counts().reindex(["HIGH","MEDIUM","LOW"], fill_value=0)
        st.bar_chart(s, height=260)
    else: st.info("No severity data.")
with c3:
    st.markdown("#### Detection Timeline")

    if filtered.empty or "Video_Time" not in filtered.columns:
        st.info("No incident timeline data available yet.")
    else:
        timeline = filtered.copy()
        timeline["Video_Time"] = timeline["Video_Time"].astype(str)
        timeline = timeline[
            timeline["Video_Time"].notna()
            & (timeline["Video_Time"].str.strip() != "")
            & (timeline["Video_Time"].str.lower() != "nan")
            & (timeline["Video_Time"].str.lower() != "n/a")
        ]

        if timeline.empty:
            st.info("No valid video-time information available.")
        else:
            timeline_counts = (
                timeline.groupby("Video_Time")
                .size()
                .reset_index(name="Incidents")
                .set_index("Video_Time")
            )
            st.line_chart(timeline_counts["Incidents"], height=260)

# ============================================================
# TRAFFIC INTELLIGENCE
# ============================================================
render_html("<div class='section'><h2>Traffic Intelligence</h2><div class='line'></div><small>FLOW • CONGESTION • VIOLATIONS</small></div>")
if not congestion.empty:
    vehicle_series = pd.to_numeric(congestion.get("Vehicle_Count", pd.Series(dtype=float)), errors="coerce").dropna()
    high_frames = value_count(congestion, "Congestion_Level", "HIGH")
    t1, t2, t3, t4 = st.columns(4)
    for col, label, val in [(t1,"PEAK VEHICLES / FRAME",int(vehicle_series.max()) if not vehicle_series.empty else 0),(t2,"AVG VEHICLES / FRAME",round(float(vehicle_series.mean()),1) if not vehicle_series.empty else 0),(t3,"HIGH-CONGESTION FRAMES",high_frames),(t4,"VIOLATION EVENTS",len(violations))]:
        with col: render_html(f"<div class='metric-strip'><div class='kpi-label'>{label}</div><div style='font-size:23px;font-weight:850;color:#0f172a;margin-top:5px'>{val}</div></div>")
    q1,q2,q3 = st.columns(3, gap="large")
    with q1:
        st.markdown("#### Vehicle Composition")
        cols=[c for c in ["Cars","Motorcycles","Buses","Trucks","Bicycles"] if c in congestion]
        if cols: st.bar_chart(congestion[cols].apply(pd.to_numeric,errors="coerce").fillna(0).sum().sort_values(ascending=False),height=260)
    with q2:
        st.markdown("#### Congestion Trend")
        if "Vehicle_Count" in congestion:
            st.line_chart(pd.to_numeric(congestion["Vehicle_Count"],errors="coerce"),height=260)
    with q3:
        st.markdown("#### Congestion Level")
        if "Congestion_Level" in congestion:
            levels=congestion["Congestion_Level"].astype(str).str.upper().value_counts().reindex(["HIGH","MEDIUM","LOW"],fill_value=0)
            st.bar_chart(levels,height=260)
    if not violations.empty and "Violation" in violations:
        st.markdown("#### 🚦 Violation Breakdown")
        st.bar_chart(violations["Violation"].astype(str).value_counts(),height=220)
else:
    st.info("Traffic analytics will populate after the traffic pipeline generates output/congestion.csv.")

# ============================================================
# ANPR + EVIDENCE
# ============================================================
render_html("<div class='section'><h2>Vehicle & Evidence Intelligence</h2><div class='line'></div><small>TRACEABILITY</small></div>")
v1,v2=st.columns([1.25,1],gap="large")
with v1:
    st.markdown("#### 🪪 Vehicle Registration")
    if not registry.empty:
        cols=[c for c in ["Vehicle_ID","Vehicle_Type","License_Plate","OCR_Confidence","Video_Time","Evidence"] if c in registry]
        st.dataframe(registry[cols].tail(12).iloc[::-1],use_container_width=True,hide_index=True,height=330)
    else: st.info("No ANPR records yet. Run the license-plate pipeline.")
with v2:
    st.markdown("#### 📸 Evidence Inspector")
    evidence=[]
    if not filtered.empty and "Evidence" in filtered:
        for e in filtered["Evidence"].tolist():
            if isinstance(e,str) and e.strip() not in ("","N/A","nan"):
                p=e if os.path.isabs(e) else os.path.join(BASE_DIR,e)
                if os.path.exists(p): evidence.append(p)
    if evidence:
        chosen=st.selectbox("Evidence",evidence,format_func=os.path.basename)
        st.image(chosen,use_container_width=True)
    else: st.info("No evidence image is available for the selected incidents.")

# ============================================================
# DATABASE + FOOTER
# ============================================================
render_html("<div class='section'><h2>Incident Database</h2><div class='line'></div><small>AUDIT TRAIL</small></div>")
if not filtered.empty:
    st.dataframe(filtered.tail(40).iloc[::-1],use_container_width=True,hide_index=True,height=380)
else: st.info("No incidents match the selected filters.")

render_html("<div class='footer'>🚍 Urban AI Command Center &nbsp;•&nbsp; Edge AI &nbsp;•&nbsp; Computer Vision &nbsp;•&nbsp; GIS &nbsp;•&nbsp; Centralized Alerts &nbsp;•&nbsp; ANPR</div>")
