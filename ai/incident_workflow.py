import os
import csv
from datetime import datetime

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output"
)

INCIDENT_FILE = os.path.join(OUTPUT_DIR, "incidents.csv")
STATUS_FILE = os.path.join(OUTPUT_DIR, "incident_status.csv")


def ensure_status_file():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Incident_ID",
                "Status",
                "Assigned_To",
                "Updated_At",
                "Notes"
            ])


def get_status(incident_id):
    ensure_status_file()

    with open(STATUS_FILE, "r", newline="") as f:
        rows = list(csv.DictReader(f))

    for row in reversed(rows):
        if row["Incident_ID"] == str(incident_id):
            return row

    return {
        "Incident_ID": incident_id,
        "Status": "NEW",
        "Assigned_To": "",
        "Updated_At": "",
        "Notes": ""
    }


def update_status(
    incident_id,
    status,
    assigned_to="",
    notes=""
):
    ensure_status_file()

    allowed = [
        "NEW",
        "ACKNOWLEDGED",
        "ASSIGNED",
        "RESOLVED"
    ]

    status = status.upper()

    if status not in allowed:
        raise ValueError(
            f"Invalid status. Use one of: {allowed}"
        )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    with open(STATUS_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            incident_id,
            status,
            assigned_to,
            timestamp,
            notes
        ])

    return True


def load_latest_statuses():
    ensure_status_file()

    with open(STATUS_FILE, "r", newline="") as f:
        rows = list(csv.DictReader(f))

    latest = {}

    for row in rows:
        latest[row["Incident_ID"]] = row

    return latest


if __name__ == "__main__":

    print("====================================")
    print(" INCIDENT WORKFLOW TEST")
    print("====================================")

    update_status(
        "TEST-001",
        "ACKNOWLEDGED",
        notes="Operator reviewed evidence"
    )

    update_status(
        "TEST-001",
        "ASSIGNED",
        assigned_to="Road Maintenance Team"
    )

    update_status(
        "TEST-001",
        "RESOLVED",
        assigned_to="Road Maintenance Team",
        notes="Issue resolved"
    )

    print(get_status("TEST-001"))