import os
import csv
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUTPUT_DIR = os.path.join(BASE_DIR, "output")

INCIDENT_FILE = os.path.join(
    OUTPUT_DIR,
    "incidents.csv"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "bus_monitoring.csv"
)


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_camera_id(row):
    """
    Prefer a real Camera_ID if available.
    """

    for key in [
        "Camera_ID",
        "Camera",
        "Camera_Id",
        "Bus_ID",
        "Bus_Id",
        "Bus",
    ]:

        value = row.get(key)

        if value and str(value).strip():
            return str(value).strip()

    return "UNKNOWN"


def get_severity(row):
    return str(
        row.get("Severity", "LOW")
    ).strip().upper()


# ============================================================
# BUS MONITORING ENGINE
# ============================================================

def analyze_buses():

    if not os.path.exists(INCIDENT_FILE):

        print("❌ incidents.csv not found")
        return

    with open(
        INCIDENT_FILE,
        "r",
        newline=""
    ) as file:

        reader = csv.DictReader(file)
        incidents = list(reader)

    if not incidents:

        print("⚠ No incidents available.")
        return

    cameras = defaultdict(list)

    # --------------------------------------------------------
    # GROUP INCIDENTS
    # --------------------------------------------------------

    for incident in incidents:

        camera_id = get_camera_id(incident)

        cameras[camera_id].append(
            incident
        )

    results = []

    # --------------------------------------------------------
    # ANALYSE EACH CAMERA / BUS
    # --------------------------------------------------------

    for camera_id, camera_incidents in cameras.items():

        incident_count = len(
            camera_incidents
        )

        high = 0
        medium = 0
        low = 0

        incident_types = defaultdict(int)

        for incident in camera_incidents:

            severity = get_severity(
                incident
            )

            if severity == "HIGH":
                high += 1

            elif severity == "MEDIUM":
                medium += 1

            else:
                low += 1

            incident_type = str(
                incident.get(
                    "Type",
                    "UNKNOWN"
                )
            ).strip().upper()

            incident_types[
                incident_type
            ] += 1

        # ----------------------------------------------------
        # PERFORMANCE / RISK SCORE
        # ----------------------------------------------------

        risk_score = (
            high * 10
            + medium * 5
            + low * 2
        )

        risk_score = min(
            100,
            risk_score
        )

        if risk_score >= 75:
            health = "CRITICAL"

        elif risk_score >= 50:
            health = "HIGH"

        elif risk_score >= 25:
            health = "MEDIUM"

        else:
            health = "NORMAL"

        # ----------------------------------------------------
        # DOMINANT INCIDENT
        # ----------------------------------------------------

        if incident_types:

            dominant_incident = max(
                incident_types,
                key=incident_types.get
            )

        else:

            dominant_incident = "NONE"

        # ----------------------------------------------------
        # LAST INCIDENT
        # ----------------------------------------------------

        last_incident = camera_incidents[-1]

        last_time = last_incident.get(
            "Video_Time",
            "N/A"
        )

        results.append({

            "Camera_ID": camera_id,

            "Incident_Count":
                incident_count,

            "High_Severity":
                high,

            "Medium_Severity":
                medium,

            "Low_Severity":
                low,

            "Dominant_Incident":
                dominant_incident,

            "Risk_Score":
                risk_score,

            "Camera_Status":
                "ACTIVE",

            "Health_Level":
                health,

            "Last_Incident":
                last_time,
        })

    # --------------------------------------------------------
    # SORT BY RISK
    # --------------------------------------------------------

    results.sort(
        key=lambda x: (
            x["Risk_Score"],
            x["Incident_Count"]
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    fieldnames = [
        "Camera_ID",
        "Incident_Count",
        "High_Severity",
        "Medium_Severity",
        "Low_Severity",
        "Dominant_Incident",
        "Risk_Score",
        "Camera_Status",
        "Health_Level",
        "Last_Incident",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    # --------------------------------------------------------
    # TERMINAL OUTPUT
    # --------------------------------------------------------

    print()
    print("========================================")
    print("🚌 BUS / CAMERA MONITORING")
    print("========================================")

    print(
        f"Cameras analysed : {len(results)}"
    )

    print()

    for row in results[:10]:

        print(
            f"{row['Camera_ID']} | "
            f"{row['Health_Level']} | "
            f"Risk: {row['Risk_Score']}/100 | "
            f"Incidents: {row['Incident_Count']} | "
            f"Main: {row['Dominant_Incident']}"
        )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )

    print("========================================")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    analyze_buses()