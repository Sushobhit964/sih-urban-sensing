import os
import csv


# ============================================================
# INCIDENT LOGGER
# ============================================================

class IncidentLogger:

    def __init__(self, output_dir="output"):

        self.output_dir = output_dir

        self.evidence_dir = os.path.join(
            output_dir,
            "evidence"
        )

        self.csv_path = os.path.join(
            output_dir,
            "incidents.csv"
        )

        os.makedirs(
            self.evidence_dir,
            exist_ok=True
        )

        # Create CSV if it doesn't exist
        if not os.path.exists(self.csv_path):

            with open(
                self.csv_path,
                "w",
                newline=""
            ) as file:

                writer = csv.writer(file)

                writer.writerow([
                    "Incident_ID",
                    "Type",
                    "Object_ID",
                    "Object_Type",
                    "Severity",
                    "Confidence",
                    "Video_Time",
                    "Latitude",
                    "Longitude",
                    "Evidence"
                ])


    # ========================================================
    # LOG INCIDENT
    # ========================================================

    def log_incident(
        self,
        incident_id,
        incident_type,
        object_id,
        object_type,
        severity,
        confidence,
        video_time,
        latitude="N/A",
        longitude="N/A",
        evidence="N/A"
    ):

        with open(
            self.csv_path,
            "a",
            newline=""
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                incident_id,
                incident_type,
                object_id,
                object_type,
                severity,
                confidence,
                video_time,
                latitude,
                longitude,
                evidence
            ])

        print()
        print("========================================")
        print("🚨 INCIDENT LOGGED")
        print("========================================")
        print(f"Incident   : {incident_id}")
        print(f"Type       : {incident_type}")
        print(f"Object ID  : {object_id}")
        print(f"Object     : {object_type}")
        print(f"Severity   : {severity}")
        print(f"Confidence : {confidence}")
        print(f"Time       : {video_time}")
        print(f"GPS        : {latitude}, {longitude}")
        print(f"Evidence   : {evidence}")
        print("========================================")
