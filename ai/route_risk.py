import os
import csv
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCIDENT_FILE = os.path.join(BASE_DIR, "output", "incidents.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "output", "route_risk.csv")


# ============================================================
# WEIGHTS
# ============================================================

TYPE_WEIGHTS = {
    "ROAD_DAMAGE": 25,
    "POTHOLE": 25,
    "PEDESTRIAN_RISK": 30,
    "WATERLOGGING": 25,
    "RASH_DRIVING": 20,
    "WRONG_WAY": 30,
    "CONGESTION": 15,
    "TRAFFIC": 10,
}

SEVERITY_MULTIPLIER = {
    "LOW": 1.0,
    "MEDIUM": 1.5,
    "HIGH": 2.0,
}


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_risk_level(score):
    if score >= 75:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 25:
        return "MEDIUM"
    return "LOW"


def get_zone(row):
    """
    Creates an approximate geographic zone from GPS.

    Example:
    23.2591, 77.4126
    becomes:
    23.259_77.413
    """

    lat = safe_float(row.get("Latitude"))
    lon = safe_float(row.get("Longitude"))

    if lat is None or lon is None:
        return "UNMAPPED"

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return "UNMAPPED"

    return f"{lat:.3f}_{lon:.3f}"


# ============================================================
# MAIN
# ============================================================

def calculate_route_risk():

    if not os.path.exists(INCIDENT_FILE):
        print("❌ incidents.csv not found")
        return

    with open(INCIDENT_FILE, "r", newline="") as file:
        reader = csv.DictReader(file)
        incidents = list(reader)

    if not incidents:
        print("⚠ No incidents found.")
        return

    zones = defaultdict(list)

    for incident in incidents:
        zone = get_zone(incident)
        zones[zone].append(incident)

    results = []

    for zone, zone_incidents in zones.items():

        incident_count = len(zone_incidents)

        counts = defaultdict(int)
        high_severity = 0

        total_score = 0

        for incident in zone_incidents:

            incident_type = str(
                incident.get("Type", "")
            ).strip().upper()

            severity = str(
                incident.get("Severity", "LOW")
            ).strip().upper()

            weight = TYPE_WEIGHTS.get(
                incident_type,
                10
            )

            multiplier = SEVERITY_MULTIPLIER.get(
                severity,
                1.0
            )

            score = weight * multiplier

            total_score += score

            counts[incident_type] += 1

            if severity == "HIGH":
                high_severity += 1

        # Normalize score so repeated incidents
        # increase risk but don't make it unlimited.
        risk_score = min(
            100,
            round(total_score / max(incident_count, 1) * 2)
        )

        # Additional penalty for repeated incidents
        repetition_bonus = min(
            20,
            incident_count * 2
        )

        risk_score = min(
            100,
            risk_score + repetition_bonus
        )

        risk_level = get_risk_level(risk_score)

        results.append({
            "Zone": zone,
            "Incident_Count": incident_count,
            "Road_Damage": counts["ROAD_DAMAGE"],
            "Potholes": counts["POTHOLE"],
            "Pedestrian_Risk": counts["PEDESTRIAN_RISK"],
            "Waterlogging": counts["WATERLOGGING"],
            "Rash_Driving": counts["RASH_DRIVING"],
            "Wrong_Way": counts["WRONG_WAY"],
            "Congestion": counts["CONGESTION"],
            "Traffic": counts["TRAFFIC"],
            "High_Severity": high_severity,
            "Risk_Score": risk_score,
            "Risk_Level": risk_level,
        })

    # Highest risk first
    results.sort(
        key=lambda x: x["Risk_Score"],
        reverse=True
    )

    fieldnames = [
        "Zone",
        "Incident_Count",
        "Road_Damage",
        "Potholes",
        "Pedestrian_Risk",
        "Waterlogging",
        "Rash_Driving",
        "Wrong_Way",
        "Congestion",
        "Traffic",
        "High_Severity",
        "Risk_Score",
        "Risk_Level",
    ]

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

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

    print()
    print("========================================")
    print("🗺️ ROUTE RISK ENGINE")
    print("========================================")
    print(f"Zones analysed : {len(results)}")
    print(f"Output         : {OUTPUT_FILE}")
    print()

    for row in results[:10]:

        print(
            f"{row['Zone']} | "
            f"Score: {row['Risk_Score']}/100 | "
            f"{row['Risk_Level']} | "
            f"Incidents: {row['Incident_Count']}"
        )

    print("========================================")


if __name__ == "__main__":
    calculate_route_risk()