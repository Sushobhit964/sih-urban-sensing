import cv2
import os
import csv
import math
from ultralytics import YOLO

from incident_logger import IncidentLogger


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "yolo11n.pt"
)

VIDEO_PATH = os.path.join(
    BASE_DIR,
    "data",
    "input",
    "d.mp4"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

RISK_DIR = os.path.join(
    OUTPUT_DIR,
    "pedestrian_risk"
)

EVIDENCE_DIR = os.path.join(
    RISK_DIR,
    "evidence"
)

CSV_PATH = os.path.join(
    RISK_DIR,
    "pedestrian_risk.csv"
)

os.makedirs(
    EVIDENCE_DIR,
    exist_ok=True
)


# ============================================================
# LOAD MODEL
# ============================================================

print()
print("========================================")
print("PEDESTRIAN RISK DETECTION")
print("========================================")

model = YOLO(MODEL_PATH)

print("Model loaded.")
print("Classes:", model.names)


# ============================================================
# VIDEO
# ============================================================

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():

    print("ERROR: Could not open video")

    exit()


fps = cap.get(
    cv2.CAP_PROP_FPS
)

if fps <= 0:
    fps = 30


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
            "Person_ID",
            "Vehicle_ID",
            "Vehicle_Type",
            "Distance",
            "Risk_Level",
            "Confidence",
            "Video_Time",
            "Evidence_File"
        ])


# ============================================================
# COCO CLASSES
# ============================================================

PERSON_CLASS = 0

VEHICLE_CLASSES = {
    1: "Bicycle",
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}


# ============================================================
# RISK PARAMETERS
# ============================================================

# Distance is measured in pixels.
#
# This is NOT a real-world meter measurement.
# Camera calibration can be added later.

HIGH_RISK_DISTANCE = 80

MEDIUM_RISK_DISTANCE = 140


# ============================================================
# TRACKING
# ============================================================

logged_risks = set()


# ============================================================
# STATISTICS
# ============================================================

frame_number = 0

person_frames = 0

risk_events = 0

high_risk_events = 0

