import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Urban Sensing Platform",
    page_icon="🚌",
    layout="wide"
)

PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

INCIDENT_CSV = os.path.join(
    PROJECT_DIR,
    "output",
    "incidents.csv"
)


# ============================================================
# TITLE
# ============================================================

st.title("🚌 AI Urban Sensing Platform")

st.markdown(
    """
    **AI-powered onboard + centralized urban monitoring system**

    Detecting road hazards, potholes and traffic violations
    from camera feeds.
    """
)


# ============================================================
# LOAD DATA
# ============================================================

if not os.path.exists(INCIDENT_CSV):

    st.error(
        "incidents.csv was not found."
    )

    st.stop()


df = pd.read_csv(INCIDENT_CSV)


if df.empty:

    st.warning(
        "No incidents have been detected yet."
    )

    st.stop()


# ============================================================
# CLEAN DATA
# ============================================================

df["Type"] = df["Type"].fillna("UNKNOWN")

df["Severity"] = df["Severity"].fillna("UNKNOWN")

df["Confidence"] = pd.to_numeric(
    df["Confidence"],
    errors="coerce"
)

df["Latitude"] = pd.to_numeric(
    df["Latitude"],
    errors="coerce"
)

df["Longitude"] = pd.to_numeric(
    df["Longitude"],
    errors="coerce"
)


# ============================================================
# METRICS
# ============================================================

total_incidents = len(df)

potholes = len(
    df[
        df["Type"].str.upper() == "POTHOLE"
    ]
)

wrong_way = len(
    df[
        df["Type"].str.upper() == "WRONG_WAY"
    ]
)

high_severity = len(
    df[
        df["Severity"].str.upper() == "HIGH"
    ]
)


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Incidents",
        total_incidents
    )

with col2:
    st.metric(
        "🚧 Potholes",
        potholes
    )

with col3:
    st.metric(
        "🚨 Wrong Way",
        wrong_way
    )

with col4:
    st.metric(
        "🔴 High Severity",
        high_severity
    )


st.divider()


# ============================================================
# INCIDENT BREAKDOWN
# ============================================================

st.subheader("📊 Incident Analytics")

col1, col2 = st.columns(2)

with col1:

    type_counts = (
        df["Type"]
        .value_counts()
    )

    st.bar_chart(
        type_counts
    )


with col2:

    severity_counts = (
        df["Severity"]
        .value_counts()
    )

    st.bar_chart(
        severity_counts
    )


st.divider()


# ============================================================
# GIS MAP
# ============================================================

st.subheader("🗺️ GIS Incident Map")

st.caption(
    "Incident locations from the centralized AI event log."
)


# ------------------------------------------------------------
# Currently your videos don't provide real GPS coordinates.
# Use a demonstration center for the map.
# ------------------------------------------------------------

DEFAULT_LAT = 23.83
DEFAULT_LON = 80.40


map_df = df.dropna(
    subset=[
        "Latitude",
        "Longitude"
    ]
).copy()


# ------------------------------------------------------------
# MAP
# ------------------------------------------------------------

m = folium.Map(
    location=[
        DEFAULT_LAT,
        DEFAULT_LON
    ],
    zoom_start=12
)


# ------------------------------------------------------------
# INCIDENT MARKERS
# ------------------------------------------------------------

for _, row in map_df.iterrows():

    incident_type = str(
        row["Type"]
    ).upper()

    severity = str(
        row["Severity"]
    ).upper()

    if incident_type == "POTHOLE":

        marker_color = "red"

        icon_symbol = "🚧"

    elif incident_type == "WRONG_WAY":

        marker_color = "orange"

        icon_symbol = "🚨"

    else:

        marker_color = "blue"

        icon_symbol = "⚠️"


    popup_text = f"""
    <b>{icon_symbol} {incident_type}</b><br>
    <b>Incident ID:</b> {row['Incident_ID']}<br>
    <b>Object:</b> {row['Object_Type']}<br>
    <b>Severity:</b> {severity}<br>
    <b>Confidence:</b> {row['Confidence']}<br>
    <b>Time:</b> {row['Video_Time']}<br>
    """

    folium.Marker(
        location=[
            row["Latitude"],
            row["Longitude"]
        ],
        popup=folium.Popup(
            popup_text,
            max_width=300
        ),
        tooltip=(
            f"{incident_type} | "
            f"{severity}"
        ),
        icon=folium.Icon(
            color=marker_color,
            icon="warning-sign"
        )
    ).add_to(m)


# ------------------------------------------------------------
# SHOW MAP
# ------------------------------------------------------------

st_folium(
    m,
    width=None,
    height=550
)


# ============================================================
# HEATMAP
# ============================================================

st.subheader("🔥 Incident Heatmap")

if len(map_df) > 0:

    heat_data = [
        [
            row["Latitude"],
            row["Longitude"],
            1
        ]
        for _, row in map_df.iterrows()
    ]

    heat_map = folium.Map(
        location=[
            DEFAULT_LAT,
            DEFAULT_LON
        ],
        zoom_start=12
    )

    HeatMap(
        heat_data,
        radius=25,
        blur=20,
        max_zoom=15
    ).add_to(
        heat_map
    )

    st_folium(
        heat_map,
        width=None,
        height=500
    )

else:

    st.info(
        "GPS coordinates are currently unavailable. "
        "The map will populate automatically when "
        "real GPS coordinates are connected."
    )


st.divider()


# ============================================================
# INCIDENT TABLE
# ============================================================

st.subheader("🚨 Recent Incidents")

display_df = df[
    [
        "Incident_ID",
        "Type",
        "Object_ID",
        "Object_Type",
        "Severity",
        "Confidence",
        "Video_Time",
        "Latitude",
        "Longitude",
        "Evidence"
    ]
].copy()


st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# EVIDENCE VIEWER
# ============================================================

st.divider()

st.subheader("📸 Evidence Viewer")


incident_ids = df[
    "Incident_ID"
].astype(str).tolist()


selected_id = st.selectbox(
    "Select an incident",
    incident_ids
)


selected_row = df[
    df["Incident_ID"].astype(str)
    == selected_id
].iloc[0]


st.write(
    f"**Type:** {selected_row['Type']}"
)

st.write(
    f"**Severity:** {selected_row['Severity']}"
)

st.write(
    f"**Confidence:** {selected_row['Confidence']}"
)

st.write(
    f"**Video Time:** {selected_row['Video_Time']}"
)


# ------------------------------------------------------------
# EVIDENCE PATH
# ------------------------------------------------------------

evidence_path = str(
    selected_row["Evidence"]
)


# Handle paths stored by detector
if not os.path.isabs(evidence_path):

    evidence_path = os.path.join(
        PROJECT_DIR,
        evidence_path
    )


if os.path.exists(evidence_path):

    st.image(
        evidence_path,
        caption=(
            f"Evidence — "
            f"{selected_row['Type']}"
        ),
        use_container_width=True
    )

else:

    st.warning(
        "Evidence image not found:"
    )

    st.code(
        evidence_path
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "AI Urban Sensing Platform • "
    "Edge AI + Centralized Incident Intelligence"
)