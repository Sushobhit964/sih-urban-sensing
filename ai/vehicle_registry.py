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

REGISTRY_DIR = os.path.join(
    OUTPUT_DIR,
    "vehicle_registry"
)

REGISTRY_FILE = os.path.join(
    REGISTRY_DIR,
    "vehicle_registry.csv"
)

EVIDENCE_DIR = os.path.join(
    REGISTRY_DIR,
    "evidence"
)

os.makedirs(
    REGISTRY_DIR,
    exist_ok=True
)

os.makedirs(
    EVIDENCE_DIR,
    exist_ok=True
)


# ============================================================
# INCIDENT WEIGHTS
# ============================================================

INCIDENT_WEIGHTS = {

    "HIT_AND_RUN": 10,

    "RASH_DRIVING": 8,

    "WRONG_WAY": 8,

    "TRAFFIC_VIOLATION": 5,

    "PEDESTRIAN_RISK": 4,

    "CONGESTION": 2,

    "ROAD_DAMAGE": 1,

    "POTHOLE": 1,

    "WATERLOGGING": 1
}


# ============================================================
# READ INCIDENTS
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

        return list(reader)


# ============================================================
# NORMALIZE PLATE
# ============================================================

def normalize_plate(plate):

    if plate is None:
        return "UNKNOWN"

    plate = str(
        plate
    ).upper().strip()

    # Remove spaces and common separators
    plate = plate.replace(
        " ",
        ""
    )

    plate = plate.replace(
        "-",
        ""
    )

    plate = plate.replace(
        ".",
        ""
    )

    if not plate:
        return "UNKNOWN"

    return plate


# ============================================================
# FIND PLATE IN INCIDENT
# ============================================================

def extract_plate(row):

    possible_fields = [

        "License_Plate",

        "Plate",

        "Plate_Number",

        "Registration",

        "Vehicle_Number",

        "Vehicle_Registration",

        "ANPR"
    ]

    for field in possible_fields:

        value = row.get(
            field,
            ""
        )

        if value:

            value = normalize_plate(
                value
            )

            if value != "UNKNOWN":

                return value

    return "UNKNOWN"


# ============================================================
# VEHICLE RISK
# ============================================================

def calculate_vehicle_risk(
    incidents
):

    score = 0

    for incident in incidents:

        incident_type = str(
            incident.get(
                "Type",
                ""
            )
        ).upper()

        severity = str(
            incident.get(
                "Severity",
                "LOW"
            )
        ).upper()

        base_weight = INCIDENT_WEIGHTS.get(
            incident_type,
            2
        )

        severity_multiplier = {

            "HIGH": 3,

            "MEDIUM": 2,

            "LOW": 1
        }.get(
            severity,
            1
        )

        score += (
            base_weight
            *
            severity_multiplier
        )

    return score


# ============================================================
# RISK LEVEL
# ============================================================

def get_risk_level(score):

    if score >= 25:
        return "CRITICAL"

    if score >= 15:
        return "HIGH"

    if score >= 7:
        return "MEDIUM"

    return "LOW"


# ============================================================
# BUILD VEHICLE REGISTRY
# ============================================================

