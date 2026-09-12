import os
import csv
from datetime import datetime

# =========================
# PATHS
# =========================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INCIDENT_FILE = os.path.join(
    BASE_DIR,
    "output",
    "incidents.csv"
)

ALERT_FILE = os.path.join(
    BASE_DIR,
    "output",
    "alerts.csv"
)


# =========================
# ALERT ENGINE
# =========================

class AlertEngine:

    def __init__(self):
        os.makedirs(
            os.path.dirname(ALERT_FILE),
            exist_ok=True
        )

        # Create alerts.csv if it doesn't exist
        if not os.path.exists(ALERT_FILE):

            with open(
                ALERT_FILE,
                "w",
                newline=""
            ) as file:

                writer = csv.writer(file)

                writer.writerow([
                    "Alert_ID",
                    "Incident_ID",
                    "Alert_Level",
                    "Incident_Type",
                    "Severity",
                    "Object_ID",
                    "Object_Type",
                    "Confidence",
                    "Video_Time",
                    "Latitude",
                    "Longitude",
                    "Evidence",
                    "Alert_Time",
                    "Status"
                ])

    # =========================
    # SEVERITY → ALERT LEVEL
    # =========================

    def get_alert_level(self, severity):

        severity = str(severity).upper()

        if severity == "HIGH":
            return "CRITICAL"

        elif severity == "MEDIUM":
            return "WARNING"

        elif severity == "LOW":
            return "INFORMATION"

        return "INFORMATION"

    # =========================
    # CREATE ALERT
    # =========================

    def create_alert(self, incident):

        alert_level = self.get_alert_level(
            incident.get("Severity", "LOW")
        )

        # Unique alert ID
        alert_id = (
            "ALT_"
            + datetime.now().strftime("%Y%m%d%H%M%S%f")
        )

        with open(
            ALERT_FILE,
            "a",
            newline=""
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                alert_id,
                incident.get("Incident_ID", "N/A"),
                alert_level,
                incident.get("Type", "UNKNOWN"),
                incident.get("Severity", "LOW"),
                incident.get("Object_ID", "N/A"),
                incident.get("Object_Type", "N/A"),
                incident.get("Confidence", "N/A"),
                incident.get("Video_Time", "N/A"),
                incident.get("Latitude", "N/A"),
                incident.get("Longitude", "N/A"),
                incident.get("Evidence", "N/A"),
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "NEW"
            ])

        print()
        print("========================================")
        print("🚨 CENTRAL ALERT GENERATED")
        print("========================================")
        print(f"Alert ID   : {alert_id}")
        print(f"Incident   : {incident.get('Incident_ID')}")
        print(f"Type       : {incident.get('Type')}")
        print(f"Severity   : {incident.get('Severity')}")
        print(f"Alert Level: {alert_level}")
        print(f"Time       : {incident.get('Video_Time')}")
        print(f"Evidence   : {incident.get('Evidence')}")
        print("========================================")

    # =========================
    # PROCESS INCIDENTS
    # =========================

    def process_incidents(self):

        if not os.path.exists(INCIDENT_FILE):

            print("❌ incidents.csv not found")

            return

        # Existing incidents
        with open(
            INCIDENT_FILE,
            "r",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            incidents = list(reader)

        # Existing alerts
        existing_incidents = set()

        if os.path.exists(ALERT_FILE):

            with open(
                ALERT_FILE,
                "r",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:

                    incident_id = row.get(
                        "Incident_ID"
                    )

                    if incident_id:
                        existing_incidents.add(
                            incident_id
                        )

        # Generate alerts only for new incidents
        new_alerts = 0

        for incident in incidents:

            incident_id = incident.get(
                "Incident_ID"
            )

            if not incident_id:
                continue

            if incident_id in existing_incidents:
                continue

            self.create_alert(incident)

            new_alerts += 1

        print()
        print("========================================")
        print("📡 ALERT ENGINE SUMMARY")
        print("========================================")
        print(f"Incidents found : {len(incidents)}")
        print(f"New alerts      : {new_alerts}")
        print(f"Alert database  : {ALERT_FILE}")
        print("========================================")


# =========================
# RUN
# =========================

if __name__ == "__main__":

    engine = AlertEngine()

    engine.process_incidents()