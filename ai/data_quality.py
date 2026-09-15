import os
import csv
import statistics
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

INCIDENT_FILE = "output/incidents.csv"
OUTPUT_FILE = "output/data_quality.csv"

MIN_CONFIDENCE = 0.40
SPIKE_MULTIPLIER = 3.0
LOW_DATA_THRESHOLD = 0
MAX_MISSING_GPS_RATIO = 0.50


# ============================================================
# DATA QUALITY ENGINE
# ============================================================

class DataQualityEngine:

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

        if not os.path.exists(self.incident_file):

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
    # GPS VALIDATION
    # --------------------------------------------------------

    def valid_gps(self, incident):

        lat = self.safe_float(
            incident.get("Latitude")
        )

        lon = self.safe_float(
            incident.get("Longitude")
        )

        if lat is None or lon is None:
            return False

        if not (-90 <= lat <= 90):
            return False

        if not (-180 <= lon <= 180):
            return False

        return True

    # --------------------------------------------------------
    # CONFIDENCE CHECK
    # --------------------------------------------------------

    def confidence_quality(self, incidents):

        values = []

        for incident in incidents:

            confidence = self.safe_float(
                incident.get("Confidence")
            )

            if confidence is not None:
                values.append(confidence)

        if not values:

            return {
                "average": None,
                "low_confidence_ratio": 0
            }

        low_count = sum(
            1
            for value in values
            if value < MIN_CONFIDENCE
        )

        return {
            "average": statistics.mean(values),
            "low_confidence_ratio":
                low_count / len(values)
        }

    # --------------------------------------------------------
    # TIMESTAMP CHECK
    # --------------------------------------------------------

    def timestamp_quality(self, incidents):

        valid = 0
        invalid = 0

        timestamps = []

        for incident in incidents:

            timestamp = incident.get(
                "Video_Time"
            )

            if not timestamp:
                invalid += 1
                continue

            try:

                # Supports numeric video time
                float(timestamp)

                valid += 1
                timestamps.append(
                    float(timestamp)
                )

            except:

                invalid += 1

        # Detect backward timestamps
        backward = 0

        for i in range(1, len(timestamps)):

            if timestamps[i] < timestamps[i - 1]:
                backward += 1

        return {
            "valid": valid,
            "invalid": invalid,
            "backward": backward
        }

    # --------------------------------------------------------
    # DUPLICATE EVENT CHECK
    # --------------------------------------------------------

    def duplicate_check(self, incidents):

        seen = set()
        duplicates = 0

        for incident in incidents:

            key = (
                incident.get("Incident_ID"),
                incident.get("Type"),
                incident.get("Object_ID"),
                incident.get("Video_Time")
            )

            if key in seen:

                duplicates += 1

            else:

                seen.add(key)

        return duplicates

    # --------------------------------------------------------
    # INCIDENT DISTRIBUTION / SPIKE CHECK
    # --------------------------------------------------------

    def spike_check(self, incidents):

        if not incidents:

            return {
                "max_type_count": 0,
                "average_type_count": 0,
                "spike_detected": False
            }

        type_counts = {}

        for incident in incidents:

            incident_type = incident.get(
                "Type",
                "UNKNOWN"
            )

            type_counts[incident_type] = (
                type_counts.get(
                    incident_type,
                    0
                ) + 1
            )

        counts = list(
            type_counts.values()
        )

        average_count = (
            statistics.mean(counts)
            if counts else 0
        )

        max_count = (
            max(counts)
            if counts else 0
        )

        spike_detected = (
            average_count > 0
            and max_count
            >= average_count * SPIKE_MULTIPLIER
        )

        return {
            "max_type_count": max_count,
            "average_type_count": average_count,
            "spike_detected": spike_detected
        }

    # --------------------------------------------------------
    # BUILD QUALITY RESULT
    # --------------------------------------------------------

    def analyze(self):

        incidents = self.load_incidents()

        if not incidents:

            return []

        total = len(incidents)

        # GPS
        valid_gps_count = sum(
            1
            for incident in incidents
            if self.valid_gps(incident)
        )

        missing_gps_count = (
            total - valid_gps_count
        )

        missing_gps_ratio = (
            missing_gps_count / total
        )

        # Confidence
        confidence = (
            self.confidence_quality(
                incidents
            )
        )

        # Timestamp
        timestamp = (
            self.timestamp_quality(
                incidents
            )
        )

        # Duplicates
        duplicates = (
            self.duplicate_check(
                incidents
            )
        )

        # Spikes
        spike = (
            self.spike_check(
                incidents
            )
        )

        # ----------------------------------------------------
        # QUALITY SCORE
        # ----------------------------------------------------

        score = 100

        # GPS penalty
        if missing_gps_ratio > 0:
            score -= min(
                30,
                missing_gps_ratio * 30
            )

        # Confidence penalty
        score -= min(
            25,
            confidence[
                "low_confidence_ratio"
            ] * 25
        )

        # Timestamp penalty
        if timestamp["invalid"] > 0:

            score -= min(
                15,
                (
                    timestamp["invalid"]
                    / total
                ) * 15
            )

        # Duplicate penalty
        if duplicates > 0:

            score -= min(
                15,
                (
                    duplicates
                    / total
                ) * 15
            )

        # Spike penalty
        if spike["spike_detected"]:

            score -= 15

        score = max(
            0,
            round(score, 2)
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        anomaly_reasons = []

        if missing_gps_ratio > MAX_MISSING_GPS_RATIO:

            anomaly_reasons.append(
                "HIGH_MISSING_GPS"
            )

        if (
            confidence["low_confidence_ratio"]
            > 0.50
        ):

            anomaly_reasons.append(
                "LOW_AI_CONFIDENCE"
            )

        if timestamp["invalid"] > 0:

            anomaly_reasons.append(
                "INVALID_TIMESTAMP"
            )

        if timestamp["backward"] > 0:

            anomaly_reasons.append(
                "TIMESTAMP_ORDER_ERROR"
            )

        if duplicates > 0:

            anomaly_reasons.append(
                "DUPLICATE_EVENTS"
            )

        if spike["spike_detected"]:

            anomaly_reasons.append(
                "DETECTION_SPIKE"
            )

        if score >= 80:

            status = "NORMAL"

        elif score >= 60:

            status = "WARNING"

        else:

            status = "ANOMALY"

        if not anomaly_reasons:

            anomaly_reasons.append(
                "NO_SIGNIFICANT_ANOMALY"
            )

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        result = {

            "Analysis_ID":
                "DQ-" +
                datetime.now().strftime(
                    "%Y%m%d%H%M%S"
                ),

            "Analysis_Time":
                datetime.now().isoformat(),

            "Total_Events":
                total,

            "Valid_GPS_Events":
                valid_gps_count,

            "Missing_GPS_Events":
                missing_gps_count,

            "Missing_GPS_Ratio":
                round(
                    missing_gps_ratio * 100,
                    2
                ),

            "Average_Confidence":
                round(
                    confidence["average"],
                    4
                )
                if confidence["average"]
                is not None
                else "N/A",

            "Low_Confidence_Ratio":
                round(
                    confidence[
                        "low_confidence_ratio"
                    ] * 100,
                    2
                ),

            "Invalid_Timestamps":
                timestamp["invalid"],

            "Timestamp_Order_Errors":
                timestamp["backward"],

            "Duplicate_Events":
                duplicates,

            "Detection_Spike":
                "YES"
                if spike["spike_detected"]
                else "NO",

            "Data_Quality_Score":
                score,

            "Status":
                status,

            "Anomaly_Reasons":
                ";".join(
                    anomaly_reasons
                )
        }

        return [result]

    # --------------------------------------------------------
    # SAVE RESULT
    # --------------------------------------------------------

    def save(self, results):

        if not results:
            return

        fieldnames = list(
            results[0].keys()
        )

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

            writer.writerows(results)

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    def run(self):

        print()
        print("========================================")
        print("📊 DATA QUALITY & ANOMALY ENGINE")
        print("========================================")

        results = self.analyze()

        if not results:

            print(
                "⚠️ No incident data available."
            )

            return

        self.save(results)

        result = results[0]

        print()
        print(
            f"Events             : "
            f"{result['Total_Events']}"
        )

        print(
            f"Missing GPS        : "
            f"{result['Missing_GPS_Ratio']}%"
        )

        print(
            f"Average Confidence : "
            f"{result['Average_Confidence']}"
        )

        print(
            f"Duplicates         : "
            f"{result['Duplicate_Events']}"
        )

        print(
            f"Detection Spike    : "
            f"{result['Detection_Spike']}"
        )

        print(
            f"Quality Score      : "
            f"{result['Data_Quality_Score']}/100"
        )

        print(
            f"Status             : "
            f"{result['Status']}"
        )

        print(
            f"Reasons            : "
            f"{result['Anomaly_Reasons']}"
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

    engine = DataQualityEngine()

    engine.run()