def build_registry():

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
        "🚗 VEHICLE REGISTRY & ANPR INTELLIGENCE"
    )
    print(
        "========================================"
    )

    vehicles = defaultdict(list)

    # --------------------------------------------------------
    # Associate incidents with plates
    # --------------------------------------------------------

    for incident in incidents:

        plate = extract_plate(
            incident
        )

        # We only create a real registry
        # entry when a plate is available.
        if plate == "UNKNOWN":
            continue

        vehicles[
            plate
        ].append(
            incident
        )

    # --------------------------------------------------------
    # Write registry
    # --------------------------------------------------------

    with open(
        REGISTRY_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow([

            "Vehicle_ID",

            "License_Plate",

            "Incident_Count",

            "High_Severity_Incidents",

            "Rash_Driving_Count",

            "Wrong_Way_Count",

            "Hit_And_Run_Count",

            "First_Seen",

            "Last_Seen",

            "Risk_Score",

            "Risk_Level",

            "Latest_Latitude",

            "Latest_Longitude",

            "Latest_Evidence",

            "Registry_Status"
        ])

        for index, (
            plate,
            vehicle_incidents
        ) in enumerate(
            vehicles.items(),
            start=1
        ):

            vehicle_id = (
                f"VEH-{index:04d}"
            )

            # ------------------------------------------------
            # Counts
            # ------------------------------------------------

            incident_count = len(
                vehicle_incidents
            )

            high_severity = sum(

                1

                for incident
                in vehicle_incidents

                if str(
                    incident.get(
                        "Severity",
                        ""
                    )
                ).upper()
                == "HIGH"
            )

            rash_count = sum(

                1

                for incident
                in vehicle_incidents

                if "RASH"
                in str(
                    incident.get(
                        "Type",
                        ""
                    )
                ).upper()
            )

            wrong_way_count = sum(

                1

                for incident
                in vehicle_incidents

                if "WRONG"
                in str(
                    incident.get(
                        "Type",
                        ""
                    )
                ).upper()
            )

            hit_run_count = sum(

                1

                for incident
                in vehicle_incidents

                if (
                    "HIT"
                    in str(
                        incident.get(
                            "Type",
                            ""
                        )
                    ).upper()
                    and
                    "RUN"
                    in str(
                        incident.get(
                            "Type",
                            ""
                        )
                    ).upper()
                )
            )

            # ------------------------------------------------
            # Time
            # ------------------------------------------------

            times = [

                incident.get(
                    "Video_Time",
                    "N/A"
                )

                for incident
                in vehicle_incidents

            ]

            first_seen = (
                times[0]
                if times
                else "N/A"
            )

            last_seen = (
                times[-1]
                if times
                else "N/A"
            )

            # ------------------------------------------------
            # Risk
            # ------------------------------------------------

            risk_score = calculate_vehicle_risk(
                vehicle_incidents
            )

            risk_level = get_risk_level(
                risk_score
            )

            # ------------------------------------------------
            # Latest incident
            # ------------------------------------------------

            latest = vehicle_incidents[
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

            evidence = latest.get(
                "Evidence",
                "N/A"
            )

            writer.writerow([

                vehicle_id,

                plate,

                incident_count,

                high_severity,

                rash_count,

                wrong_way_count,

                hit_run_count,

                first_seen,

                last_seen,

                risk_score,

                risk_level,

                latitude,

                longitude,

                evidence,

                "ACTIVE"
            ])

            print()
            print(
                f"🚗 {vehicle_id}"
            )
            print(
                f"   Plate       : {plate}"
            )
            print(
                f"   Incidents   : {incident_count}"
            )
            print(
                f"   Risk Score  : {risk_score}"
            )
            print(
                f"   Risk Level  : {risk_level}"
            )

    print()
    print(
        "========================================"
    )
    print(
        f"Vehicles identified : {len(vehicles)}"
    )
    print(
        f"Registry             : {REGISTRY_FILE}"
    )
    print(
        "========================================"
    )


# ============================================================
# VEHICLE SEARCH
# ============================================================

def search_vehicle(plate):

    plate = normalize_plate(
        plate
    )

    if not os.path.exists(
        REGISTRY_FILE
    ):

        print(
            "❌ Vehicle registry does not exist."
        )

        return

    with open(
        REGISTRY_FILE,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(
            file
        )

        found = False

        for row in reader:

            if normalize_plate(
                row.get(
                    "License_Plate",
                    ""
                )
            ) == plate:

                found = True

                print()
                print(
                    "========================================"
                )
                print(
                    "🚗 VEHICLE RECORD"
                )
                print(
                    "========================================"
                )

                for key, value in row.items():

                    print(
                        f"{key:<28}: {value}"
                    )

                print(
                    "========================================"
                )

                break

    if not found:

        print(
            f"❌ No registry record found for {plate}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    build_registry()

    print()
    print(
        "Vehicle registry generation complete."
    )