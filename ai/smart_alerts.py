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

SMART_ALERT_FILE = os.path.join(
    OUTPUT_DIR,
    "smart_alerts.csv"
)


# ============================================================
# TYPE IMPORTANCE
# ============================================================

TYPE_SCORE = {
    "PEDESTRIAN_RISK": 35,
    "WRONG_WAY": 35,
    "WATERLOGGING": 30,
    "ROAD_DAMAGE": 25,
    "POTHOLE": 25,
    "RASH_DRIVING": 30,
    "CONGESTION": 20,
    "TRAFFIC": 15,
}


def normalize_type(value):

    value = str(value).upper()

    if "PEDESTRIAN" in value:
        return "PEDESTRIAN_RISK"

    if "WRONG" in value:
        return "WRONG_WAY"

    if "WATER" in value:
        return "WATERLOGGING"

    if "POTHOLE" in value:
        return "POTHOLE"

    if "ROAD_DAMAGE" in value:
        return "ROAD_DAMAGE"

    if "RASH" in value:
        return "RASH_DRIVING"

    if "CONGESTION" in value:
        return "CONGESTION"

    if "TRAFFIC" in value:
        return "TRAFFIC"

    return "OTHER"


def severity_score(severity):

    severity = str(severity).upper()

    return {
        "LOW": 10,
        "MEDIUM": 25,
        "HIGH": 40
    }.get(severity, 5)


def confidence_score(confidence):

    try:
        value = float(confidence)

        if value > 1:
            value = value / 100

        return value * 15

    except Exception:
        return 5


def calculate_priority(row):

    incident_type = normalize_type(
        row.get("Type", "OTHER")
    )

    severity = row.get(
        "Severity",
        "LOW"
    )

    type_score = TYPE_SCORE.get(
        incident_type,
        5
    )

    sev_score = severity_score(
        severity
    )

    conf_score = confidence_score(
        row.get("Confidence", 0)
    )

    score = (
        type_score
        + sev_score
        + conf_score
    )

    return min(round(score, 1), 100)


def priority_level(score):

    if score >= 75:
        return "CRITICAL"

    if score >= 55:
        return "HIGH"

    if score >= 30:
        return "MEDIUM"

    return "LOW"


def generate_alerts():

    if not os.path.exists(INCIDENT_FILE):

        print(
            "No incidents.csv found."
        )

        return

    df = pd.read_csv(
        INCIDENT_FILE
    )

    if df.empty:
        print(
            "No incidents available."
        )

        return

    df["Priority_Score"] = (
        df.apply(
            calculate_priority,
            axis=1
        )
    )

    df["Alert_Level"] = (
        df["Priority_Score"]
        .apply(priority_level)
    )

    df["Incident_Category"] = (
        df["Type"]
        .apply(normalize_type)
    )

    columns = [
        "Incident_ID",
        "Incident_Category",
        "Object_ID",
        "Object_Type",
        "Severity",
        "Confidence",
        "Priority_Score",
        "Alert_Level",
        "Video_Time",
        "Latitude",
        "Longitude",
        "Evidence"
    ]

    columns = [
        c for c in columns
        if c in df.columns
    ]

    result = df[columns].copy()

    result = result.sort_values(
        "Priority_Score",
        ascending=False
    )

    result.to_csv(
        SMART_ALERT_FILE,
        index=False
    )

    print()
    print("====================================")
    print(" SMART ALERT ENGINE")
    print("====================================")

    print(
        result[
            [
                "Incident_ID",
                "Incident_Category",
                "Priority_Score",
                "Alert_Level"
            ]
        ].head(15).to_string(
            index=False
        )
    )

    print()
    print(
        f"Saved: {SMART_ALERT_FILE}"
    )


if __name__ == "__main__":
    generate_alerts()