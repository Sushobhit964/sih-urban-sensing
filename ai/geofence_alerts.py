import os
import csv
import math
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

INCIDENT_FILE = "output/incidents.csv"
OUTPUT_FILE = "output/geofence_alerts.csv"

# Prototype geofences.
# Replace these coordinates with actual city GIS coordinates
# during deployment.
GEOFENCES = [
    {
        "Zone_ID": "ZONE-001",
        "Zone_Name": "Central Critical Zone",
        "Latitude": 22.7196,
        "Longitude": 75.8577,
        "Radius_M": 500,
        "Priority": "CRITICAL",
        "Escalation_Boost": 30
    },
    {
        "Zone_ID": "ZONE-002",
        "Zone_Name": "School Safety Zone",
        "Latitude": 22.7250,
        "Longitude": 75.8500,
        "Radius_M": 300,
        "Priority": "HIGH",
        "Escalation_Boost": 25
    },
    {
        "Zone_ID": "ZONE-003",
        "Zone_Name": "Hospital Safety Zone",
        "Latitude": 22.7100,
        "Longitude": 75.8650,
        "Radius_M": 300,
        "Priority": "HIGH",
        "Escalation_Boost": 25
    }
]


# ============================================================
# GEOSPATIAL FUNCTIONS
# ============================================================

