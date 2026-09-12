import os
import pandas as pd


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

OUTPUT_DIR = os.path.join(BASE_DIR, "output")

INCIDENT_FILE = os.path.join(
    OUTPUT_DIR,
    "incidents.csv"
)

RISK_FILE = os.path.join(
    OUTPUT_DIR,
    "road_risk.csv"
)


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


SEVERITY_WEIGHTS = {
    "LOW": 1.0,
    "MEDIUM": 1.5,
    "HIGH": 2.0
}


def load_incidents():

    if not os.path.exists(INCIDENT_FILE):
        return pd.DataFrame()

    try:
        return pd.read_csv(INCIDENT_FILE)
    except Exception:
        return pd.DataFrame()


def normalize_type(value):

    value = str(value).upper()

    if "POTHOLE" in value:
        return "POTHOLE"

    if "ROAD_DAMAGE" in value:
        return "ROAD_DAMAGE"

    if "PEDESTRIAN" in value:
        return "PEDESTRIAN_RISK"

    if "WATER" in value:
        return "WATERLOGGING"

    if "RASH" in value:
        return "RASH_DRIVING"

    if "WRONG" in value:
        return "WRONG_WAY"

    if "CONGESTION" in value:
        return "CONGESTION"

    if "TRAFFIC" in value:
        return "TRAFFIC"

    return "OTHER"


def calculate_score(group):

    score = 0

    for _, row in group.iterrows():

        incident_type = normalize_type(
            row.get("Type", "OTHER")
        )

        severity = str(
            row.get("Severity", "LOW")
        ).upper()

        base = TYPE_WEIGHTS.get(
            incident_type,
            5
        )

        severity_multiplier = SEVERITY_WEIGHTS.get(
            severity,
            1.0
        )

        score += base * severity_multiplier

    # Prevent unlimited score
    score = min(score, 100)

    return round(score, 1)


def risk_level(score):

    if score >= 70:
        return "CRITICAL"

    if score >= 45:
        return "HIGH"

    if score >= 20:
        return "MEDIUM"

    return "LOW"


def generate_risk_scores():

    df = load_incidents()

    if df.empty:
        print("No incidents found.")
        return pd.DataFrame()

    # --------------------------------------------------------
    # Create a zone
    # --------------------------------------------------------

    if (
        "Latitude" in df.columns
        and "Longitude" in df.columns
    ):

        df["Latitude"] = pd.to_numeric(
            df["Latitude"],
            errors="coerce"
        )

        df["Longitude"] = pd.to_numeric(
            df["Longitude"],
            errors="coerce"
        )

        valid_gps = df.dropna(
            subset=["Latitude", "Longitude"]
        )

        if not valid_gps.empty:

            # Approximate spatial zones
            valid_gps = valid_gps.copy()

            valid_gps["Zone"] = (
                valid_gps["Latitude"].round(3).astype(str)
                + "_"
                + valid_gps["Longitude"].round(3).astype(str)
            )

            df = valid_gps

        else:
            df["Zone"] = "UNMAPPED"

    else:
        df["Zone"] = "UNMAPPED"

    results = []

    for zone, group in df.groupby("Zone"):

        score = calculate_score(group)

        results.append({
            "Zone": zone,
            "Incident_Count": len(group),
            "High_Severity": int(
                (
                    group["Severity"]
                    .astype(str)
                    .str.upper()
                    == "HIGH"
                ).sum()
            ),
            "Risk_Score": score,
            "Risk_Level": risk_level(score)
        })

    result = pd.DataFrame(results)

    result = result.sort_values(
        "Risk_Score",
        ascending=False
    )

    result.to_csv(
        RISK_FILE,
        index=False
    )

    print()
    print("====================================")
    print(" ROAD RISK ANALYSIS")
    print("====================================")

    print(result.to_string(index=False))

    print()
    print(f"Saved: {RISK_FILE}")

    return result


if __name__ == "__main__":
    generate_risk_scores()