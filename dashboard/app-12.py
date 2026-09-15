import os
from datetime import datetime
import math
import pandas as pd
import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Urban AI Command Center", page_icon="🚍", layout="wide", initial_sidebar_state="expanded")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INPUT_DIR = os.path.join(BASE_DIR, "data", "input")

FILES = {
    "incidents": "incidents.csv", "alerts": "alerts.csv", "congestion": "congestion.csv",
    "violations": "violations.csv", "potholes": "potholes/potholes.csv",
    "road_damage": "road_damage/road_damage.csv", "pedestrian": "pedestrian_risk/pedestrian_risk.csv",
    "waterlogging": "waterlogging/waterlogging.csv", "route_risk": "route_risk.csv",
    "hotspots": "incident_hotspots.csv", "bus_monitoring": "bus_monitoring.csv",
    "route_delay": "route_delay.csv", "vehicle_flow": "vehicle_flow.csv",
    "camera_health": "camera_health.csv", "sync_log": "sync_log.csv",
    "registry": "vehicle_registry/vehicle_registry.csv", "maintenance": "maintenance_prediction.csv",
    "correlations": "incident_correlations.csv", "recommendations": "route_recommendation.csv",
    "security": "security_audit.csv", "data_quality": "data_quality.csv", "geofence": "geofence_alerts.csv",
}


def load_csv(name):
    path = os.path.join(OUTPUT_DIR, name)
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


data = {k: load_csv(v) for k, v in FILES.items()}
incidents = data["incidents"]
alerts = data["alerts"]


def txt(v, default="N/A"):
    if v is None:
        return default
    try:
        if pd.isna(v):
            return default
    except Exception:
        pass
    return str(v)


def count(df, col, value):
    if df.empty or col not in df.columns:
        return 0
    return int(df[col].astype(str).str.upper().eq(value.upper()).sum())


def clean_gps(df):
    if df.empty or "Latitude" not in df.columns or "Longitude" not in df.columns:
        return pd.DataFrame()
    x = df.copy()
    x["Latitude"] = pd.to_numeric(x["Latitude"], errors="coerce")
    x["Longitude"] = pd.to_numeric(x["Longitude"], errors="coerce")
    x = x.dropna(subset=["Latitude", "Longitude"])
    return x[x["Latitude"].between(-90, 90) & x["Longitude"].between(-180, 180)]


