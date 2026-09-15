import os
from datetime import datetime
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
    "incidents":"incidents.csv","alerts":"alerts.csv","congestion":"congestion.csv","violations":"violations.csv",
    "potholes":"potholes/potholes.csv","road_damage":"road_damage/road_damage.csv","pedestrian":"pedestrian_risk/pedestrian_risk.csv",
    "waterlogging":"waterlogging/waterlogging.csv","route_risk":"route_risk.csv","hotspots":"incident_hotspots.csv",
    "bus_monitoring":"bus_monitoring.csv","route_delay":"route_delay.csv","vehicle_flow":"vehicle_flow.csv",
    "camera_health":"camera_health.csv","sync_log":"sync_log.csv","registry":"vehicle_registry/vehicle_registry.csv",
    "maintenance":"maintenance_prediction.csv","correlations":"incident_correlations.csv","recommendations":"route_recommendation.csv",
    "security":"security_audit.csv","data_quality":"data_quality.csv","geofence":"geofence_alerts.csv",
}

@st.cache_data(ttl=3)
def load_csv(name):
    path=os.path.join(OUTPUT_DIR,name)
    if not os.path.exists(path): return pd.DataFrame()
    try: return pd.read_csv(path)
    except Exception: return pd.DataFrame()

data={k:load_csv(v) for k,v in FILES.items()}
incidents=data["incidents"]
alerts=data["alerts"]

PALETTE={
    "violet":"#7C5CFC","cyan":"#35C2FF","mint":"#4FD1A1","pink":"#F472B6",
    "amber":"#F6B73C","coral":"#FB7185","blue":"#5B8DEF","indigo":"#6366F1",
    "slate":"#64748B","danger":"#EF5B6B","dark":"#18243A"
}

