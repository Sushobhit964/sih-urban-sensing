import os
import csv
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUTPUT_DIR = os.path.join(BASE_DIR, "output")

CONGESTION_FILE = os.path.join(
    OUTPUT_DIR,
    "congestion.csv"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "route_delay.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

# Baseline travel time used for the prototype.
# Replace with actual route travel times when GPS/route data
# becomes available.
DEFAULT_BASE_TIME = 30  # minutes

# Estimated delay produced by congestion level
CONGESTION_DELAY = {
    "LOW": 0,
    "MEDIUM": 5,
    "HIGH": 12,
}


# ============================================================
# HELPERS
# ============================================================

def get_congestion_level(value):

    value = str(value).strip().upper()

    if value in ["LOW", "MEDIUM", "HIGH"]:
        return value

    return "LOW"


def get_route_status(delay):

    if delay >= 15:
        return "HEAVY DELAY"

    if delay >= 7:
        return "DELAYED"

    if delay > 0:
        return "SLIGHT DELAY"

    return "ON TIME"


# ============================================================
# ROUTE DELAY ENGINE
# ============================================================

def calculate_route_delay():

    if not os.path.exists(CONGESTION_FILE):

        print("❌ congestion.csv not found")

        print(
            "Run your traffic/congestion detection first."
        )

        return

    with open(
        CONGESTION_FILE,
        "r",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        records = list(reader)

    if not records:

        print("⚠ No congestion records found.")

        return

    # --------------------------------------------------------
    # GROUP OBSERVATIONS
    # --------------------------------------------------------

    levels = defaultdict(list)

    vehicle_counts = defaultdict(list)

    for row in records:

        # Current prototype has no route ID.
        # Therefore observations are grouped into a
        # monitored corridor.

        route = row.get(
            "Route_ID",
            "MONITORED_CORRIDOR"
        )

        route = str(route).strip()

        if not route:
            route = "MONITORED_CORRIDOR"

        level = get_congestion_level(
            row.get(
                "Congestion_Level",
                "LOW"
            )
        )

        vehicle_count = 0

        try:
            vehicle_count = int(
                float(
                    row.get(
                        "Vehicle_Count",
                        0
                    )
                )
            )
        except (TypeError, ValueError):
            vehicle_count = 0

        levels[route].append(level)

        vehicle_counts[route].append(
            vehicle_count
        )

    results = []

    # --------------------------------------------------------
    # ANALYSE ROUTES
    # --------------------------------------------------------

    for route in levels:

        observations = levels[route]

        counts = vehicle_counts[route]

        total = len(observations)

        low_count = observations.count("LOW")
        medium_count = observations.count("MEDIUM")
        high_count = observations.count("HIGH")

        # ----------------------------------------------------
        # DOMINANT CONGESTION
        # ----------------------------------------------------

        level_counts = {
            "LOW": low_count,
            "MEDIUM": medium_count,
            "HIGH": high_count,
        }

        dominant_level = max(
            level_counts,
            key=level_counts.get
        )

        # ----------------------------------------------------
        # ESTIMATED DELAY
        # ----------------------------------------------------

        # Weighted average congestion delay.
        #
        # This is an ESTIMATE, not real GPS-derived ETA.

        weighted_delay = (
            low_count * CONGESTION_DELAY["LOW"]
            + medium_count * CONGESTION_DELAY["MEDIUM"]
            + high_count * CONGESTION_DELAY["HIGH"]
        ) / total

        estimated_delay = round(
            weighted_delay,
            1
        )

        estimated_travel_time = round(
            DEFAULT_BASE_TIME + estimated_delay,
            1
        )

        delay_percentage = round(
            (
                estimated_delay
                / DEFAULT_BASE_TIME
            ) * 100,
            1
        )

        average_vehicle_count = round(
            sum(counts) / len(counts),
            1
        )

        status = get_route_status(
            estimated_delay
        )

        results.append({

            "Route_ID": route,

            "Baseline_Time_Min": DEFAULT_BASE_TIME,

            "Estimated_Delay_Min":
                estimated_delay,

            "Estimated_Travel_Time_Min":
                estimated_travel_time,

            "Delay_Percentage":
                delay_percentage,

            "Average_Vehicles":
                average_vehicle_count,

            "Low_Observations":
                low_count,

            "Medium_Observations":
                medium_count,

            "High_Observations":
                high_count,

            "Dominant_Congestion":
                dominant_level,

            "Route_Status":
                status,
        })

    # --------------------------------------------------------
    # SORT BY DELAY
    # --------------------------------------------------------

    results.sort(
        key=lambda x: x[
            "Estimated_Delay_Min"
        ],
        reverse=True
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    fieldnames = [
        "Route_ID",
        "Baseline_Time_Min",
        "Estimated_Delay_Min",
        "Estimated_Travel_Time_Min",
        "Delay_Percentage",
        "Average_Vehicles",
        "Low_Observations",
        "Medium_Observations",
        "High_Observations",
        "Dominant_Congestion",
        "Route_Status",
    ]

    os.makedirs(
        OUTPUT_DIR,
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

    # --------------------------------------------------------
    # TERMINAL OUTPUT
    # --------------------------------------------------------

    print()
    print("========================================")
    print("⏱️ ROUTE DELAY / ETA INTELLIGENCE")
    print("========================================")

    print(
        f"Routes analysed : {len(results)}"
    )

    print()

    for row in results:

        print(
            f"{row['Route_ID']} | "
            f"{row['Route_Status']} | "
            f"Delay: +{row['Estimated_Delay_Min']} min | "
            f"ETA: {row['Estimated_Travel_Time_Min']} min | "
            f"Congestion: {row['Dominant_Congestion']}"
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

    calculate_route_delay()