medium_risk_events = 0


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = cap.read()

    if not success:
        break

    frame_number += 1

    height, width = frame.shape[:2]

    video_seconds = frame_number / fps

    minutes = int(
        video_seconds // 60
    )

    seconds = video_seconds % 60

    video_time = (
        f"{minutes:02d}:{seconds:05.2f}"
    )


    # ========================================================
    # YOLO TRACKING
    # ========================================================

    results = model.track(
        frame,
        persist=True,
        classes=[
            PERSON_CLASS,
            *VEHICLE_CLASSES.keys()
        ],
        conf=0.25,
        verbose=False
    )


    if not results:
        continue


    result = results[0]


    if result.boxes is None:
        continue


    boxes = result.boxes


    if len(boxes) == 0:
        continue


    # ========================================================
    # TRACK IDS
    # ========================================================

    if boxes.id is not None:

        track_ids = (
            boxes.id
            .cpu()
            .numpy()
            .astype(int)
        )

    else:

        track_ids = list(
            range(len(boxes))
        )


    xyxy = (
        boxes.xyxy
        .cpu()
        .numpy()
    )

    classes = (
        boxes.cls
        .cpu()
        .numpy()
        .astype(int)
    )

    confidences = (
        boxes.conf
        .cpu()
        .numpy()
    )


    # ========================================================
    # STORE PEOPLE AND VEHICLES
    # ========================================================

    people = []

    vehicles = []


    for track_id, box, class_id, confidence in zip(
        track_ids,
        xyxy,
        classes,
        confidences
    ):

        x1, y1, x2, y2 = map(
            int,
            box
        )

        center_x = int(
            (x1 + x2) / 2
        )

        center_y = int(
            (y1 + y2) / 2
        )


        # ----------------------------------------------------
        # PERSON
        # ----------------------------------------------------

        if class_id == PERSON_CLASS:

            people.append({
                "id": int(track_id),
                "box": (x1, y1, x2, y2),
                "center": (
                    center_x,
                    center_y
                ),
                "confidence": float(confidence)
            })

            person_frames += 1


        # ----------------------------------------------------
        # VEHICLE
        # ----------------------------------------------------

        elif class_id in VEHICLE_CLASSES:

            vehicles.append({
                "id": int(track_id),
                "type": VEHICLE_CLASSES[class_id],
                "box": (x1, y1, x2, y2),
                "center": (
                    center_x,
                    center_y
                ),
                "confidence": float(confidence)
            })


    # ========================================================
    # DRAW PEOPLE
    # ========================================================

    for person in people:

        x1, y1, x2, y2 = person["box"]

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Person ID:{person['id']}",
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2
        )


    # ========================================================
    # DRAW VEHICLES
    # ========================================================

    for vehicle in vehicles:

        x1, y1, x2, y2 = vehicle["box"]

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            (
                f"{vehicle['type']} "
                f"ID:{vehicle['id']}"
            ),
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2
        )


    # ========================================================
    # PERSON-VEHICLE RISK ANALYSIS
    # ========================================================

    for person in people:

        person_id = person["id"]

        px, py = person["center"]


        for vehicle in vehicles:

            vehicle_id = vehicle["id"]

            vx, vy = vehicle["center"]


            # ------------------------------------------------
            # CENTER DISTANCE
            # ------------------------------------------------

            distance = math.sqrt(
                (px - vx) ** 2
                +
                (py - vy) ** 2
            )


            # =================================================
            # RISK LEVEL
            # =================================================

            if distance <= HIGH_RISK_DISTANCE:

                risk_level = "HIGH"

            elif distance <= MEDIUM_RISK_DISTANCE:

                risk_level = "MEDIUM"

            else:

                risk_level = "LOW"


            # =================================================
            # ONLY REPORT MEDIUM/HIGH RISK
            # =================================================

            if risk_level == "LOW":
                continue


            # ------------------------------------------------
            # UNIQUE EVENT
            # ------------------------------------------------

            risk_key = (
                f"{person_id}_"
                f"{vehicle_id}"
            )


            if risk_key in logged_risks:
                continue


            logged_risks.add(
                risk_key
            )


            risk_events += 1


            if risk_level == "HIGH":

                high_risk_events += 1

            else:

                medium_risk_events += 1


            # =================================================
            # EVIDENCE
            # =================================================

            evidence_name = (
                f"pedestrian_risk_"
                f"P{person_id}_"
                f"V{vehicle_id}_"
                f"{frame_number}.jpg"
            )

            evidence_path = os.path.join(
                EVIDENCE_DIR,
                evidence_name
            )


            cv2.imwrite(
                evidence_path,
                frame
            )


            # =================================================
            # CSV
            # =================================================

            with open(
                CSV_PATH,
                "a",
                newline=""
            ) as file:

                writer = csv.writer(file)

                writer.writerow([
                    (
                        f"PEDESTRIAN_"
                        f"{person_id}_"
                        f"{vehicle_id}_"
                        f"{frame_number}"
                    ),
                    person_id,
                    vehicle_id,
                    vehicle["type"],
                    round(
                        distance,
                        2
                    ),
                    risk_level,
                    round(
                        min(
                            person["confidence"],
                            vehicle["confidence"]
                        ),
                        2
                    ),
                    video_time,
                    evidence_path
                ])


            # =================================================
            # CENTRAL INCIDENT
            # =================================================

            incident_logger.log_incident(

                incident_id=(
                    f"PEDESTRIAN_"
                    f"{person_id}_"
                    f"{vehicle_id}_"
                    f"{frame_number}"
                ),

                incident_type=(
                    "PEDESTRIAN_RISK"
                ),

                object_id=person_id,

                object_type=(
                    f"Person near "
                    f"{vehicle['type']}"
                ),

                severity=risk_level,

                confidence=round(
                    min(
                        person["confidence"],
                        vehicle["confidence"]
                    ),
                    2
                ),

                video_time=video_time,

                latitude="N/A",

                longitude="N/A",

                evidence=evidence_path
            )


            # =================================================
            # VISUAL RISK INDICATOR
            # =================================================

            cv2.line(
                frame,
                person["center"],
                vehicle["center"],
                (255, 255, 255),
                3
            )


            midpoint_x = int(
                (px + vx) / 2
            )

            midpoint_y = int(
                (py + vy) / 2
            )


            cv2.putText(
                frame,
                f"PEDESTRIAN RISK: {risk_level}",
                (
                    midpoint_x,
                    midpoint_y
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )


            print()
            print(
                "🚨 PEDESTRIAN RISK"
            )

            print(
                f"Person     : {person_id}"
            )

            print(
                f"Vehicle    : {vehicle_id}"
            )

            print(
                f"Type       : {vehicle['type']}"
            )

            print(
                f"Distance   : {distance:.1f} px"
            )

            print(
                f"Risk       : {risk_level}"
            )

            print(
                f"Time       : {video_time}"
            )

            print(
                f"Evidence   : {evidence_path}"
            )


    # ========================================================
    # INFORMATION PANEL
    # ========================================================

    cv2.rectangle(
        frame,
        (10, 10),
        (380, 115),
        (0, 0, 0),
        -1
    )


    cv2.putText(
        frame,
        "PEDESTRIAN SAFETY AI",
        (20, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"People: {len(people)}",
        (20, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"Vehicles: {len(vehicles)}",
        (20, 88),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"Risk Events: {risk_events}",
        (20, 108),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.imshow(
        "Pedestrian Risk Detection",
        frame
    )


    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ============================================================
# CLEANUP
# ============================================================

cap.release()

cv2.destroyAllWindows()


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("========================================")
print("PEDESTRIAN RISK ANALYSIS COMPLETE")
print("========================================")

print(
    f"Frames processed : {frame_number}"
)

print(
    f"Risk events      : {risk_events}"
)

print(
    f"High-risk events : {high_risk_events}"
)

print(
    f"Medium-risk events: {medium_risk_events}"
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