CSS="""
<style>
:root{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.stApp{background:#f6f8fc;color:#172033}
.block-container{max-width:1540px;padding:1.15rem 1.8rem 3rem}
section[data-testid="stSidebar"]{background:#101827;border-right:1px solid #253149}
section[data-testid="stSidebar"] *{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif!important}
section[data-testid="stSidebar"] label{color:#9eacc2!important;font-size:11px!important;font-weight:700!important;letter-spacing:.25px}
section[data-testid="stSidebar"] [data-baseweb="select"]>div{background:#1b273b!important;border:1px solid #34445d!important;border-radius:10px!important;min-height:42px}
section[data-testid="stSidebar"] [data-baseweb="select"] *{color:#f4f7fb!important}
section[data-testid="stSidebar"] [data-baseweb="select"] svg{fill:#9fb0c9!important}
section[data-testid="stSidebar"] [data-testid="stRadio"] label{color:#dbe5f4!important;background:transparent;border-radius:9px;padding:7px 9px}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:#1d2a40}
section[data-testid="stSidebar"] .stButton button{background:#273651!important;color:#fff!important;border:1px solid #415371!important;border-radius:10px!important;font-weight:750!important}
section[data-testid="stSidebar"] .stButton button:hover{background:#314362!important;border-color:#5b70a0!important}
[data-baseweb="popover"]{background:#172238!important}
[data-baseweb="popover"] *{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif!important}
.hero{background:radial-gradient(circle at 86% 15%,rgba(124,92,252,.30),transparent 25%),radial-gradient(circle at 10% 90%,rgba(53,194,255,.16),transparent 27%),linear-gradient(135deg,#111b31,#27385f);border-radius:22px;padding:27px 31px;color:#fff;box-shadow:0 15px 40px rgba(20,34,62,.13);margin-bottom:19px}
.hero h1{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:30px;line-height:1.15;font-weight:800;letter-spacing:-.7px;color:#fff}
.hero p{margin:8px 0 0;color:#c8d4e7;font-size:13px}
.pill{display:inline-block;margin:14px 6px 0 0;padding:6px 10px;border-radius:999px;background:rgba(255,255,255,.09);color:#eaf1fb;font-size:10px;font-weight:750}.live{color:#7ff0bd!important}
.kpi{background:#fff;border:1px solid #e3e8f1;border-radius:15px;padding:15px 16px;min-height:101px;box-shadow:0 5px 18px rgba(26,42,70,.045)}
.kpi-label{color:#718096;font-size:10px;font-weight:800;letter-spacing:.55px}.kpi-value{color:#172033;font-size:26px;font-weight:800;margin-top:7px}.kpi-note{color:#98a4b6;font-size:10px;margin-top:4px}
.section{font-size:23px;font-weight:800;color:#172033;margin:7px 0 5px;letter-spacing:-.35px}.sub{font-size:13px;color:#718096;margin:0 0 16px}
.empty-card{background:#fff;border:1px dashed #c9d3e2;border-radius:15px;padding:16px;margin:6px 0 13px}.empty-title{font-weight:800;color:#344157}.empty-title span{float:right;font-size:9px;color:#9a6509;background:#fff7e8;padding:5px 8px;border-radius:999px}.empty-text{color:#64748b;font-size:12px;margin:8px 0}.empty-code,.empty-run{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace!important;font-size:10px;background:#f6f8fb;border-radius:7px;padding:8px;margin-top:6px;color:#526174}.empty-run{color:#536bff}
.module-title{font-size:23px;font-weight:800;line-height:1.2;color:#172033;letter-spacing:-.3px;margin:2px 0 7px}.side-brand{padding:5px 2px 13px}.side-brand b{font-size:18px;color:#fff}.side-brand small{display:block;color:#8fa0ba;margin-top:3px;font-size:10px}.side-card{background:#19263b;border:1px solid #30415d;border-radius:13px;padding:13px;margin:9px 0 15px}.side-status{font-size:10px;font-weight:800;color:#7ff0bd}.side-big{font-size:22px;font-weight:800;color:#fff;margin-top:4px}.side-small{font-size:10px;color:#92a3bd}.nav-title{font-size:10px;color:#788aa6;font-weight:800;letter-spacing:1px;margin:13px 0 6px}
/* Keep Streamlit's native typography; only tighten the data surface. */
div[data-testid="stDataFrame"]{border:1px solid #dfe5ee!important;border-radius:12px!important;overflow:hidden!important;background:#fff!important;box-shadow:0 4px 14px rgba(20,34,62,.035)!important}
div[data-testid="stDataFrame"] [role="columnheader"]{background:#f5f7fb!important;color:#4b5870!important;font-weight:750!important}
div[data-testid="stDataFrame"] [role="gridcell"]{color:#263247!important}
div[data-testid="stDataFrame"] [role="row"]{border-bottom:1px solid #edf1f6!important}
.stButton button{border-radius:10px;font-weight:700}

.pipeline{background:#fff;border:1px solid #e1e7f0;border-radius:18px;padding:18px 18px 15px;margin:4px 0 18px;box-shadow:0 5px 18px rgba(26,42,70,.04)}
.pipeline-head{font-size:11px;font-weight:800;letter-spacing:.7px;color:#718096;margin-bottom:12px}.pipeline-flow{display:flex;align-items:stretch;gap:8px}.pipeline-node{flex:1;min-width:0;background:#f7f9fd;border:1px solid #e1e7f0;border-radius:13px;padding:12px 10px;text-align:center}.pipeline-icon{font-size:22px}.pipeline-name{font-size:11px;font-weight:800;color:#253149;margin-top:7px}.pipeline-detail{font-size:9px;color:#8290a5;margin-top:3px}.pipeline-arrow{align-self:center;color:#8b9ab0;font-size:18px;font-weight:800}.pipeline-node.edge{background:#f5f3ff;border-color:#d9d1ff}.pipeline-node.central{background:#f0faff;border-color:#c9eafa}.pipeline-node.output{background:#f0fbf6;border-color:#ccefe0}@media(max-width:900px){.pipeline-flow{flex-wrap:wrap}.pipeline-arrow{display:none}.pipeline-node{min-width:30%}}
footer{visibility:hidden}
</style>
"""
st.markdown(CSS,unsafe_allow_html=True)


