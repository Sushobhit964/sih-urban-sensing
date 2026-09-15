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
    "incident_hotspots.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

# Number of incidents required for each hotspot level
CRITICAL_THRESHOLD = 15
HIGH_THRESHOLD = 10
MEDIUM_THRESHOLD = 5


# ============================================================
# HELPERS
# ============================================================

def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_zone(row):
    """
    Creates an approximate geographic zone.

    GPS is rounded so nearby incidents are grouped together.
    """

    lat = safe_float(row.get("Latitude"))
    lon = safe_float(row.get("Longitude"))

    if lat is None or lon is None:
        return "UNMAPPED"

    if not (-90 <= lat <= 90):
        return "UNMAPPED"

    if not (-180 <= lon <= 180):
        return "UNMAPPED"

    return f"{lat:.3f}_{lon:.3f}"


def get_hotspot_level(count):

    if count >= CRITICAL_THRESHOLD:
        return "CRITICAL"

    if count >= HIGH_THRESHOLD:
        return "HIGH"

    if count >= MEDIUM_THRESHOLD:
        return "MEDIUM"

    return "NORMAL"


# ============================================================
# HOTSPOT ENGINE
# ============================================================

def detect_hotspots():

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

    zones = defaultdict(list)

    # --------------------------------------------------------
    # GROUP INCIDENTS BY LOCATION
    # --------------------------------------------------------

    for incident in incidents:

        zone = get_zone(incident)

        # Ignore incidents without usable GPS
        if zone == "UNMAPPED":
            continue

        zones[zone].append(incident)

    results = []

    # --------------------------------------------------------
    # ANALYSE EACH ZONE
    # --------------------------------------------------------

    for zone, zone_incidents in zones.items():

        incident_count = len(zone_incidents)

        type_counts = defaultdict(int)

        severity_counts = defaultdict(int)

        incident_types = set()

        for incident in zone_incidents:

            incident_type = str(
                incident.get(
                    "Type",
                    "UNKNOWN"
                )
            ).strip().upper()

            severity = str(
                incident.get(
                    "Severity",
                    "LOW"
                )
            ).strip().upper()

            type_counts[incident_type] += 1

            severity_counts[severity] += 1

            incident_types.add(
                incident_type
            )

        high_severity = (
            severity_counts["HIGH"]
        )

        medium_severity = (
            severity_counts["MEDIUM"]
        )

        # ----------------------------------------------------
        # HOTSPOT SCORE
        # ----------------------------------------------------

        score = incident_count * 5

        # High-severity incidents have
        # stronger influence on hotspot score.

        score += high_severity * 8

        score += medium_severity * 3

        score = min(
            100,
            score
        )

        if score >= 75:
            hotspot_level = "CRITICAL"

        elif score >= 50:
            hotspot_level = "HIGH"

        elif score >= 25:
            hotspot_level = "MEDIUM"

        else:
            hotspot_level = "NORMAL"

        # ----------------------------------------------------
        # MOST COMMON INCIDENT
        # ----------------------------------------------------

        if type_counts:

            dominant_incident = max(
                type_counts,
                key=type_counts.get
            )

        else:

            dominant_incident = "UNKNOWN"

        # ----------------------------------------------------
        # GPS
        # ----------------------------------------------------

        first = zone_incidents[0]

        latitude = safe_float(
            first.get("Latitude")
        )

        longitude = safe_float(
            first.get("Longitude")
        )

        results.append({

            "Zone": zone,

            "Latitude": (
                round(latitude, 6)
                if latitude is not None
                else ""
            ),

            "Longitude": (
                round(longitude, 6)
                if longitude is not None
                else ""
            ),

            "Incident_Count":
                incident_count,

            "High_Severity":
                high_severity,

            "Medium_Severity":
                medium_severity,

            "Dominant_Incident":
                dominant_incident,

            "Incident_Types":
                len(incident_types),

            "Hotspot_Score":
                score,

            "Hotspot_Level":
                hotspot_level,
        })

    # --------------------------------------------------------
    # SORT HOTSPOTS
    # --------------------------------------------------------

    results.sort(
        key=lambda x: (
            x["Hotspot_Score"],
            x["Incident_Count"]
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    fieldnames = [
        "Zone",
        "Latitude",
        "Longitude",
        "Incident_Count",
        "High_Severity",
        "Medium_Severity",
        "Dominant_Incident",
        "Incident_Types",
        "Hotspot_Score",
        "Hotspot_Level",
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
    print("🔥 INCIDENT HOTSPOT ENGINE")
    print("========================================")

    print(
        f"Zones analysed : {len(results)}"
    )

    print(
        f"Hotspots       : "
        f"{sum(1 for r in results if r['Hotspot_Level'] != 'NORMAL')}"
    )

    print()

    for row in results[:10]:

        print(
            f"{row['Zone']} | "
            f"{row['Hotspot_Level']} | "
            f"Score: {row['Hotspot_Score']}/100 | "
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

    detect_hotspots()