import cv2
import os
import csv
import numpy as np

from incident_logger import IncidentLogger


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

# Change this to your waterlogging video when available.
VIDEO_PATH = os.path.join(
    BASE_DIR,
    "data",
    "input",
    "c.mp4"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

WATER_DIR = os.path.join(
    OUTPUT_DIR,
    "waterlogging"
)

EVIDENCE_DIR = os.path.join(
    WATER_DIR,
    "evidence"
)

CSV_PATH = os.path.join(
    WATER_DIR,
    "waterlogging.csv"
)

os.makedirs(
    EVIDENCE_DIR,
    exist_ok=True
)


# ============================================================
# INCIDENT LOGGER
# ============================================================

incident_logger = IncidentLogger(
    OUTPUT_DIR
)


# ============================================================
# CSV
# ============================================================

if not os.path.exists(CSV_PATH):

    with open(
        CSV_PATH,
        "w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Incident_ID",
            "Water_Score",
            "Coverage",
            "Risk_Level",
            "Video_Time",
            "Evidence_File"
        ])


# ============================================================
# VIDEO
# ============================================================

cap = cv2.VideoCapture(
    VIDEO_PATH
)

if not cap.isOpened():

    print("ERROR: Could not open video")
    exit()


fps = cap.get(
    cv2.CAP_PROP_FPS
)

if fps <= 0:
    fps = 30


# ============================================================
# PARAMETERS
# ============================================================

# Only analyse the lower portion of the image because
# waterlogging on roads generally appears in the road area.

ROAD_START_RATIO = 0.45


# Percentage of road-region pixels that must satisfy
# water-like visual characteristics.

LOW_COVERAGE = 0.10
MEDIUM_COVERAGE = 0.25
HIGH_COVERAGE = 0.40


# Avoid logging the same continuous waterlogging event
# every frame.

EVENT_INTERVAL = 5.0


last_event_time = -999


# ============================================================
# STATISTICS
# ============================================================

frame_number = 0

detections = 0

