import os
import csv
from datetime import datetime
from collections import defaultdict


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
    "incident_correlations.csv"
)


# ============================================================
# CORRELATION SETTINGS
# ============================================================

# Incidents are considered related when they occur
# within this many seconds of each other.
TIME_WINDOW_SECONDS = 15

# GPS zone precision.
# 3 decimal places is approximately a 100m-scale zone.
GPS_PRECISION = 3


# ============================================================
# INCIDENT RELATIONSHIPS
# ============================================================

RELATED_TYPES = {

    "POTHOLE": [
        "ROAD_DAMAGE",
        "PEDESTRIAN_RISK",
        "CONGESTION",
        "RASH_DRIVING"
    ],

    "ROAD_DAMAGE": [
        "POTHOLE",
        "WATERLOGGING",
        "CONGESTION",
        "PEDESTRIAN_RISK"
    ],

    "WATERLOGGING": [
        "ROAD_DAMAGE",
        "CONGESTION",
        "PEDESTRIAN_RISK"
    ],

    "CONGESTION": [
        "POTHOLE",
        "ROAD_DAMAGE",
        "WATERLOGGING",
        "RASH_DRIVING"
    ],

    "PEDESTRIAN_RISK": [
        "POTHOLE",
        "ROAD_DAMAGE",
        "WATERLOGGING",
        "RASH_DRIVING"
    ],

    "RASH_DRIVING": [
        "PEDESTRIAN_RISK",
        "CONGESTION",
        "WRONG_WAY",
        "HIT_AND_RUN"
    ],

    "WRONG_WAY": [
        "RASH_DRIVING",
        "PEDESTRIAN_RISK",
        "TRAFFIC_VIOLATION"
    ],

    "HIT_AND_RUN": [
        "RASH_DRIVING",
        "PEDESTRIAN_RISK"
    ]
}


# ============================================================
# ROOT-CAUSE RULES
# ============================================================

ROOT_CAUSES = {

    frozenset([
        "POTHOLE",
        "CONGESTION"
    ]): (
        "ROAD_DAMAGE_CAUSING_TRAFFIC_SLOWDOWN",
        "Inspect and repair damaged road surface"
    ),

    frozenset([
        "POTHOLE",
        "PEDESTRIAN_RISK"
    ]): (
        "ROAD_DAMAGE_CREATING_SAFETY_RISK",
        "Inspect road and improve pedestrian safety"
    ),

    frozenset([
        "ROAD_DAMAGE",
        "CONGESTION"
    ]): (
        "ROAD_CONDITION_AFFECTING_TRAFFIC",
        "Prioritize road maintenance"
    ),

    frozenset([
        "WATERLOGGING",
        "CONGESTION"
    ]): (
        "WATERLOGGING_CAUSING_TRAFFIC_DISRUPTION",
        "Inspect drainage and remove water accumulation"
    ),

    frozenset([
        "RASH_DRIVING",
        "PEDESTRIAN_RISK"
    ]): (
        "DANGEROUS_VEHICLE_BEHAVIOR",
        "Prioritize traffic enforcement"
    ),

    frozenset([
        "WRONG_WAY",
        "RASH_DRIVING"
    ]): (
        "HIGH_RISK_TRAFFIC_BEHAVIOR",
        "Flag for traffic enforcement review"
    ),

    frozenset([
        "HIT_AND_RUN",
        "RASH_DRIVING"
    ]): (
        "SERIOUS_TRAFFIC_INCIDENT",
        "Escalate to traffic/police response"
    )
}


# ============================================================
# SEVERITY
# ============================================================

SEVERITY_SCORE = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1
}