def kpi(label, value, note=""):
    st.markdown(f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div><div class='kpi-note'>{note}</div></div>", unsafe_allow_html=True)


def empty_state(title, output, command, reason):
    st.markdown(f"""
    <div class='empty-card'>
      <div class='empty-title'>{title} <span>NOT GENERATED</span></div>
      <div class='empty-text'>{reason}</div>
      <div class='empty-code'>{output}</div>
      <div class='empty-run'>▶ {command}</div>
    </div>""", unsafe_allow_html=True)


def severity_color(s):
    return {"CRITICAL": "darkred", "HIGH": "red", "MEDIUM": "orange", "LOW": "green"}.get(str(s).upper(), "blue")


def incident_map(df, heat=False, show_geofence=False):
    gps = clean_gps(df)
    if gps.empty:
        m = folium.Map(location=[22.7196, 75.8577], zoom_start=12, tiles="OpenStreetMap", control_scale=True)
        return m, gps
    center = [gps.Latitude.mean(), gps.Longitude.mean()]
    m = folium.Map(location=center, zoom_start=13, tiles="OpenStreetMap", control_scale=True)
    points = []
    for _, r in gps.iterrows():
        sev = txt(r.get("Severity", "LOW")).upper()
        lat, lon = float(r.Latitude), float(r.Longitude)
        points.append([lat, lon, {"CRITICAL":1.3,"HIGH":1,"MEDIUM":.65,"LOW":.35}.get(sev,.5)])
        folium.CircleMarker([lat, lon], radius=7, color=severity_color(sev), fill=True, fill_opacity=.85,
            popup=folium.Popup(f"<b>{txt(r.get('Type','INCIDENT'))}</b><br>Severity: {sev}<br>Object: {txt(r.get('Object_Type'))}<br>Confidence: {txt(r.get('Confidence'))}<br>Time: {txt(r.get('Video_Time'))}", max_width=320)).add_to(m)
    if heat and points:
        HeatMap(points, radius=28, blur=20, min_opacity=.3).add_to(m)
    return m, gps


def geofence_map(df):
    gps = clean_gps(df)
    if gps.empty:
        m = folium.Map(location=[22.7196, 75.8577], zoom_start=12, tiles="OpenStreetMap")
        return m, gps
    center = [gps.Latitude.mean(), gps.Longitude.mean()]
    m = folium.Map(location=center, zoom_start=13, tiles="OpenStreetMap", control_scale=True)
    for _, r in gps.iterrows():
        sev = txt(r.get("Escalated_Severity", r.get("Severity", "LOW"))).upper()
        name = txt(r.get("Geofence", r.get("Zone", r.get("Geofence_Name", "Configured Zone"))))
        folium.Circle([float(r.Latitude), float(r.Longitude)], radius=120, color=severity_color(sev), fill=True, fill_opacity=.10).add_to(m)
        folium.Marker([float(r.Latitude), float(r.Longitude)], tooltip=name,
            popup=f"<b>{name}</b><br>Status: {txt(r.get('Status',r.get('Alert_Status','ESCALATED')))}<br>Severity: {sev}<br>Incident: {txt(r.get('Incident_Type',r.get('Type')))}").add_to(m)
    return m, gps


st.markdown("""
<style>
.stApp{background:#f4f7fb}.block-container{max-width:1550px;padding-top:1rem}
section[data-testid="stSidebar"]{background:#0b1220;border-right:1px solid #1e293b}
section[data-testid="stSidebar"] *{color:#e8eef7!important}
section[data-testid="stSidebar"] [data-baseweb="select"]>div{background:#162235!important;border:1px solid #334155!important;border-radius:10px!important}
section[data-testid="stSidebar"] [data-baseweb="select"] div{color:#f8fafc!important}
section[data-testid="stSidebar"] [data-baseweb="select"] svg{fill:#94a3b8!important}
[data-baseweb="popover"]{background:#111827!important}.stSelectbox label,.stRadio label{font-weight:700!important}
.hero{background:linear-gradient(120deg,#07111f,#153752);border-radius:22px;padding:28px 32px;color:white;margin-bottom:18px}
.hero h1{margin:0;font-size:31px}.hero p{color:#b8c7d9;margin:7px 0}.pill{display:inline-block;margin:12px 7px 0 0;padding:6px 10px;border-radius:999px;background:#ffffff12;color:#dbeafe;font-size:10px;font-weight:800}.live{color:#86efac!important}
.kpi{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:16px;min-height:102px;box-shadow:0 4px 15px #0f172a0a}.kpi-label{color:#64748b;font-size:10px;font-weight:850;letter-spacing:.6px}.kpi-value{color:#0f172a;font-size:27px;font-weight:850;margin-top:7px}.kpi-note{color:#94a3b8;font-size:10px;margin-top:4px}
.section{font-size:21px;font-weight:850;color:#0f172a;margin:18px 0 10px}.panel{background:white;border:1px solid #e2e8f0;border-radius:17px;padding:16px}.empty-card{background:#fff;border:1px dashed #cbd5e1;border-radius:15px;padding:16px;margin:6px 0 12px}.empty-title{font-weight:850;color:#334155}.empty-title span{float:right;font-size:10px;color:#b45309;background:#fff7ed;padding:5px 8px;border-radius:999px}.empty-text{color:#64748b;font-size:12px;margin:8px 0}.empty-code,.empty-run{font-family:monospace;font-size:11px;background:#f8fafc;border-radius:8px;padding:8px;margin-top:6px;color:#475569}.empty-run{color:#0369a1}
.status{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid #eef2f7}.good{color:#059669;font-weight:800}.warn{color:#d97706;font-weight:800}.bad{color:#dc2626;font-weight:800}
</style>""", unsafe_allow_html=True)

now = datetime.now().strftime("%d %b %Y • %H:%M")
st.markdown(f"<div class='hero'><h1>🚍 Urban AI Command Center</h1><p>Edge AI → GIS → centralized alerts → fleet intelligence → evidence.</p><span class='pill live'>● CONTROL ROOM</span><span class='pill'>EDGE AI</span><span class='pill'>GIS</span><span class='pill'>ANPR</span><span class='pill'>CENTRAL ALERTS</span><span class='pill'>{now}</span></div>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("# 🎛️ Control Room")
    st.caption("Filter the entire operational dashboard")
    st.divider()
    types = ["ALL"] + (sorted(incidents["Type"].dropna().astype(str).unique().tolist()) if not incidents.empty and "Type" in incidents else [])
    selected_type = st.selectbox("Incident type", types, key="incident_type")
    selected_severity = st.selectbox("Severity", ["ALL","CRITICAL","HIGH","MEDIUM","LOW"], key="severity")
    st.divider()
    st.markdown("### 🧭 Dashboard regions")
    region = st.radio("Jump to region", ["Command Center","Camera & Edge AI","GIS Intelligence","Traffic & Flow","Road & Safety","Fleet & Routes","Security & Data","Evidence & Database"], key="region")
    st.divider()
    if st.button("🔄 Refresh data", width="stretch"):
        st.rerun()
    available = sum(not d.empty for d in data.values())
    st.markdown("### Output coverage")
    st.progress(available / len(data) if data else 0)
    st.caption(f"{available} / {len(data)} datasets have records")

filtered = incidents.copy()
if not filtered.empty and selected_type != "ALL" and "Type" in filtered:
    filtered = filtered[filtered.Type.astype(str) == selected_type]
if not filtered.empty and selected_severity != "ALL" and "Severity" in filtered:
    filtered = filtered[filtered.Severity.astype(str).str.upper() == selected_severity]

# Tabs
names=["🚨 Command Center","🎥 Camera & Edge AI","🗺️ GIS Intelligence","🚦 Traffic & Flow","🛣️ Road & Safety","🚍 Fleet & Routes","🔐 Security & Data","📋 Evidence & Database"]
tabs=st.tabs(names)

with tabs[0]:
    st.markdown("<div class='section'>Operations Overview</div>",unsafe_allow_html=True)
    c=st.columns(6)
    metrics=[("CRITICAL",count(alerts,"Alert_Level","CRITICAL"),"Immediate"),("WARNINGS",count(alerts,"Alert_Level","WARNING"),"Review"),("INCIDENTS",len(filtered),"Filtered events"),("HIGH",count(filtered,"Severity","HIGH"),"Priority hazards"),("VIOLATIONS",len(data["violations"]),"Traffic events"),("DATASETS",available,f"of {len(data)}")]
    for col,(a,b,d) in zip(c,metrics):
        with col:kpi(a,b,d)
    st.markdown("<div class='section'>Alert Intelligence</div>",unsafe_allow_html=True)
    a,b=st.columns([1,1.35],gap="large")
    with a:
        if alerts.empty: empty_state("Central Alerts","output/alerts.csv","python ai/alert_engine.py","The alert engine has not produced an alert log yet.")
        else:
            ac=alerts["Alert_Level"].value_counts() if "Alert_Level" in alerts else pd.Series()
            fig=px.pie(values=ac.values,names=ac.index,hole=.55,title="Alert priority distribution")
            fig.update_layout(height=330,margin=dict(l=10,r=10,t=55,b=10))
            st.plotly_chart(fig,use_container_width=True)
    with b:
        if filtered.empty: st.info("No incidents match the current filters.")
        elif "Type" in filtered:
            vc=filtered.Type.astype(str).value_counts().head(12).sort_values()
            fig=px.bar(x=vc.values,y=vc.index,orientation="h",title="Incident mix")
            fig.update_layout(height=330,margin=dict(l=10,r=10,t=55,b=10))
            st.plotly_chart(fig,use_container_width=True)

with tabs[1]:
    st.markdown("<div class='section'>🎥 Camera + Edge AI</div>",unsafe_allow_html=True)
    videos=[os.path.join(INPUT_DIR,f) for f in os.listdir(INPUT_DIR)] if os.path.isdir(INPUT_DIR) else []
    videos=[v for v in videos if v.lower().endswith((".mp4",".avi",".mov",".mkv"))]
    if videos:
        selected=st.selectbox("Camera source",sorted(videos),format_func=os.path.basename)
        st.video(selected)
    else: empty_state("Camera source","data/input/","Place an MP4/AVI/MOV camera recording here","No recorded camera input is available.")
    c=st.columns(5)
    for col,(label,key) in zip(c,[("POTHOLES","potholes"),("ROAD DAMAGE","road_damage"),("PEDESTRIAN","pedestrian"),("WATERLOGGING","waterlogging"),("VIOLATIONS","violations")]):
        with col:kpi(label,len(data[key]),"records")
    if data["camera_health"].empty: empty_state("Camera Health","output/camera_health.csv","python ai/camera_health.py","Hardware/network telemetry is not being claimed; this module measures the video processing pipeline.")
    else:
        st.markdown("#### Camera health timeline")
        st.dataframe(data["camera_health"].tail(20),width="stretch",hide_index=True)

with tabs[2]:
    st.markdown("<div class='section'>🗺️ GIS Intelligence</div>",unsafe_allow_html=True)
    map_mode=st.radio("Map layer",["Incidents","Density heatmap","Geofences"],horizontal=True)
    if map_mode=="Geofences":
        gf=data["geofence"]
        if gf.empty:
            empty_state("Geofence visualization","output/geofence_alerts.csv","python ai/geofence_alerts.py","The geofence pipeline has not generated records. Real-world zones must be configured; the dashboard will not invent school/hospital locations.")
        else:
            gm,gps=geofence_map(gf); st_folium(gm,width="100%",height=560,returned_objects=[],key="geofence_map")
            st.success(f"{len(gps)} geofence event(s) visualized")
    else:
        im,gps=incident_map(filtered,heat=map_mode=="Density heatmap")
        st_folium(im,width="100%",height=560,returned_objects=[],key="incident_map")
        if gps.empty: st.warning("No valid GPS coordinates are present in the filtered incident records.")
    a,b,c=st.columns(3)
    with a:
        kpi("HOTSPOT ZONES",len(data["hotspots"]),"generated zones")
        if data["hotspots"].empty: empty_state("Hotspot intelligence","output/incident_hotspots.csv","python ai/hotspot_detection.py","Needs incident records grouped into geographic zones.")
    with b:kpi("GEOFENCE EVENTS",len(data["geofence"]),"escalations")
    with c:kpi("GPS INCIDENTS",len(clean_gps(filtered)),"valid coordinates")
    if not data["hotspots"].empty:
        st.markdown("#### 🔥 Hotspot severity")
        h=data["hotspots"].copy()
        numcol=next((x for x in ["Hotspot_Score","Incident_Count","Total_Incidents"] if x in h),None)
        if numcol:
            fig=px.bar(h.sort_values(numcol).tail(12),x=numcol,y=h.columns[0],orientation="h",title="Highest-risk hotspot zones")
            st.plotly_chart(fig,use_container_width=True)

with tabs[3]:
    st.markdown("<div class='section'>🚦 Traffic + Vehicle Flow</div>",unsafe_allow_html=True)
    con=data["congestion"]; flow=data["vehicle_flow"]; vio=data["violations"]
    c=st.columns(4)
    vc=pd.to_numeric(con.get("Vehicle_Count",pd.Series(dtype=float)),errors="coerce").dropna() if not con.empty else pd.Series(dtype=float)
    for col,(a,b,d) in zip(c,[("PEAK VEHICLES",int(vc.max()) if len(vc) else 0,"peak"),("AVG VEHICLES",round(vc.mean(),1) if len(vc) else 0,"average"),("HIGH CONGESTION",count(con,"Congestion_Level","HIGH"),"records"),("VIOLATIONS",len(vio),"events")]):
        with col:kpi(a,b,d)
    x,y=st.columns(2)
    with x:
        if len(vc): st.plotly_chart(px.line(vc.reset_index(drop=True),title="Congestion vehicle-count trend",labels={"value":"Vehicles","index":"Observation"}),use_container_width=True)
        else: empty_state("Congestion trend","output/congestion.csv","python ai/detection.py","No vehicle-count series is available.")
    with y:
        if not flow.empty:
            cols=[x for x in flow.columns if "COUNT" in x.upper() or "VEHICLE" in x.upper()]
            if cols:
                vals={x:pd.to_numeric(flow[x],errors="coerce").fillna(0).sum() for x in cols}
                st.plotly_chart(px.bar(x=list(vals.values()),y=list(vals.keys()),orientation="h",title="Directional / vehicle flow totals"),use_container_width=True)
            else: st.dataframe(flow.tail(20),width="stretch",hide_index=True)
        else: empty_state("Vehicle flow","output/vehicle_flow.csv","python ai/vehicle_flow.py","Directional counts have not been generated.")
    if not vio.empty and "Violation" in vio:
        st.plotly_chart(px.bar(vio.Violation.astype(str).value_counts(),title="Violation breakdown"),use_container_width=True)

with tabs[4]:
    st.markdown("<div class='section'>🛣️ Road + Safety Intelligence</div>",unsafe_allow_html=True)
    modules=[("🕳️ Potholes","potholes","output/potholes/potholes.csv","python ai/pothole_detection.py"),("🛣️ Road damage","road_damage","output/road_damage/road_damage.csv","python ai/infrastructure_detection.py"),("🚶 Pedestrian risk","pedestrian","output/pedestrian_risk/pedestrian_risk.csv","python ai/pedestrian_risk.py"),("🌊 Waterlogging","waterlogging","output/waterlogging/waterlogging.csv","python ai/waterlogging_detection.py"),("🔧 Maintenance","maintenance","output/maintenance_prediction.csv","python ai/maintenance_prediction.py"),("🔗 Correlation","correlations","output/incident_correlations.csv","python ai/incident_correlation.py")]
    for i,(title,key,out,cmd) in enumerate(modules):
        if i%2==0:a,b=st.columns(2,gap="large")
        with (a if i%2==0 else b):
            st.markdown(f"#### {title}")
            df=data[key]
            if df.empty: empty_state(title,out,cmd,"The module has no generated records yet; this is a data-availability state, not a fabricated detection.")
            else:
                # Prefer a visual severity chart, retain a compact table for audit.
                sevcol=next((x for x in ["Severity","Risk_Level","Maintenance_Level","Combined_Severity"] if x in df),None)
                if sevcol:
                    vc=df[sevcol].astype(str).str.upper().value_counts()
                    st.plotly_chart(px.bar(x=vc.index,y=vc.values,title=f"{title} — severity distribution",height=260),use_container_width=True)
                st.dataframe(df.tail(8),width="stretch",hide_index=True,height=180)

with tabs[5]:
    st.markdown("<div class='section'>🚍 Fleet + Routes</div>",unsafe_allow_html=True)
    for i,(title,key,out,cmd) in enumerate([("Bus monitoring","bus_monitoring","output/bus_monitoring.csv","python ai/bus_monitoring.py"),("Route risk","route_risk","output/route_risk.csv","python ai/route_risk.py"),("Route delay","route_delay","output/route_delay.csv","python ai/route_delay.py"),("Route recommendation","recommendations","output/route_recommendation.csv","python ai/route_recommendation.py")]):
        if i%2==0:a,b=st.columns(2,gap="large")
        with (a if i%2==0 else b):
            st.markdown(f"#### {title}"); df=data[key]
            if df.empty: empty_state(title,out,cmd,"This output depends on upstream route, incident, congestion or fleet data.")
            else:
                num=next((x for x in ["Risk_Score","Route_Score","Estimated_Delay_Minutes","Delay_Minutes","Maintenance_Score"] if x in df),None)
                if num:
                    n=pd.to_numeric(df[num],errors="coerce").dropna().head(20)
                    st.plotly_chart(px.bar(x=n.values,y=list(range(len(n))),orientation="h",title=f"{title} — {num}",height=250),use_container_width=True)
                st.dataframe(df.tail(8),width="stretch",hide_index=True,height=170)

with tabs[6]:
    st.markdown("<div class='section'>🔐 Security + Data Operations</div>",unsafe_allow_html=True)
    a,b,c=st.columns(3)
    for col,(title,key,out,cmd) in zip([a,b,c],[("Security audit","security","output/security_audit.csv","python ai/security_audit.py"),("Data quality","data_quality","output/data_quality.csv","python ai/data_quality.py"),("Edge sync","sync_log","output/sync_log.csv","python ai/data_sync.py")]):
        with col:
            st.markdown(f"#### {title}")
            df=data[key]
            if df.empty: empty_state(title,out,cmd,"No records have been generated by this module yet.")
            else:
                kpi("RECORDS",len(df),"audit/output rows")
                st.dataframe(df.tail(8),width="stretch",hide_index=True,height=220)

with tabs[7]:
    st.markdown("<div class='section'>📋 Evidence + Vehicle Database</div>",unsafe_allow_html=True)
    reg=data["registry"]
    if reg.empty: empty_state("Vehicle registry / ANPR","output/vehicle_registry/vehicle_registry.csv","python ai/vehicle_registry.py","The registry only populates when incident records contain usable registration/plate fields. No plate values are invented.")
    else: st.dataframe(reg.tail(20),width="stretch",hide_index=True)
    evidence=[]
    if not filtered.empty and "Evidence" in filtered:
        for e in filtered.Evidence:
            if txt(e,"") not in ("","N/A","nan"):
                p=str(e) if os.path.isabs(str(e)) else os.path.join(BASE_DIR,str(e))
                if os.path.exists(p): evidence.append(p)
    if evidence:
        chosen=st.selectbox("Evidence inspector",evidence,format_func=os.path.basename)
        st.image(chosen,width="stretch")
    else: st.info("No evidence image exists for the currently filtered incidents.")
    st.markdown("#### Incident database")
    st.dataframe(filtered.tail(40).iloc[::-1] if not filtered.empty else pd.DataFrame({"Status":["No incidents match filters"]}),width="stretch",hide_index=True,height=350)
