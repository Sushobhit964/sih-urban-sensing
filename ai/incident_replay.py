import os
import pandas as pd


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


def load_incidents():

    if not os.path.exists(
        INCIDENT_FILE
    ):
        return pd.DataFrame()

    try:
        return pd.read_csv(
            INCIDENT_FILE
        )

    except Exception:
        return pd.DataFrame()


def resolve_evidence_path(path):

    if not isinstance(path, str):
        return None

    path = path.strip()

    if path in [
        "",
        "N/A",
        "nan",
        "None"
    ]:
        return None

    if os.path.isabs(path):
        full_path = path

    else:
        full_path = os.path.join(
            BASE_DIR,
            path
        )

    if os.path.exists(full_path):
        return full_path

    return None


def get_incident_replay(
    incident_id
):

    df = load_incidents()

    if df.empty:
        return []

    if "Incident_ID" not in df.columns:
        return []

    rows = df[
        df["Incident_ID"]
        .astype(str)
        == str(incident_id)
    ]

    if rows.empty:
        return []

    replay = []

    for _, row in rows.iterrows():

        evidence = resolve_evidence_path(
            row.get("Evidence")
        )

        replay.append({
            "Incident_ID":
                row.get("Incident_ID"),

            "Type":
                row.get("Type"),

            "Severity":
                row.get("Severity"),

            "Object_ID":
                row.get("Object_ID"),

            "Video_Time":
                row.get("Video_Time"),

            "Confidence":
                row.get("Confidence"),

            "Evidence":
                evidence
        })

    return replay


if __name__ == "__main__":

    df = load_incidents()

    if df.empty:

        print(
            "No incidents found."
        )

    else:

        incident_id = str(
            df.iloc[-1]["Incident_ID"]
        )

        replay = get_incident_replay(
            incident_id
        )

        print()
        print(
            "===================================="
        )
        print(
            " INCIDENT REPLAY"
        )
        print(
            "===================================="
        )

        for item in replay:

            print(
                f"Incident : {item['Incident_ID']}"
            )

            print(
                f"Type     : {item['Type']}"
            )

            print(
                f"Severity : {item['Severity']}"
            )

            print(
                f"Time     : {item['Video_Time']}"
            )

            print(
                f"Evidence : {item['Evidence']}"
            )

            print(
                "------------------------------------"
            )