def txt(v,default="N/A"):
    if v is None:return default
    try:
        if pd.isna(v):return default
    except Exception:pass
    return str(v)

def count(df,col,value):
    if df.empty or col not in df.columns:return 0
    return int(df[col].astype(str).str.upper().eq(str(value).upper()).sum())

def clean_gps(df):
    if df.empty or not {"Latitude","Longitude"}.issubset(df.columns):return pd.DataFrame()
    x=df.copy();x["Latitude"]=pd.to_numeric(x["Latitude"],errors="coerce");x["Longitude"]=pd.to_numeric(x["Longitude"],errors="coerce")
    x=x.dropna(subset=["Latitude","Longitude"])
    return x[x.Latitude.between(-90,90)&x.Longitude.between(-180,180)]

def kpi(label,value,note=""):
    st.markdown(f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div><div class='kpi-note'>{note}</div></div>",unsafe_allow_html=True)

def empty_state(title,output,command,reason):
    st.markdown(f"<div class='empty-card'><div class='empty-title'>{title} <span>NO RECORDS</span></div><div class='empty-text'>{reason}</div><div class='empty-code'>{output}</div><div class='empty-run'>▶ {command}</div></div>",unsafe_allow_html=True)

def plot(fig,height=330):
    fig.update_layout(
        height=height, margin=dict(l=12,r=14,t=82,b=14),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif",color="#42516a",size=11),
        title=dict(font=dict(size=18,color="#172033",family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif"),x=0.0,xanchor="left",y=0.98,yanchor="top"),
        legend=dict(orientation="h",yanchor="bottom",y=1.16,x=0,font=dict(size=11,color="#526174")),
        hoverlabel=dict(bgcolor="#172033",font=dict(color="#fff",size=11)),
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=False,showline=True,linecolor="#e1e6ee",tickfont=dict(color="#68758a",size=10),title_font=dict(color="#526174",size=10))
    fig.update_yaxes(showgrid=True,gridcolor="#edf1f6",zeroline=False,showline=False,tickfont=dict(color="#68758a",size=10),title_font=dict(color="#526174",size=10))
    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False,"responsive":True})

def severity_color(s):
    return {"CRITICAL":"#9F1239","HIGH":"#EF5B6B","MEDIUM":"#F6B73C","LOW":"#4FD1A1"}.get(str(s).upper(),"#7C5CFC")

def incident_map(df,heat=False):
    gps=clean_gps(df)
    if gps.empty:m=folium.Map(location=[22.7196,75.8577],zoom_start=12,tiles="OpenStreetMap",control_scale=True);return m,gps
    m=folium.Map(location=[gps.Latitude.mean(),gps.Longitude.mean()],zoom_start=13,tiles="OpenStreetMap",control_scale=True)
    pts=[]
    for _,r in gps.iterrows():
        sev=txt(r.get("Severity","LOW")).upper();lat=float(r.Latitude);lon=float(r.Longitude)
        pts.append([lat,lon,{"CRITICAL":1.3,"HIGH":1,"MEDIUM":.65,"LOW":.35}.get(sev,.5)])
        folium.CircleMarker([lat,lon],radius=7,color=severity_color(sev),fill=True,fill_color=severity_color(sev),fill_opacity=.85,
            popup=folium.Popup(f"<b>{txt(r.get('Type','INCIDENT'))}</b><br>Severity: {sev}<br>Object: {txt(r.get('Object_Type'))}<br>Confidence: {txt(r.get('Confidence'))}<br>Time: {txt(r.get('Video_Time'))}",max_width=300)).add_to(m)
    if heat and pts:HeatMap(pts,radius=28,blur=20,min_opacity=.3).add_to(m)
    return m,gps

def geofence_map(df):
    gps=clean_gps(df)
    if gps.empty:m=folium.Map(location=[22.7196,75.8577],zoom_start=12,tiles="OpenStreetMap");return m,gps
    m=folium.Map(location=[gps.Latitude.mean(),gps.Longitude.mean()],zoom_start=13,tiles="OpenStreetMap",control_scale=True)
    for _,r in gps.iterrows():
        sev=txt(r.get("Escalated_Severity",r.get("Severity","LOW"))).upper();name=txt(r.get("Geofence",r.get("Zone",r.get("Geofence_Name","Configured Zone"))))
        folium.Circle([float(r.Latitude),float(r.Longitude)],radius=120,color=severity_color(sev),fill=True,fill_color=severity_color(sev),fill_opacity=.10).add_to(m)
        folium.Marker([float(r.Latitude),float(r.Longitude)],tooltip=name,popup=f"<b>{name}</b><br>Severity: {sev}<br>Incident: {txt(r.get('Incident_Type',r.get('Type')))}").add_to(m)
    return m,gps

# Sidebar — feature selector + global filters
with st.sidebar:
    st.markdown("<div class='side-brand'><b>🚍 Urban AI</b><small>Smart mobility command center</small></div>",unsafe_allow_html=True)
    available=sum(not d.empty for d in data.values())
    st.markdown(f"<div class='side-card'><div class='side-status'>● SYSTEM ONLINE</div><div class='side-big'>{available}/{len(data)}</div><div class='side-small'>output datasets currently populated</div></div>",unsafe_allow_html=True)

    pages=["🚨 Command Center","🎥 Camera & Edge AI","🗺️ GIS Intelligence","🚦 Traffic & Flow","🛣️ Road & Safety","🚍 Fleet & Routes","🔐 Security & Data","📋 Evidence & Database"]
    st.markdown("<div class='nav-title'>FEATURE SELECT</div>",unsafe_allow_html=True)
    page=st.selectbox("Feature",pages,label_visibility="collapsed",key="feature_select")

    st.markdown("<div class='nav-title'>GLOBAL FILTERS</div>",unsafe_allow_html=True)
    types=["ALL"]+(sorted(incidents.Type.dropna().astype(str).unique().tolist()) if not incidents.empty and "Type" in incidents else [])
    selected_type=st.selectbox("Incident type",types,key="incident_type")
    selected_severity=st.selectbox("Severity",["ALL","CRITICAL","HIGH","MEDIUM","LOW"],key="severity")

    st.markdown("<div class='nav-title'>SYSTEM</div>",unsafe_allow_html=True)
    if st.button("↻  Refresh all data",width="stretch"):
        st.cache_data.clear();st.rerun()
    st.progress(available/len(data) if data else 0)
    st.caption(f"Coverage  •  {available}/{len(data)} outputs")
    st.caption(datetime.now().strftime("Updated  •  %d %b %Y  %H:%M"))

filtered=incidents.copy()
if not filtered.empty and selected_type!="ALL" and "Type" in filtered:filtered=filtered[filtered.Type.astype(str)==selected_type]
if not filtered.empty and selected_severity!="ALL" and "Severity" in filtered:filtered=filtered[filtered.Severity.astype(str).str.upper()==selected_severity]

now=datetime.now().strftime("%d %b %Y • %H:%M")
st.markdown(f"<div class='hero'><h1>🚍 Urban AI Command Center</h1><p>Edge AI → GIS → centralized alerts → fleet intelligence → evidence.</p><span class='pill live'>● CONTROL ROOM</span><span class='pill'>EDGE AI</span><span class='pill'>GIS</span><span class='pill'>ANPR</span><span class='pill'>CENTRAL ALERTS</span><span class='pill'>{now}</span></div>",unsafe_allow_html=True)

# COMMAND
if page==pages[0]:
    st.markdown("<div class='section'>Operations Overview</div><div class='sub'>A live-style operational view of the records currently generated by your prototype.</div>",unsafe_allow_html=True)
    c=st.columns(6)
    metrics=[("CRITICAL",count(alerts,"Alert_Level","CRITICAL"),"immediate"),("WARNINGS",count(alerts,"Alert_Level","WARNING"),"review"),("INCIDENTS",len(filtered),"filtered events"),("HIGH",count(filtered,"Severity","HIGH"),"priority hazards"),("VIOLATIONS",len(data["violations"]),"traffic events"),("DATASETS",available,f"of {len(data)}")]
    for col,(a,b,d) in zip(c,metrics):
        with col:kpi(a,b,d)

    st.markdown("""<div class='pipeline'><div class='pipeline-head'>END-TO-END INTELLIGENCE PIPELINE</div><div class='pipeline-flow'><div class='pipeline-node'><div class='pipeline-icon'>🎥</div><div class='pipeline-name'>BUS CAMERA</div><div class='pipeline-detail'>Video / IP camera input</div></div><div class='pipeline-arrow'>→</div><div class='pipeline-node edge'><div class='pipeline-icon'>🤖</div><div class='pipeline-name'>EDGE AI</div><div class='pipeline-detail'>YOLO • detection • tracking</div></div><div class='pipeline-arrow'>→</div><div class='pipeline-node edge'><div class='pipeline-icon'>🚨</div><div class='pipeline-name'>INCIDENT ENGINE</div><div class='pipeline-detail'>Risk • severity • evidence</div></div><div class='pipeline-arrow'>→</div><div class='pipeline-node central'><div class='pipeline-icon'>🗺️</div><div class='pipeline-name'>CENTRAL INTELLIGENCE</div><div class='pipeline-detail'>GIS • alerts • fleet • analytics</div></div><div class='pipeline-arrow'>→</div><div class='pipeline-node output'><div class='pipeline-icon'>👮</div><div class='pipeline-name'>RESPONSE</div><div class='pipeline-detail'>Prioritize • investigate • maintain</div></div></div></div>""",unsafe_allow_html=True)
    a,b=st.columns([1,1.25],gap="large")
    with a:
        if alerts.empty:empty_state("Central alerts","output/alerts.csv","python ai/alert_engine.py","Generate alerts from incidents before this panel can display priority distribution.")
        else:
            ac=alerts.Alert_Level.astype(str).value_counts().reset_index();ac.columns=["level","count"]
            fig=px.pie(ac,names="level",values="count",hole=.62,title="Alert priority mix",color_discrete_sequence=[PALETTE["coral"],PALETTE["amber"],PALETTE["mint"],PALETTE["violet"]]);fig.update_traces(textposition="inside",textinfo="percent+label");plot(fig,340)
    with b:
        if filtered.empty:st.info("No incidents match the current filters.")
        elif "Type" in filtered:
            vc=filtered.Type.astype(str).value_counts().sort_values();fig=px.bar(x=vc.values,y=vc.index,orientation="h",title="Incident mix",labels={"x":"Events","y":"Incident type"},color=vc.values,color_continuous_scale=[PALETTE["cyan"],PALETTE["violet"]]);plot(fig,340)

# CAMERA
elif page==pages[1]:
    st.markdown("<div class='section'>🎥 Camera + Edge AI</div><div class='sub'>Recorded camera inputs and the AI outputs they currently feed.</div>",unsafe_allow_html=True)
    videos=[os.path.join(INPUT_DIR,f) for f in os.listdir(INPUT_DIR)] if os.path.isdir(INPUT_DIR) else []
    videos=[v for v in videos if v.lower().endswith((".mp4",".avi",".mov",".mkv"))]
    if videos:
        selected=st.selectbox("Camera source",sorted(videos),format_func=os.path.basename);st.video(selected)
    else:empty_state("Camera source","data/input/","Place an MP4/AVI/MOV camera recording here","No recorded camera input is available.")
    c=st.columns(5)
    for col,(label,key) in zip(c,[("POTHOLES","potholes"),("ROAD DAMAGE","road_damage"),("PEDESTRIAN","pedestrian"),("WATERLOGGING","waterlogging"),("VIOLATIONS","violations")]):
        with col:kpi(label,len(data[key]),"records")
    if data["camera_health"].empty:empty_state("Camera health","output/camera_health.csv","python ai/camera_health.py","This prototype measures the video processing pipeline; it does not claim hardware telemetry.")
    else:
        ch=data["camera_health"];num=next((x for x in ["Processing_FPS","Source_FPS","FPS"] if x in ch),None)
        if num:
            vals=pd.to_numeric(ch[num],errors="coerce").dropna();fig=px.line(x=range(len(vals)),y=vals,title=f"{num} over observations",labels={"x":"Observation","y":num});fig.update_traces(line=dict(color=PALETTE["cyan"],width=3));plot(fig,300)
        st.dataframe(ch.tail(12),width="stretch",hide_index=True)

# GIS
elif page==pages[2]:
    st.markdown("<div class='section'>🗺️ GIS Intelligence</div><div class='sub'>Spatial incidents, density, hotspots and configured geofence events.</div>",unsafe_allow_html=True)
    map_mode=st.radio("Map layer",["Incidents","Density heatmap","Geofences"],horizontal=True)
    if map_mode=="Geofences":
        gf=data["geofence"]
        if gf.empty:empty_state("Geofence visualization","output/geofence_alerts.csv","python ai/geofence_alerts.py","The geofence pipeline has no records. The dashboard does not invent real school/hospital locations; zones must be configured in the module.")
        else:gm,gps=geofence_map(gf);st_folium(gm,width="100%",height=570,returned_objects=[],key="gfmap");st.success(f"{len(gps)} geofence event(s) visualized")
    else:
        im,gps=incident_map(filtered,heat=map_mode=="Density heatmap");st_folium(im,width="100%",height=570,returned_objects=[],key="imap")
        if gps.empty:st.warning("No valid GPS coordinates are present in the filtered incident records.")
    a,b,c=st.columns(3); 
    with a:kpi("HOTSPOT ZONES",len(data["hotspots"]),"generated zones")
    with b:kpi("GEOFENCE EVENTS",len(data["geofence"]),"escalations")
    with c:kpi("GPS INCIDENTS",len(clean_gps(filtered)),"valid coordinates")
    if not data["hotspots"].empty:
        h=data["hotspots"].copy();num=next((x for x in ["Hotspot_Score","Incident_Count","Total_Incidents"] if x in h),None)
        if num:
            y=next((x for x in h.columns if x not in [num] and h[x].dtype=="object"),h.columns[0]);hh=h.sort_values(num).tail(12);fig=px.bar(hh,x=num,y=y,orientation="h",title="Highest-risk hotspot zones",color=num,color_continuous_scale=[PALETTE["cyan"],PALETTE["violet"]]);plot(fig,350)
    else:empty_state("Hotspot intelligence","output/incident_hotspots.csv","python ai/hotspot_detection.py","Needs incident records grouped into geographic zones.")

# TRAFFIC
elif page==pages[3]:
    st.markdown("<div class='section'>🚦 Traffic + Vehicle Flow</div><div class='sub'>Traffic volume, violations and directional movement.</div>",unsafe_allow_html=True)
    con=data["congestion"];flow=data["vehicle_flow"];vio=data["violations"]
    vc=pd.to_numeric(con.get("Vehicle_Count",pd.Series(dtype=float)),errors="coerce").dropna() if not con.empty else pd.Series(dtype=float)
    c=st.columns(4)
    for col,(a,b,d) in zip(c,[("PEAK VEHICLES",int(vc.max()) if len(vc) else 0,"peak"),("AVG VEHICLES",round(vc.mean(),1) if len(vc) else 0,"average"),("HIGH CONGESTION",count(con,"Congestion_Level","HIGH"),"records"),("VIOLATIONS",len(vio),"events")]):
        with col:kpi(a,b,d)
    a,b=st.columns(2,gap="large")
    with a:
        if len(vc):
            fig=px.area(x=list(range(len(vc))),y=vc,title="Vehicle volume trend",labels={"x":"Observation","y":"Vehicles"});fig.update_traces(line_color=PALETTE["violet"],fillcolor="rgba(124,92,252,.13)");plot(fig,330)
        else:empty_state("Congestion trend","output/congestion.csv","python ai/detection.py","No vehicle-count series is available.")
    with b:
        if not flow.empty:
            cols=[x for x in flow.columns if "COUNT" in x.upper() or "VEHICLE" in x.upper()];vals={x:pd.to_numeric(flow[x],errors="coerce").fillna(0).sum() for x in cols}
            if vals:
                fig=px.bar(x=list(vals.values()),y=list(vals.keys()),orientation="h",title="Vehicle flow totals",labels={"x":"Vehicles","y":"Flow metric"},color=list(vals.values()),color_continuous_scale=[PALETTE["mint"],PALETTE["cyan"]]);plot(fig,330)
            else:st.dataframe(flow.tail(20),width="stretch",hide_index=True)
        else:empty_state("Vehicle flow","output/vehicle_flow.csv","python ai/vehicle_flow.py","Directional counts have not been generated.")
    if not vio.empty and "Violation" in vio:
        vv=vio.Violation.astype(str).value_counts().reset_index();vv.columns=["type","count"];fig=px.bar(vv,x="type",y="count",title="Violation breakdown",color="count",color_continuous_scale=[PALETTE["amber"],PALETTE["coral"]]);plot(fig,300)

# ROAD
elif page==pages[4]:
    st.markdown("<div class='section'>🛣️ Road + Safety Intelligence</div><div class='sub'>Road condition, pedestrian exposure, waterlogging and maintenance signals.</div>",unsafe_allow_html=True)
    modules=[("🕳️ Potholes","potholes","output/potholes/potholes.csv","python ai/pothole_detection.py"),("🛣️ Road damage","road_damage","output/road_damage/road_damage.csv","python ai/infrastructure_detection.py"),("🚶 Pedestrian risk","pedestrian","output/pedestrian_risk/pedestrian_risk.csv","python ai/pedestrian_risk.py"),("🌊 Waterlogging","waterlogging","output/waterlogging/waterlogging.csv","python ai/waterlogging_detection.py"),("🔧 Maintenance","maintenance","output/maintenance_prediction.csv","python ai/maintenance_prediction.py"),("🔗 Correlation","correlations","output/incident_correlations.csv","python ai/incident_correlation.py")]
    for i,(title,key,out,cmd) in enumerate(modules):
        if i%2==0:a,b=st.columns(2,gap="large")
        with (a if i%2==0 else b):
            st.markdown(f"<div class='module-title'>{title}</div>",unsafe_allow_html=True);df=data[key]
            if df.empty:empty_state(title,out,cmd,"This module has no generated records yet. Empty output is shown honestly rather than fabricating detections.")
            else:
                sev=next((x for x in ["Severity","Risk_Level","Maintenance_Level","Combined_Severity"] if x in df),None)
                if sev:
                    vv=df[sev].astype(str).str.upper().value_counts().reset_index();vv.columns=["level","count"];fig=px.bar(vv,x="level",y="count",title="Severity / risk profile",color="level",color_discrete_sequence=[PALETTE["mint"],PALETTE["amber"],PALETTE["coral"],PALETTE["violet"]]);plot(fig,270)
                st.dataframe(df.tail(8),width="stretch",hide_index=True,height=190)

# FLEET
elif page==pages[5]:
    st.markdown("<div class='section'>🚍 Fleet + Routes</div><div class='sub'>Fleet health, route risk, delay and route decision support.</div>",unsafe_allow_html=True)
    modules=[("Bus monitoring","bus_monitoring","output/bus_monitoring.csv","python ai/bus_monitoring.py"),("Route risk","route_risk","output/route_risk.csv","python ai/route_risk.py"),("Route delay","route_delay","output/route_delay.csv","python ai/route_delay.py"),("Route recommendation","recommendations","output/route_recommendation.csv","python ai/route_recommendation.py")]
    for i,(title,key,out,cmd) in enumerate(modules):
        if i%2==0:a,b=st.columns(2,gap="large")
        with (a if i%2==0 else b):
            st.markdown(f"<div class='module-title'>{title}</div>",unsafe_allow_html=True);df=data[key]
            if df.empty:empty_state(title,out,cmd,"This output depends on upstream incident, congestion, route or fleet data.")
            else:
                num=next((x for x in ["Risk_Score","Route_Score","Estimated_Delay_Minutes","Delay_Minutes","Maintenance_Score"] if x in df),None)
                if num:
                    n=pd.to_numeric(df[num],errors="coerce").dropna();fig=px.bar(x=n.values,y=[str(i+1) for i in range(len(n))],orientation="h",title=num,labels={"x":num,"y":"Record"},color=n.values,color_continuous_scale=[PALETTE["cyan"],PALETTE["violet"]]);plot(fig,270)
                st.dataframe(df.tail(8),width="stretch",hide_index=True,height=180)

# SECURITY
elif page==pages[6]:
    st.markdown("<div class='section'>🔐 Security + Data Operations</div><div class='sub'>Integrity, data quality and edge-to-central synchronization.</div>",unsafe_allow_html=True)
    a,b,c=st.columns(3)
    for col,(title,key,out,cmd) in zip([a,b,c],[("Security audit","security","output/security_audit.csv","python ai/security_audit.py"),("Data quality","data_quality","output/data_quality.csv","python ai/data_quality.py"),("Edge sync","sync_log","output/sync_log.csv","python ai/data_sync.py")]):
        with col:
            st.markdown(f"<div class='module-title'>{title}</div>",unsafe_allow_html=True);df=data[key]
            if df.empty:empty_state(title,out,cmd,"No records have been generated by this module yet.")
            else:
                kpi("RECORDS",len(df),"output rows")
                # visualise the first useful numeric field
                nums=[x for x in df.columns if pd.api.types.is_numeric_dtype(df[x])]
                if nums:
                    n=nums[0];vals=pd.to_numeric(df[n],errors="coerce").dropna();fig=px.line(x=list(range(len(vals))),y=vals,title=n,labels={"x":"Observation","y":n});fig.update_traces(line_color=PALETTE["cyan"],line_width=3);plot(fig,220)
                st.dataframe(df.tail(7),width="stretch",hide_index=True,height=190)

# EVIDENCE
else:
    st.markdown("<div class='section'>📋 Evidence + Vehicle Database</div><div class='sub'>Audit records, evidence images and registration history.</div>",unsafe_allow_html=True)
    reg=data["registry"]
    if reg.empty:empty_state("Vehicle registry / ANPR","output/vehicle_registry/vehicle_registry.csv","python ai/vehicle_registry.py","The registry only populates when incident records contain usable registration fields. No plate values are invented.")
    else:st.dataframe(reg.tail(20),width="stretch",hide_index=True)
    evidence=[]
    if not filtered.empty and "Evidence" in filtered:
        for e in filtered.Evidence:
            p=str(e) if os.path.isabs(str(e)) else os.path.join(BASE_DIR,str(e))
            if txt(e,"") not in ("","N/A","nan") and os.path.exists(p):evidence.append(p)
    if evidence:
        chosen=st.selectbox("Evidence inspector",evidence,format_func=os.path.basename);st.image(chosen,width="stretch")
    else:st.info("No evidence image exists for the currently filtered incidents.")
    st.markdown("#### Incident database")
    st.dataframe(filtered.tail(40).iloc[::-1] if not filtered.empty else pd.DataFrame({"Status":["No incidents match filters"]}),width="stretch",hide_index=True,height=370)