high_events = 0
medium_events = 0


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = cap.read()

    if not success:
        break

    frame_number += 1

    height, width = frame.shape[:2]


    # ========================================================
    # VIDEO TIME
    # ========================================================

    video_seconds = (
        frame_number / fps
    )

    minutes = int(
        video_seconds // 60
    )

    seconds = (
        video_seconds % 60
    )

    video_time = (
        f"{minutes:02d}:{seconds:05.2f}"
    )


    # ========================================================
    # ROAD REGION
    # ========================================================

    road_start = int(
        height * ROAD_START_RATIO
    )

    road = frame[
        road_start:height,
        0:width
    ]


    # ========================================================
    # HSV ANALYSIS
    # ========================================================

    hsv = cv2.cvtColor(
        road,
        cv2.COLOR_BGR2HSV
    )

    h, s, v = cv2.split(hsv)


    # ========================================================
    # WATER-LIKE PIXELS
    #
    # This is a heuristic, not a trained classifier.
    #
    # We look for relatively dark / low-saturation regions
    # that can correspond to reflective standing water.
    # ========================================================

    dark_mask = (
        v < 150
    )

    low_saturation = (
        s < 100
    )


    water_mask = (
        dark_mask &
        low_saturation
    )


    # ========================================================
    # REMOVE SMALL NOISE
    # ========================================================

    kernel = np.ones(
        (7, 7),
        np.uint8
    )

    water_mask = cv2.morphologyEx(
        water_mask.astype(np.uint8),
        cv2.MORPH_OPEN,
        kernel
    )

    water_mask = cv2.morphologyEx(
        water_mask,
        cv2.MORPH_CLOSE,
        kernel
    )


    # ========================================================
    # COVERAGE
    # ========================================================

    total_pixels = (
        water_mask.shape[0] *
        water_mask.shape[1]
    )

    water_pixels = np.count_nonzero(
        water_mask
    )

    coverage = (
        water_pixels /
        total_pixels
    )


    # ========================================================
    # SCORE
    # ========================================================

    water_score = (
        coverage * 100
    )


    # ========================================================
    # CLASSIFICATION
    # ========================================================

    if coverage < LOW_COVERAGE:

        risk_level = "LOW"

    elif coverage < MEDIUM_COVERAGE:

        risk_level = "MEDIUM"

    elif coverage < HIGH_COVERAGE:

        risk_level = "HIGH"

    else:

        risk_level = "HIGH"


    # ========================================================
    # ONLY CONSIDER MEDIUM/HIGH
    # ========================================================

    if risk_level in [
        "MEDIUM",
        "HIGH"
    ]:

        detections += 1


        # ====================================================
        # EVIDENCE / INCIDENT INTERVAL
        # ====================================================

        if (
            video_seconds -
            last_event_time
            >= EVENT_INTERVAL
        ):

            last_event_time = (
                video_seconds
            )


            evidence_name = (
                f"waterlogging_"
                f"{frame_number}.jpg"
            )

            evidence_path = os.path.join(
                EVIDENCE_DIR,
                evidence_name
            )


            # Draw overlay before saving
            display_frame = frame.copy()


            cv2.putText(
                display_frame,
                "WATERLOGGING / ROAD HAZARD",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )


            cv2.putText(
                display_frame,
                f"Risk: {risk_level}",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )


            cv2.putText(
                display_frame,
                f"Water score: {water_score:.1f}",
                (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )


            cv2.imwrite(
                evidence_path,
                display_frame
            )


            # =================================================
            # CSV
            # =================================================

            incident_id = (
                f"WATER_{frame_number}"
            )


            with open(
                CSV_PATH,
                "a",
                newline=""
            ) as file:

                writer = csv.writer(
                    file
                )

                writer.writerow([
                    incident_id,
                    round(
                        water_score,
                        2
                    ),
                    round(
                        coverage * 100,
                        2
                    ),
                    risk_level,
                    video_time,
                    evidence_path
                ])


            # =================================================
            # CENTRAL INCIDENT
            # =================================================

            incident_logger.log_incident(

                incident_id=incident_id,

                incident_type=(
                    "WATERLOGGING"
                ),

                object_id="ROAD_ZONE",

                object_type="Water",

                severity=risk_level,

                confidence=round(
                    min(
                        water_score / 100,
                        1.0
                    ),
                    2
                ),

                video_time=video_time,

                latitude="N/A",

                longitude="N/A",

                evidence=evidence_path
            )


            if risk_level == "HIGH":

                high_events += 1

            else:

                medium_events += 1


            print()
            print(
                "🚨 WATERLOGGING DETECTED"
            )

            print(
                f"Risk       : {risk_level}"
            )

            print(
                f"Score      : {water_score:.1f}"
            )

            print(
                f"Coverage   : {coverage * 100:.1f}%"
            )

            print(
                f"Time       : {video_time}"
            )

            print(
                f"Evidence   : {evidence_path}"
            )


    # ========================================================
    # VISUALIZATION
    # ========================================================

    overlay = frame.copy()


    # Show analysed road region
    cv2.rectangle(
        overlay,
        (0, road_start),
        (width - 1, height - 1),
        (255, 255, 255),
        2
    )


    # ========================================================
    # INFORMATION PANEL
    # ========================================================

    cv2.rectangle(
        overlay,
        (10, 10),
        (390, 125),
        (0, 0, 0),
        -1
    )


    cv2.putText(
        overlay,
        "WATERLOGGING AI",
        (20, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )


    cv2.putText(
        overlay,
        f"Water score: {water_score:.1f}",
        (20, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.putText(
        overlay,
        f"Coverage: {coverage * 100:.1f}%",
        (20, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.putText(
        overlay,
        f"Risk: {risk_level}",
        (20, 115),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.imshow(
        "Waterlogging Detection",
        overlay
    )


    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ============================================================
# CLEANUP
# ============================================================

cap.release()

cv2.destroyAllWindows()


# ============================================================
# SUMMARY
# ============================================================

print()
print("========================================")
print("WATERLOGGING ANALYSIS COMPLETE")
print("========================================")

print(
    f"Frames processed : {frame_number}"
)

print(
    f"Detected frames  : {detections}"
)

print(
    f"Medium events    : {medium_events}"
)

print(
    f"High events      : {high_events}"
)

print()
print("Created:")

print(
    f"- {CSV_PATH}"
)

print(
    f"- {EVIDENCE_DIR}"
)

print(
    f"- {os.path.join(OUTPUT_DIR, 'incidents.csv')}"
)

print("========================================")