def haversine_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Calculate distance between two GPS coordinates.
    Returns meters.
    """

    earth_radius = 6371000

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = math.radians(
        lat2 - lat1
    )

    delta_lon = math.radians(
        lon2 - math.radians(lon1)
        if False
        else lon2 - math.degrees(
            math.radians(lon1)
        )
    )

    # Recalculate longitude correctly
    lon1_rad = math.radians(lon1)
    lon2_rad = math.radians(lon2)

    delta_lon = lon2_rad - lon1_rad

    a = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius * c


# ============================================================
# ALERT ENGINE
# ============================================================

class GeofenceAlertEngine:

    def __init__(
        self,
        incident_file=INCIDENT_FILE,
        output_file=OUTPUT_FILE
    ):

        self.incident_file = incident_file
        self.output_file = output_file

        os.makedirs(
            os.path.dirname(output_file),
            exist_ok=True
        )

    # --------------------------------------------------------
    # LOAD INCIDENTS
    # --------------------------------------------------------

    def load_incidents(self):

        if not os.path.exists(
            self.incident_file
        ):

            print(
                f"❌ Incident file not found: "
                f"{self.incident_file}"
            )

            return []

        with open(
            self.incident_file,
            "r",
            newline=""
        ) as file:

            return list(
                csv.DictReader(file)
            )

    # --------------------------------------------------------
    # SAFE FLOAT
    # --------------------------------------------------------

    def safe_float(self, value):

        try:
            return float(value)

        except:
            return None

    # --------------------------------------------------------
    # FIND GEOFENCE
    # --------------------------------------------------------

    def find_geofence(
        self,
        latitude,
        longitude
    ):

        matched = []

        for zone in GEOFENCES:

            distance = haversine_distance(
                latitude,
                longitude,
                zone["Latitude"],
                zone["Longitude"]
            )

            if distance <= zone["Radius_M"]:

                matched.append(
                    (
                        zone,
                        distance
                    )
                )

        if not matched:

            return None

        # If multiple zones overlap,
        # choose the highest-priority one.
        priority_order = {
            "CRITICAL": 3,
            "HIGH": 2,
            "MEDIUM": 1,
            "LOW": 0
        }

        matched.sort(
            key=lambda item:
            priority_order.get(
                item[0]["Priority"],
                0
            ),
            reverse=True
        )

        return matched[0]

    # --------------------------------------------------------
    # INCIDENT SEVERITY SCORE
    # --------------------------------------------------------

    def severity_score(
        self,
        severity
    ):

        severity = str(
            severity
        ).upper()

        values = {
            "CRITICAL": 100,
            "HIGH": 75,
            "MEDIUM": 50,
            "LOW": 25
        }

        return values.get(
            severity,
            25
        )

    # --------------------------------------------------------
    # CREATE ESCALATED LEVEL
    # --------------------------------------------------------

    def escalation_level(
        self,
        incident,
        zone
    ):

        incident_severity = str(
            incident.get(
                "Severity",
                "LOW"
            )
        ).upper()

        base_score = self.severity_score(
            incident_severity
        )

        score = min(
            100,
            base_score
            + zone["Escalation_Boost"]
        )

        if score >= 90:

            return "CRITICAL", score

        if score >= 70:

            return "HIGH", score

        if score >= 40:

            return "MEDIUM", score

        return "LOW", score

    # --------------------------------------------------------
    # ANALYZE
    # --------------------------------------------------------

    def analyze(self):

        incidents = self.load_incidents()

        if not incidents:

            return []

        alerts = []

        for incident in incidents:

            latitude = self.safe_float(
                incident.get(
                    "Latitude"
                )
            )

            longitude = self.safe_float(
                incident.get(
                    "Longitude"
                )
            )

            # No GPS → cannot geofence
            if (
                latitude is None
                or longitude is None
            ):

                continue

            # Ignore invalid coordinates
            if not (
                -90 <= latitude <= 90
                and
                -180 <= longitude <= 180
            ):

                continue

            match = self.find_geofence(
                latitude,
                longitude
            )

            if match is None:

                continue

            zone, distance = match

            alert_level, score = (
                self.escalation_level(
                    incident,
                    zone
                )
            )

            alert_id = (
                "GEO-"
                + datetime.now().strftime(
                    "%Y%m%d%H%M%S"
                )
                + "-"
                + str(
                    len(alerts) + 1
                ).zfill(3)
            )

            alert = {

                "Alert_ID":
                    alert_id,

                "Incident_ID":
                    incident.get(
                        "Incident_ID",
                        "UNKNOWN"
                    ),

                "Incident_Type":
                    incident.get(
                        "Type",
                        "UNKNOWN"
                    ),

                "Object_ID":
                    incident.get(
                        "Object_ID",
                        "UNKNOWN"
                    ),

                "Original_Severity":
                    incident.get(
                        "Severity",
                        "UNKNOWN"
                    ),

                "Geofence_ID":
                    zone["Zone_ID"],

                "Geofence_Name":
                    zone["Zone_Name"],

                "Geofence_Priority":
                    zone["Priority"],

                "Distance_From_Zone_Center_M":
                    round(
                        distance,
                        2
                    ),

                "Escalation_Score":
                    round(
                        score,
                        2
                    ),

                "Alert_Level":
                    alert_level,

                "Confidence":
                    incident.get(
                        "Confidence",
                        "N/A"
                    ),

                "Video_Time":
                    incident.get(
                        "Video_Time",
                        "N/A"
                    ),

                "Latitude":
                    latitude,

                "Longitude":
                    longitude,

                "Evidence":
                    incident.get(
                        "Evidence",
                        "N/A"
                    ),

                "Alert_Time":
                    datetime.now().isoformat(),

                "Status":
                    "ACTIVE"
            }

            alerts.append(alert)

        return alerts

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    def save(self, alerts):

        fieldnames = [

            "Alert_ID",
            "Incident_ID",
            "Incident_Type",
            "Object_ID",
            "Original_Severity",
            "Geofence_ID",
            "Geofence_Name",
            "Geofence_Priority",
            "Distance_From_Zone_Center_M",
            "Escalation_Score",
            "Alert_Level",
            "Confidence",
            "Video_Time",
            "Latitude",
            "Longitude",
            "Evidence",
            "Alert_Time",
            "Status"
        ]

        with open(
            self.output_file,
            "w",
            newline=""
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames
            )

            writer.writeheader()

            writer.writerows(
                alerts
            )

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    def run(self):

        print()
        print("========================================")
        print("📍 GEOFENCE ALERT ENGINE")
        print("========================================")

        alerts = self.analyze()

        self.save(alerts)

        print(
            f"Incidents checked : "
            f"{len(self.load_incidents())}"
        )

        print(
            f"Geofence alerts   : "
            f"{len(alerts)}"
        )

        critical = sum(
            1
            for alert in alerts
            if alert["Alert_Level"]
            == "CRITICAL"
        )

        high = sum(
            1
            for alert in alerts
            if alert["Alert_Level"]
            == "HIGH"
        )

        print(
            f"Critical alerts   : "
            f"{critical}"
        )

        print(
            f"High alerts       : "
            f"{high}"
        )

        print()
        print(
            f"💾 Saved to: "
            f"{self.output_file}"
        )

        print("========================================")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    engine = GeofenceAlertEngine()

    engine.run()