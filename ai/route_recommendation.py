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

ROUTE_RISK_FILE = os.path.join(
    OUTPUT_DIR,
    "route_risk.csv"
)

ROUTE_DELAY_FILE = os.path.join(
    OUTPUT_DIR,
    "route_delay.csv"
)

FLOW_FILE = os.path.join(
    OUTPUT_DIR,
    "vehicle_flow.csv"
)

HOTSPOT_FILE = os.path.join(
    OUTPUT_DIR,
    "incident_hotspots.csv"
)

MAINTENANCE_FILE = os.path.join(
    OUTPUT_DIR,
    "maintenance_prediction.csv"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "route_recommendation.csv"
)


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_float(value, default=0):

    try:

        if value is None:
            return default

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
            return default

        return float(value)

    except (
        ValueError,
        TypeError
    ):

        return default


# ============================================================
# READ CSV
# ============================================================

def read_csv_file(path):

    if not os.path.exists(path):

        return []

    try:

        with open(
            path,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            return list(
                csv.DictReader(file)
            )

    except Exception as error:

        print(
            f"⚠️ Could not read {path}: {error}"
        )

        return []


# ============================================================
# ROUTE NAME
# ============================================================

def get_route(row):

    for field in [
        "Route_ID",
        "Route",
        "Corridor",
        "MONITORED_CORRIDOR"
    ]:

        value = row.get(
            field,
            ""
        )

        if value:

            return str(
                value
            ).strip()

    return "MONITORED_CORRIDOR"


# ============================================================
# LOAD ROUTE DATA
# ============================================================

def load_route_data():

    data = defaultdict(
        lambda: {
            "risk": 0,
            "delay": 0,
            "hotspot": 0,
            "maintenance": 0,
            "flow_imbalance": 0,
            "sources": 0
        }
    )

    # --------------------------------------------------------
    # Route risk
    # --------------------------------------------------------

    for row in read_csv_file(
        ROUTE_RISK_FILE
    ):

        route = get_route(
            row
        )

        data[route]["risk"] = max(
            data[route]["risk"],
            safe_float(
                row.get(
                    "Risk_Score"
                )
            )
        )

        data[route]["sources"] += 1

    # --------------------------------------------------------
    # Route delay
    # --------------------------------------------------------

    for row in read_csv_file(
        ROUTE_DELAY_FILE
    ):

        route = get_route(
            row
        )

        data[route]["delay"] = max(
            data[route]["delay"],
            safe_float(
                row.get(
                    "Estimated_Delay_Minutes"
                )
            )
        )

        data[route]["sources"] += 1

    # --------------------------------------------------------
    # Vehicle flow
    # --------------------------------------------------------

    for row in read_csv_file(
        FLOW_FILE
    ):

        route = get_route(
            row
        )

        imbalance = safe_float(
            row.get(
                "Flow_Imbalance"
            )
        )

        data[route]["flow_imbalance"] = max(
            data[route]["flow_imbalance"],
            imbalance
        )

    # --------------------------------------------------------
    # Hotspots
    # --------------------------------------------------------

    for row in read_csv_file(
        HOTSPOT_FILE
    ):

        route = get_route(
            row
        )

        hotspot_score = safe_float(
            row.get(
                "Hotspot_Score"
            )
        )

        data[route]["hotspot"] = max(
            data[route]["hotspot"],
            hotspot_score
        )

    # --------------------------------------------------------
    # Maintenance
    # --------------------------------------------------------

    for row in read_csv_file(
        MAINTENANCE_FILE
    ):

        route = get_route(
            row
        )

        maintenance_score = safe_float(
            row.get(
                "Maintenance_Score"
            )
        )

        data[route]["maintenance"] = max(
            data[route]["maintenance"],
            maintenance_score
        )

    return data


# ============================================================
# NORMALIZE SCORE
# ============================================================

def normalize(
    value,
    maximum
):

    if maximum <= 0:
        return 0

    return min(
        (
            value
            /
            maximum
        )
        * 100,
        100
    )


# ============================================================
# ROUTE SCORE
# ============================================================

def calculate_route_score(
    route_data,
    max_risk,
    max_delay,
    max_hotspot,
    max_maintenance
):

    risk = normalize(
        route_data["risk"],
        max_risk
    )

    delay = normalize(
        route_data["delay"],
        max_delay
    )

    hotspot = normalize(
        route_data["hotspot"],
        max_hotspot
    )

    maintenance = normalize(
        route_data["maintenance"],
        max_maintenance
    )

    flow = min(
        route_data["flow_imbalance"],
        100
    )

    # --------------------------------------------------------
    # Weighted score
    #
    # Lower = better
    # --------------------------------------------------------

    score = (

        risk * 0.35

        +

        delay * 0.25

        +

        hotspot * 0.15

        +

        maintenance * 0.15

        +

        flow * 0.10
    )

    return round(
        score,
        2
    )


# ============================================================
# ROUTE CONDITION
# ============================================================

def get_condition(score):

    if score >= 75:
        return "CRITICAL"

    if score >= 55:
        return "HIGH RISK"

    if score >= 30:
        return "MODERATE"

    return "GOOD"


# ============================================================
# RECOMMENDATION
# ============================================================

def get_recommendation(
    score
):

    if score >= 75:

        return (
            "AVOID ROUTE - "
            "Critical safety/congestion conditions"
        )

    if score >= 55:

        return (
            "USE WITH CAUTION - "
            "High risk conditions detected"
        )

    if score >= 30:

        return (
            "ACCEPTABLE - "
            "Monitor conditions"
        )

    return (
        "PREFERRED ROUTE"
    )


# ============================================================
# BUILD ROUTE RECOMMENDATION
# ============================================================

def build_recommendation():

    route_data = load_route_data()

    if not route_data:

        print(
            "❌ No route intelligence data found."
        )

        print(
            "Run route_risk.py, route_delay.py, "
            "hotspot_detection.py etc. first."
        )

        return

    print()
    print(
        "========================================"
    )
    print(
        "🧭 DYNAMIC ROUTE RECOMMENDATION"
    )
    print(
        "========================================"
    )

    max_risk = max(
        (
            value["risk"]
            for value in route_data.values()
        ),
        default=1
    )

    max_delay = max(
        (
            value["delay"]
            for value in route_data.values()
        ),
        default=1
    )

    max_hotspot = max(
        (
            value["hotspot"]
            for value in route_data.values()
        ),
        default=1
    )

    max_maintenance = max(
        (
            value["maintenance"]
            for value in route_data.values()
        ),
        default=1
    )

    recommendations = []

    for route, values in route_data.items():

        score = calculate_route_score(
            values,
            max_risk,
            max_delay,
            max_hotspot,
            max_maintenance
        )

        condition = get_condition(
            score
        )

        recommendation = get_recommendation(
            score
        )

        recommendations.append({

            "Route_ID":
                route,

            "Route_Score":
                score,

            "Condition":
                condition,

            "Recommendation":
                recommendation,

            "Risk_Score":
                round(
                    values["risk"],
                    2
                ),

            "Estimated_Delay_Minutes":
                round(
                    values["delay"],
                    2
                ),

            "Hotspot_Score":
                round(
                    values["hotspot"],
                    2
                ),

            "Maintenance_Score":
                round(
                    values["maintenance"],
                    2
                ),

            "Flow_Imbalance":
                round(
                    values["flow_imbalance"],
                    2
                ),

            "Generated_At":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        })

    # --------------------------------------------------------
    # Best route first
    # --------------------------------------------------------

    recommendations.sort(
        key=lambda x:
        x["Route_Score"]
    )

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

            "Route_ID",

            "Route_Score",

            "Condition",

            "Recommendation",

            "Risk_Score",

            "Estimated_Delay_Minutes",

            "Hotspot_Score",

            "Maintenance_Score",

            "Flow_Imbalance",

            "Generated_At"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            recommendations
        )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    for index, route in enumerate(
        recommendations,
        start=1
    ):

        print()
        print(
            f"#{index} "
            f"{route['Route_ID']}"
        )

        print(
            f"   Score         : "
            f"{route['Route_Score']}"
        )

        print(
            f"   Condition     : "
            f"{route['Condition']}"
        )

        print(
            f"   Delay         : "
            f"{route['Estimated_Delay_Minutes']} min"
        )

        print(
            f"   Risk          : "
            f"{route['Risk_Score']}"
        )

        print(
            f"   Hotspot       : "
            f"{route['Hotspot_Score']}"
        )

        print(
            f"   Recommendation: "
            f"{route['Recommendation']}"
        )

    # --------------------------------------------------------
    # Best route
    # --------------------------------------------------------

    best = recommendations[0]

    print()
    print(
        "========================================"
    )

    print(
        "🟢 CURRENT BEST MONITORED ROUTE"
    )

    print(
        f"Route : {best['Route_ID']}"
    )

    print(
        f"Score : {best['Route_Score']}"
    )

    print(
        f"Status: {best['Condition']}"
    )

    print(
        "========================================"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    build_recommendation()
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

ROUTE_RISK_FILE = os.path.join(
    OUTPUT_DIR,
    "route_risk.csv"
)

ROUTE_DELAY_FILE = os.path.join(
    OUTPUT_DIR,
    "route_delay.csv"
)

FLOW_FILE = os.path.join(
    OUTPUT_DIR,
    "vehicle_flow.csv"
)

HOTSPOT_FILE = os.path.join(
    OUTPUT_DIR,
    "incident_hotspots.csv"
)

MAINTENANCE_FILE = os.path.join(
    OUTPUT_DIR,
    "maintenance_prediction.csv"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "route_recommendation.csv"
)


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_float(value, default=0):

    try:

        if value is None:
            return default

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
            return default

        return float(value)

    except (
        ValueError,
        TypeError
    ):

        return default


# ============================================================
# READ CSV
# ============================================================

def read_csv_file(path):

    if not os.path.exists(path):

        return []

    try:

        with open(
            path,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            return list(
                csv.DictReader(file)
            )

    except Exception as error:

        print(
            f"⚠️ Could not read {path}: {error}"
        )

        return []


# ============================================================
# ROUTE NAME
# ============================================================

def get_route(row):

    for field in [
        "Route_ID",
        "Route",
        "Corridor",
        "MONITORED_CORRIDOR"
    ]:

        value = row.get(
            field,
            ""
        )

        if value:

            return str(
                value
            ).strip()

    return "MONITORED_CORRIDOR"


# ============================================================
# LOAD ROUTE DATA
# ============================================================

def load_route_data():

    data = defaultdict(
        lambda: {
            "risk": 0,
            "delay": 0,
            "hotspot": 0,
            "maintenance": 0,
            "flow_imbalance": 0,
            "sources": 0
        }
    )

    # --------------------------------------------------------
    # Route risk
    # --------------------------------------------------------

    for row in read_csv_file(
        ROUTE_RISK_FILE
    ):

        route = get_route(
            row
        )

        data[route]["risk"] = max(
            data[route]["risk"],
            safe_float(
                row.get(
                    "Risk_Score"
                )
            )
        )

        data[route]["sources"] += 1

    # --------------------------------------------------------
    # Route delay
    # --------------------------------------------------------

    for row in read_csv_file(
        ROUTE_DELAY_FILE
    ):

        route = get_route(
            row
        )

        data[route]["delay"] = max(
            data[route]["delay"],
            safe_float(
                row.get(
                    "Estimated_Delay_Minutes"
                )
            )
        )

        data[route]["sources"] += 1

    # --------------------------------------------------------
    # Vehicle flow
    # --------------------------------------------------------

    for row in read_csv_file(
        FLOW_FILE
    ):

        route = get_route(
            row
        )

        imbalance = safe_float(
            row.get(
                "Flow_Imbalance"
            )
        )

        data[route]["flow_imbalance"] = max(
            data[route]["flow_imbalance"],
            imbalance
        )

    # --------------------------------------------------------
    # Hotspots
    # --------------------------------------------------------

    for row in read_csv_file(
        HOTSPOT_FILE
    ):

        route = get_route(
            row
        )

        hotspot_score = safe_float(
            row.get(
                "Hotspot_Score"
            )
        )

        data[route]["hotspot"] = max(
            data[route]["hotspot"],
            hotspot_score
        )

    # --------------------------------------------------------
    # Maintenance
    # --------------------------------------------------------

    for row in read_csv_file(
        MAINTENANCE_FILE
    ):

        route = get_route(
            row
        )

        maintenance_score = safe_float(
            row.get(
                "Maintenance_Score"
            )
        )

        data[route]["maintenance"] = max(
            data[route]["maintenance"],
            maintenance_score
        )

    return data


# ============================================================
# NORMALIZE SCORE
# ============================================================

def normalize(
    value,
    maximum
):

    if maximum <= 0:
        return 0

    return min(
        (
            value
            /
            maximum
        )
        * 100,
        100
    )


# ============================================================
# ROUTE SCORE
# ============================================================

def calculate_route_score(
    route_data,
    max_risk,
    max_delay,
    max_hotspot,
    max_maintenance
):

    risk = normalize(
        route_data["risk"],
        max_risk
    )

    delay = normalize(
        route_data["delay"],
        max_delay
    )

    hotspot = normalize(
        route_data["hotspot"],
        max_hotspot
    )

    maintenance = normalize(
        route_data["maintenance"],
        max_maintenance
    )

    flow = min(
        route_data["flow_imbalance"],
        100
    )

    # --------------------------------------------------------
    # Weighted score
    #
    # Lower = better
    # --------------------------------------------------------

    score = (

        risk * 0.35

        +

        delay * 0.25

        +

        hotspot * 0.15

        +

        maintenance * 0.15

        +

        flow * 0.10
    )

    return round(
        score,
        2
    )


# ============================================================
# ROUTE CONDITION
# ============================================================

def get_condition(score):

    if score >= 75:
        return "CRITICAL"

    if score >= 55:
        return "HIGH RISK"

    if score >= 30:
        return "MODERATE"

    return "GOOD"


# ============================================================
# RECOMMENDATION
# ============================================================

def get_recommendation(
    score
):

    if score >= 75:

        return (
            "AVOID ROUTE - "
            "Critical safety/congestion conditions"
        )

    if score >= 55:

        return (
            "USE WITH CAUTION - "
            "High risk conditions detected"
        )

    if score >= 30:

        return (
            "ACCEPTABLE - "
            "Monitor conditions"
        )

    return (
        "PREFERRED ROUTE"
    )


# ============================================================
# BUILD ROUTE RECOMMENDATION
# ============================================================

def build_recommendation():

    route_data = load_route_data()

    if not route_data:

        print(
            "❌ No route intelligence data found."
        )

        print(
            "Run route_risk.py, route_delay.py, "
            "hotspot_detection.py etc. first."
        )

        return

    print()
    print(
        "========================================"
    )
    print(
        "🧭 DYNAMIC ROUTE RECOMMENDATION"
    )
    print(
        "========================================"
    )

    max_risk = max(
        (
            value["risk"]
            for value in route_data.values()
        ),
        default=1
    )

    max_delay = max(
        (
            value["delay"]
            for value in route_data.values()
        ),
        default=1
    )

    max_hotspot = max(
        (
            value["hotspot"]
            for value in route_data.values()
        ),
        default=1
    )

    max_maintenance = max(
        (
            value["maintenance"]
            for value in route_data.values()
        ),
        default=1
    )

    recommendations = []

    for route, values in route_data.items():

        score = calculate_route_score(
            values,
            max_risk,
            max_delay,
            max_hotspot,
            max_maintenance
        )

        condition = get_condition(
            score
        )

        recommendation = get_recommendation(
            score
        )

        recommendations.append({

            "Route_ID":
                route,

            "Route_Score":
                score,

            "Condition":
                condition,

            "Recommendation":
                recommendation,

            "Risk_Score":
                round(
                    values["risk"],
                    2
                ),

            "Estimated_Delay_Minutes":
                round(
                    values["delay"],
                    2
                ),

            "Hotspot_Score":
                round(
                    values["hotspot"],
                    2
                ),

            "Maintenance_Score":
                round(
                    values["maintenance"],
                    2
                ),

            "Flow_Imbalance":
                round(
                    values["flow_imbalance"],
                    2
                ),

            "Generated_At":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        })

    # --------------------------------------------------------
    # Best route first
    # --------------------------------------------------------

    recommendations.sort(
        key=lambda x:
        x["Route_Score"]
    )

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

            "Route_ID",

            "Route_Score",

            "Condition",

            "Recommendation",

            "Risk_Score",

            "Estimated_Delay_Minutes",

            "Hotspot_Score",

            "Maintenance_Score",

            "Flow_Imbalance",

            "Generated_At"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            recommendations
        )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    for index, route in enumerate(
        recommendations,
        start=1
    ):

        print()
        print(
            f"#{index} "
            f"{route['Route_ID']}"
        )

        print(
            f"   Score         : "
            f"{route['Route_Score']}"
        )

        print(
            f"   Condition     : "
            f"{route['Condition']}"
        )

        print(
            f"   Delay         : "
            f"{route['Estimated_Delay_Minutes']} min"
        )

        print(
            f"   Risk          : "
            f"{route['Risk_Score']}"
        )

        print(
            f"   Hotspot       : "
            f"{route['Hotspot_Score']}"
        )

        print(
            f"   Recommendation: "
            f"{route['Recommendation']}"
        )

    # --------------------------------------------------------
    # Best route
    # --------------------------------------------------------

    best = recommendations[0]

    print()
    print(
        "========================================"
    )

    print(
        "🟢 CURRENT BEST MONITORED ROUTE"
    )

    print(
        f"Route : {best['Route_ID']}"
    )

    print(
        f"Score : {best['Route_Score']}"
    )

    print(
        f"Status: {best['Condition']}"
    )

    print(
        "========================================"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    build_recommendation()