def combined_severity(incidents):

    highest = 0

    for incident in incidents:

        severity = str(
            incident.get(
                "Severity",
                "LOW"
            )
        ).upper()

        highest = max(
            highest,
            SEVERITY_SCORE.get(
                severity,
                1
            )
        )

    if highest >= 3:
        return "HIGH"

    if highest == 2:
        return "MEDIUM"

    return "LOW"


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value):

    try:

        if value is None:
            return None

        value = str(
            value
        ).strip()

        if value.upper() in [
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

def get_zone(incident):

    latitude = safe_float(
        incident.get(
            "Latitude"
        )
    )

    longitude = safe_float(
        incident.get(
            "Longitude"
        )
    )

    if (
        latitude is None
        or longitude is None
    ):
        return "UNKNOWN_ZONE"

    return (
        f"{latitude:.{GPS_PRECISION}f},"
        f"{longitude:.{GPS_PRECISION}f}"
    )


# ============================================================
# VIDEO TIME
# ============================================================

def parse_video_time(value):

    """
    Supports:
        00:12
        01:23
        00:01:25
        12.5
        125
    """

    if value is None:
        return None

    value = str(
        value
    ).strip()

    if not value:
        return None

    try:

        # Plain seconds
        if ":" not in value:

            return float(
                value
            )

        parts = value.split(":")

        if len(parts) == 2:

            minutes = float(
                parts[0]
            )

            seconds = float(
                parts[1]
            )

            return (
                minutes * 60
                +
                seconds
            )

        if len(parts) == 3:

            hours = float(
                parts[0]
            )

            minutes = float(
                parts[1]
            )

            seconds = float(
                parts[2]
            )

            return (
                hours * 3600
                +
                minutes * 60
                +
                seconds
            )

    except (
        ValueError,
        TypeError
    ):
        return None

    return None


# ============================================================
# INCIDENT TYPE
# ============================================================

def get_type(incident):

    return str(
        incident.get(
            "Type",
            "UNKNOWN"
        )
    ).upper().strip()


# ============================================================
# ARE INCIDENTS RELATED?
# ============================================================

def are_related(
    first,
    second
):

    type_a = get_type(
        first
    )

    type_b = get_type(
        second
    )

    # Same incident type can still be part
    # of the same event.
    if type_a == type_b:
        type_related = True

    else:

        related = RELATED_TYPES.get(
            type_a,
            []
        )

        reverse_related = RELATED_TYPES.get(
            type_b,
            []
        )

        type_related = (
            type_b in related
            or
            type_a in reverse_related
        )

    if not type_related:
        return False

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    zone_a = get_zone(
        first
    )

    zone_b = get_zone(
        second
    )

    if (
        zone_a != "UNKNOWN_ZONE"
        and
        zone_b != "UNKNOWN_ZONE"
        and
        zone_a != zone_b
    ):
        return False

    # --------------------------------------------------------
    # Time
    # --------------------------------------------------------

    time_a = parse_video_time(
        first.get(
            "Video_Time"
        )
    )

    time_b = parse_video_time(
        second.get(
            "Video_Time"
        )
    )

    # If both times are known, enforce window.
    if (
        time_a is not None
        and
        time_b is not None
    ):

        if abs(
            time_a - time_b
        ) > TIME_WINDOW_SECONDS:

            return False

    return True


# ============================================================
# FIND ROOT CAUSE
# ============================================================

def determine_root_cause(
    incidents
):

    types = set(
        get_type(
            incident
        )
        for incident in incidents
    )

    # Exact known combinations first.
    for combination, result in ROOT_CAUSES.items():

        if combination.issubset(
            types
        ):

            return result

    # Generic fallback rules.
    if "POTHOLE" in types:

        return (
            "POTHOLE_RELATED_ROAD_HAZARD",
            "Inspect and repair pothole"
        )

    if "ROAD_DAMAGE" in types:

        return (
            "ROAD_DAMAGE_RELATED_HAZARD",
            "Inspect road condition"
        )

    if "WATERLOGGING" in types:

        return (
            "WATERLOGGING_RELATED_HAZARD",
            "Inspect drainage"
        )

    if (
        "RASH_DRIVING" in types
        or
        "WRONG_WAY" in types
    ):

        return (
            "TRAFFIC_BEHAVIOR_HAZARD",
            "Traffic enforcement review"
        )

    return (
        "MULTI_INCIDENT_EVENT",
        "Review correlated incidents"
    )


# ============================================================
# CORRELATION CONFIDENCE
# ============================================================

def calculate_confidence(
    incident_count,
    same_zone,
    time_match
):

    score = 0

    # More incidents → stronger correlation.
    if incident_count >= 4:
        score += 0.4

    elif incident_count == 3:
        score += 0.3

    elif incident_count == 2:
        score += 0.2

    if same_zone:
        score += 0.3

    if time_match:
        score += 0.3

    return round(
        min(
            score,
            1.0
        ),
        2
    )


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

        reader = csv.DictReader(
            file
        )

        return list(
            reader
        )


# ============================================================
# BUILD CORRELATIONS
# ============================================================

def build_correlations():

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
        "🔗 INCIDENT CORRELATION ENGINE"
    )
    print(
        "========================================"
    )

    # --------------------------------------------------------
    # Group by geographic zone
    # --------------------------------------------------------

    zones = defaultdict(list)

    for index, incident in enumerate(
        incidents
    ):

        incident["_index"] = index

        zones[
            get_zone(
                incident
            )
        ].append(
            incident
        )

    correlations = []

    correlation_id = 1

    # --------------------------------------------------------
    # Compare incidents within each zone
    # --------------------------------------------------------

    for zone, zone_incidents in zones.items():

        visited = set()

        for i in range(
            len(zone_incidents)
        ):

            if i in visited:
                continue

            group = [
                zone_incidents[i]
            ]

            visited.add(i)

            # ----------------------------------------------
            # Find related incidents
            # ----------------------------------------------

            for j in range(
                i + 1,
                len(zone_incidents)
            ):

                if j in visited:
                    continue

                candidate = zone_incidents[j]

                related_to_group = False

                for existing in group:

                    if are_related(
                        existing,
                        candidate
                    ):

                        related_to_group = True
                        break

                if related_to_group:

                    group.append(
                        candidate
                    )

                    visited.add(j)

            # A single incident is not a correlation.
            if len(group) < 2:
                continue

            # ----------------------------------------------
            # Analyze group
            # ----------------------------------------------

            types = sorted(
                set(
                    get_type(
                        incident
                    )
                    for incident in group
                )
            )

            incident_ids = [
                incident.get(
                    "Incident_ID",
                    "N/A"
                )
                for incident in group
            ]

            root_cause, recommendation = (
                determine_root_cause(
                    group
                )
            )

            severity = combined_severity(
                group
            )

            time_values = [
                parse_video_time(
                    incident.get(
                        "Video_Time"
                    )
                )
                for incident in group
            ]

            valid_times = [
                value
                for value in time_values
                if value is not None
            ]

            if valid_times:

                time_spread = (
                    max(valid_times)
                    -
                    min(valid_times)
                )

            else:

                time_spread = None

            same_zone = (
                zone != "UNKNOWN_ZONE"
            )

            time_match = (
                time_spread is not None
                and
                time_spread
                <= TIME_WINDOW_SECONDS
            )

            confidence = calculate_confidence(
                len(group),
                same_zone,
                time_match
            )

            latest = group[-1]

            correlation = {

                "Correlation_ID":
                    f"CORR-{correlation_id:04d}",

                "Incident_Count":
                    len(group),

                "Incident_IDs":
                    "|".join(
                        incident_ids
                    ),

                "Incident_Types":
                    "|".join(
                        types
                    ),

                "Zone":
                    zone,

                "Combined_Severity":
                    severity,

                "Root_Cause":
                    root_cause,

                "Recommendation":
                    recommendation,

                "Correlation_Confidence":
                    confidence,

                "Time_Spread_Seconds":
                    (
                        round(
                            time_spread,
                            2
                        )
                        if time_spread is not None
                        else "N/A"
                    ),

                "Latitude":
                    latest.get(
                        "Latitude",
                        "N/A"
                    ),

                "Longitude":
                    latest.get(
                        "Longitude",
                        "N/A"
                    ),

                "Generated_At":
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
            }

            correlations.append(
                correlation
            )

            correlation_id += 1

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        fieldnames = [

            "Correlation_ID",

            "Incident_Count",

            "Incident_IDs",

            "Incident_Types",

            "Zone",

            "Combined_Severity",

            "Root_Cause",

            "Recommendation",

            "Correlation_Confidence",

            "Time_Spread_Seconds",

            "Latitude",

            "Longitude",

            "Generated_At"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            correlations
        )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    if correlations:

        for correlation in correlations:

            print()
            print(
                f"🔗 "
                f"{correlation['Correlation_ID']}"
            )

            print(
                f"   Incidents   : "
                f"{correlation['Incident_IDs']}"
            )

            print(
                f"   Types       : "
                f"{correlation['Incident_Types']}"
            )

            print(
                f"   Severity    : "
                f"{correlation['Combined_Severity']}"
            )

            print(
                f"   Root Cause  : "
                f"{correlation['Root_Cause']}"
            )

            print(
                f"   Confidence  : "
                f"{correlation['Correlation_Confidence']}"
            )

            print(
                f"   Action      : "
                f"{correlation['Recommendation']}"
            )

    else:

        print()
        print(
            "ℹ️ No correlated incidents found."
        )

    print()
    print(
        "========================================"
    )

    print(
        f"Correlations found : "
        f"{len(correlations)}"
    )

    print(
        f"Output             : "
        f"{OUTPUT_FILE}"
    )

    print(
        "========================================"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    build_correlations()