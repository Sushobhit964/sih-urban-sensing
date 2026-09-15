import os
import csv
from collections import defaultdict
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

INCIDENT_FILE = os.path.join(
    OUTPUT_DIR,
    "incidents.csv"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "maintenance_prediction.csv"
)


# ============================================================
# WEIGHTS
# ============================================================

INCIDENT_WEIGHTS = {
    "POTHOLE": 5,
    "ROAD_DAMAGE": 5,
    "WATERLOGGING": 4,
    "PEDESTRIAN_RISK": 3,
    "WRONG_WAY": 2,
    "RASH_DRIVING": 2,
    "TRAFFIC_VIOLATION": 2,
    "CONGESTION": 1,
}


SEVERITY_MULTIPLIER = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


# ============================================================
# LOAD INCIDENTS
# ============================================================

def load_incidents():

    if not os.path.exists(
        INCIDENT_FILE
    ):
        print(
            "❌ incidents.csv not found."
        )
        return []

    with open(
        INCIDENT_FILE,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        return list(reader)


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value):

    try:

        if value is None:
            return None

        if str(value).strip().upper() in [
            "",
            "N/A",
            "NA",
            "NONE",
            "NULL"
        ]:
            return None

        return float(value)

    except (
        ValueError,
        TypeError
    ):

        return None


# ============================================================
# ZONE
# ============================================================

def get_zone(row):

    latitude = safe_float(
        row.get(
            "Latitude"
        )
    )

    longitude = safe_float(
        row.get(
            "Longitude"
        )
    )

    if (
        latitude is not None
        and
        longitude is not None
    ):

        # Approximate geographic zone.
        # Rounding prevents every detection
        # from becoming a separate location.
        return (
            f"{latitude:.3f},"
            f"{longitude:.3f}"
        )

    return "UNKNOWN_ZONE"


# ============================================================
# INCIDENT SCORE
# ============================================================

def incident_score(row):

    incident_type = str(
        row.get(
            "Type",
            "UNKNOWN"
        )
    ).upper().strip()

    severity = str(
        row.get(
            "Severity",
            "LOW"
        )
    ).upper().strip()

    base_weight = INCIDENT_WEIGHTS.get(
        incident_type,
        1
    )

    multiplier = SEVERITY_MULTIPLIER.get(
        severity,
        1
    )

    return (
        base_weight
        *
        multiplier
    )


# ============================================================
# MAINTENANCE LEVEL
# ============================================================

def get_maintenance_level(
    score,
    incident_count
):

    if score >= 40 or incident_count >= 10:
        return "CRITICAL"

    if score >= 25 or incident_count >= 6:
        return "HIGH"

    if score >= 12 or incident_count >= 3:
        return "MEDIUM"

    return "LOW"


# ============================================================
# TREND
# ============================================================

def get_trend(
    incidents
):

    """
    Estimates deterioration from the ordering
    of incidents in the available dataset.

    This is a prototype trend indicator.
    A production version should use dated historical
    observations over multiple days/weeks.
    """

    if len(incidents) < 4:
        return "INSUFFICIENT DATA"

    scores = [
        incident_score(
            incident
        )
        for incident in incidents
    ]

    midpoint = len(scores) // 2

    first_half = scores[
        :midpoint
    ]

    second_half = scores[
        midpoint:
    ]

    first_average = (
        sum(first_half)
        /
        len(first_half)
    )

    second_average = (
        sum(second_half)
        /
        len(second_half)
    )

    if first_average == 0:
        return "STABLE"

    change = (
        (
            second_average
            -
            first_average
        )
        /
        first_average
    ) * 100

    if change >= 40:
        return "RAPIDLY DETERIORATING"

    if change >= 15:
        return "DETERIORATING"

    if change <= -15:
        return "IMPROVING"

    return "STABLE"


# ============================================================
# MAINTENANCE PRIORITY
# ============================================================

def get_priority(
    maintenance_level,
    trend
):

    if (
        maintenance_level == "CRITICAL"
        or
        trend == "RAPIDLY DETERIORATING"
    ):
        return 1

    if (
        maintenance_level == "HIGH"
        or
        trend == "DETERIORATING"
    ):
        return 2

    if maintenance_level == "MEDIUM":
        return 3

    return 4


# ============================================================
# BUILD PREDICTION
# ============================================================

def build_prediction():

    incidents = load_incidents()

    if not incidents:

        print(
            "ℹ️ No incidents available."
        )

        return

    print()
    print(
        "========================================"
    )
    print(
        "🛣️ ROAD MAINTENANCE PREDICTION"
    )
    print(
        "========================================"
    )

    zones = defaultdict(list)

    # --------------------------------------------------------
    # Group incidents geographically
    # --------------------------------------------------------

    for incident in incidents:

        zone = get_zone(
            incident
        )

        zones[
            zone
        ].append(
            incident
        )

    predictions = []

    # --------------------------------------------------------
    # Analyze each zone
    # --------------------------------------------------------

    for zone, zone_incidents in zones.items():

        total_score = sum(
            incident_score(
                incident
            )
            for incident
            in zone_incidents
        )

        incident_count = len(
            zone_incidents
        )

        potholes = sum(

            1

            for incident
            in zone_incidents

            if "POTHOLE"
            in str(
                incident.get(
                    "Type",
                    ""
                )
            ).upper()
        )

        road_damage = sum(

            1

            for incident
            in zone_incidents

            if "ROAD_DAMAGE"
            in str(
                incident.get(
                    "Type",
                    ""
                )
            ).upper()
        )

        waterlogging = sum(

            1

            for incident
            in zone_incidents

            if "WATERLOGGING"
            in str(
                incident.get(
                    "Type",
                    ""
                )
            ).upper()
        )

        high_severity = sum(

            1

            for incident
            in zone_incidents

            if str(
                incident.get(
                    "Severity",
                    ""
                )
            ).upper()
            == "HIGH"
        )

        trend = get_trend(
            zone_incidents
        )

        maintenance_level = get_maintenance_level(
            total_score,
            incident_count
        )

        priority = get_priority(
            maintenance_level,
            trend
        )

        latest = zone_incidents[
            -1
        ]

        latitude = latest.get(
            "Latitude",
            "N/A"
        )

        longitude = latest.get(
            "Longitude",
            "N/A"
        )

        prediction = {

            "Zone": zone,

            "Incident_Count":
                incident_count,

            "Pothole_Count":
                potholes,

            "Road_Damage_Count":
                road_damage,

            "Waterlogging_Count":
                waterlogging,

            "High_Severity_Count":
                high_severity,

            "Maintenance_Score":
                total_score,

            "Maintenance_Level":
                maintenance_level,

            "Condition_Trend":
                trend,

            "Maintenance_Priority":
                priority,

            "Latitude":
                latitude,

            "Longitude":
                longitude,

            "Generated_At":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        }

        predictions.append(
            prediction
        )

    # --------------------------------------------------------
    # Highest priority first
    # --------------------------------------------------------

    predictions.sort(
        key=lambda x: (
            x["Maintenance_Priority"],
            -x["Maintenance_Score"]
        )
    )

    # --------------------------------------------------------
    # WRITE CSV
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "Zone",
                "Incident_Count",
                "Pothole_Count",
                "Road_Damage_Count",
                "Waterlogging_Count",
                "High_Severity_Count",
                "Maintenance_Score",
                "Maintenance_Level",
                "Condition_Trend",
                "Maintenance_Priority",
                "Latitude",
                "Longitude",
                "Generated_At"
            ]
        )

        writer.writeheader()

        writer.writerows(
            predictions
        )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    for prediction in predictions:

        print()
        print(
            f"📍 Zone: "
            f"{prediction['Zone']}"
        )

        print(
            f"   Incidents    : "
            f"{prediction['Incident_Count']}"
        )

        print(
            f"   Road Damage  : "
            f"{prediction['Road_Damage_Count']}"
        )

        print(
            f"   Potholes     : "
            f"{prediction['Pothole_Count']}"
        )

        print(
            f"   Waterlogging : "
            f"{prediction['Waterlogging_Count']}"
        )

        print(
            f"   Score        : "
            f"{prediction['Maintenance_Score']}"
        )

        print(
            f"   Condition    : "
            f"{prediction['Condition_Trend']}"
        )

        print(
            f"   Maintenance  : "
            f"{prediction['Maintenance_Level']}"
        )

        print(
            f"   Priority     : "
            f"{prediction['Maintenance_Priority']}"
        )

    print()
    print(
        "========================================"
    )

    print(
        f"Zones analyzed : {len(predictions)}"
    )

    print(
        f"Output         : {OUTPUT_FILE}"
    )

    print(
        "========================================"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    build_prediction()