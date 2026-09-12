import cv2
import os
import csv
import math
from ultralytics import YOLO

from incident_logger import IncidentLogger


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(BASE_DIR, "yolo11n.pt")
VIDEO_PATH = os.path.join(BASE_DIR, "data", "input", "road.mp4")

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
VIOLATION_DIR = os.path.join(OUTPUT_DIR, "violations")

VIOLATION_CSV = os.path.join(OUTPUT_DIR, "violations.csv")
CONGESTION_CSV = os.path.join(OUTPUT_DIR, "congestion.csv")

os.makedirs(VIOLATION_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# LOAD MODEL
# ============================================================

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print("ERROR: Could not open video")
    exit()


fps = cap.get(cv2.CAP_PROP_FPS)

if fps <= 0:
    fps = 30

print()
print("========================================")
print("TRAFFIC ANALYSIS STARTED")
print("========================================")
print(f"FPS: {fps:.2f}")


# ============================================================
# INCIDENT LOGGER
# ============================================================

incident_logger = IncidentLogger(OUTPUT_DIR)


# ============================================================
# VEHICLE CLASSES
# COCO
# 1 = bicycle
# 2 = car
# 3 = motorcycle
# 5 = bus
# 7 = truck
# ============================================================

VEHICLE_CLASSES = {
    1: "Bicycle",
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}


# ============================================================
# VIOLATION CSV
# ============================================================

if not os.path.exists(VIOLATION_CSV):

    with open(VIOLATION_CSV, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "Vehicle_ID",
            "Vehicle_Type",
            "Violation",
            "Video_Time",
            "Evidence_File"
        ])


# ============================================================
# CONGESTION CSV
# ============================================================

if not os.path.exists(CONGESTION_CSV):

    with open(CONGESTION_CSV, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "Video_Time",
            "Vehicle_Count",
            "Cars",
            "Motorcycles",
            "Buses",
            "Trucks",
            "Bicycles",
            "Congestion_Level"
        ])


# ============================================================
# TRACKING VARIABLES
# ============================================================

previous_positions = {}

speed_history = {}

wrong_way_logged = set()

rash_logged = set()

crossed_ids = set()

high_congestion_logged = False


# ============================================================
# LINE CROSSING
# ============================================================

LINE_RATIO = 0.55


# ============================================================
# SPEED PARAMETERS
# ============================================================

# Pixel movement threshold.
#
# This is NOT real km/h.
#
# It measures how rapidly an object moves through the
# camera image.
#
# We will use this for prototype rash-driving detection.

RASH_SPEED_THRESHOLD = 18.0

MIN_SPEED_SAMPLES = 3

# Prevent tiny detection jitter from being considered speed.
MIN_MOVEMENT = 2.0


# ============================================================
# STATISTICS
# ============================================================

frame_number = 0

max_vehicle_count = 0

low_frames = 0
medium_frames = 0
high_frames = 0

rash_events = 0


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = cap.read()

    if not success:
        break

    frame_number += 1

    height, width = frame.shape[:2]

    line_y = int(height * LINE_RATIO)

    video_seconds = frame_number / fps

    minutes = int(video_seconds // 60)

    seconds = video_seconds % 60

    video_time = f"{minutes:02d}:{seconds:05.2f}"


    # ========================================================
    # YOLO TRACKING
    # ========================================================

    results = model.track(
        frame,
        persist=True,
        classes=list(VEHICLE_CLASSES.keys()),
        verbose=False
    )


    vehicle_count = 0

    cars = 0
    motorcycles = 0
    buses = 0
    trucks = 0
    bicycles = 0


    current_positions = {}


    # ========================================================
    # PROCESS DETECTIONS
    # ========================================================

    if results and results[0].boxes is not None:

        boxes = results[0].boxes


        if boxes.id is not None:

            ids = boxes.id.cpu().numpy().astype(int)

            xyxy = boxes.xyxy.cpu().numpy()

            classes = boxes.cls.cpu().numpy().astype(int)

            confidences = boxes.conf.cpu().numpy()


            for track_id, box, class_id, confidence in zip(
                ids,
                xyxy,
                classes,
                confidences
            ):

                if class_id not in VEHICLE_CLASSES:
                    continue


                vehicle_type = VEHICLE_CLASSES[class_id]

                x1, y1, x2, y2 = map(int, box)


                # ------------------------------------------------
                # CENTER POINT
                # ------------------------------------------------

                center_x = int((x1 + x2) / 2)

                center_y = int((y1 + y2) / 2)


                current_positions[track_id] = (
                    center_x,
                    center_y
                )


                vehicle_count += 1


                # ------------------------------------------------
                # VEHICLE COUNTERS
                # ------------------------------------------------

                if class_id == 2:
                    cars += 1

                elif class_id == 3:
                    motorcycles += 1

                elif class_id == 5:
                    buses += 1

                elif class_id == 7:
                    trucks += 1

                elif class_id == 1:
                    bicycles += 1


                # =================================================
                # SPEED ESTIMATION
                # =================================================

                if track_id in previous_positions:

                    previous_x, previous_y = previous_positions[
                        track_id
                    ]


                    movement = math.sqrt(
                        (center_x - previous_x) ** 2
                        +
                        (center_y - previous_y) ** 2
                    )


                    # Ignore tiny tracking jitter
                    if movement < MIN_MOVEMENT:
                        movement = 0


                    # ------------------------------------------------
                    # Convert to approximate pixels/second
                    # ------------------------------------------------

                    speed_pixels = movement * fps


                    speed_history.setdefault(
                        track_id,
                        []
                    )

                    speed_history[track_id].append(
                        speed_pixels
                    )


                    # Keep recent history only
                    if len(speed_history[track_id]) > 10:

                        speed_history[track_id].pop(0)


                    # ------------------------------------------------
                    # Average recent speed
                    # ------------------------------------------------

                    average_speed = sum(
                        speed_history[track_id]
                    ) / len(
                        speed_history[track_id]
                    )


                    # =================================================
                    # RASH DRIVING DETECTION
                    # =================================================

                    if (
                        len(speed_history[track_id])
                        >= MIN_SPEED_SAMPLES
                        and average_speed
                        >= RASH_SPEED_THRESHOLD
                    ):

                        if track_id not in rash_logged:

                            rash_logged.add(track_id)

                            rash_events += 1


                            # -----------------------------------------
                            # Evidence image
                            # -----------------------------------------

                            evidence_name = (
                                f"rash_vehicle_{track_id}_"
                                f"{frame_number}.jpg"
                            )

                            evidence_path = os.path.join(
                                VIOLATION_DIR,
                                evidence_name
                            )


                            cv2.imwrite(
                                evidence_path,
                                frame
                            )


                            # -----------------------------------------
                            # CSV
                            # -----------------------------------------

                            with open(
                                VIOLATION_CSV,
                                "a",
                                newline=""
                            ) as file:

                                writer = csv.writer(file)

                                writer.writerow([
                                    track_id,
                                    vehicle_type,
                                    "RASH_DRIVING",
                                    video_time,
                                    evidence_path
                                ])


                            # -----------------------------------------
                            # CENTRAL INCIDENT LOGGER
                            # -----------------------------------------

                            incident_logger.log_incident(

                                incident_id=(
                                    f"RASH_{track_id}_"
                                    f"{frame_number}"
                                ),

                                incident_type="RASH_DRIVING",

                                object_id=track_id,

                                object_type=vehicle_type,

                                severity="HIGH",

                                confidence=round(
                                    float(confidence),
                                    2
                                ),

                                video_time=video_time,

                                latitude="N/A",

                                longitude="N/A",

                                evidence=evidence_path
                            )


                            print(
                                f"🚨 RASH DRIVING | "
                                f"Vehicle {track_id} | "
                                f"{vehicle_type} | "
                                f"Speed score: "
                                f"{average_speed:.1f}"
                            )


                    # ------------------------------------------------
                    # DISPLAY SPEED
                    # ------------------------------------------------

                    speed_text = (
                        f"{average_speed:.0f} px/s"
                    )

                else:

                    speed_text = "0 px/s"


                # =================================================
                # DRAW VEHICLE
                # =================================================

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (255, 255, 255),
                    2
                )


                label = (
                    f"{vehicle_type} "
                    f"ID:{track_id} "
                    f"{speed_text}"
                )


                cv2.putText(
                    frame,
                    label,
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2
                )


                # =================================================
                # LINE CROSSING
                # =================================================

                if track_id in previous_positions:

                    previous_y = previous_positions[
                        track_id
                    ][1]


                    if (
                        previous_y < line_y
                        and center_y >= line_y
                    ):

                        if track_id not in crossed_ids:

                            crossed_ids.add(track_id)

                            print(
                                f"Vehicle {track_id} "
                                f"crossed line"
                            )


    # ============================================================
    # UPDATE POSITIONS
    # ============================================================

    previous_positions = current_positions.copy()


    # ============================================================
    # CONGESTION
    # ============================================================

    max_vehicle_count = max(
        max_vehicle_count,
        vehicle_count
    )


    if vehicle_count <= 5:

        congestion_level = "LOW"

        low_frames += 1

    elif vehicle_count <= 12:

        congestion_level = "MEDIUM"

        medium_frames += 1

    else:

        congestion_level = "HIGH"

        high_frames += 1


    # ============================================================
    # CONGESTION CSV
    # ============================================================

    with open(
        CONGESTION_CSV,
        "a",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            video_time,
            vehicle_count,
            cars,
            motorcycles,
            buses,
            trucks,
            bicycles,
            congestion_level
        ])


    # ============================================================
    # LOG HIGH CONGESTION ONCE
    # ============================================================

    if (
        congestion_level == "HIGH"
        and not high_congestion_logged
    ):

        high_congestion_logged = True


        incident_logger.log_incident(

            incident_id=f"CONGESTION_{frame_number}",

            incident_type="CONGESTION",

            object_id="TRAFFIC_ZONE",

            object_type="Traffic",

            severity="HIGH",

            confidence=1.0,

            video_time=video_time,

            latitude="N/A",

            longitude="N/A",

            evidence="N/A"
        )


    # ============================================================
    # DRAW COUNTING LINE
    # ============================================================

    cv2.line(
        frame,
        (0, line_y),
        (width, line_y),
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        "COUNTING LINE",
        (10, line_y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )


    # ============================================================
    # TRAFFIC INFORMATION PANEL
    # ============================================================

    cv2.rectangle(
        frame,
        (10, 10),
        (330, 170),
        (0, 0, 0),
        -1
    )


    cv2.putText(
        frame,
        f"Vehicles: {vehicle_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"Cars: {cars}",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"Bus: {buses}  Truck: {trucks}",
        (20, 95),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"Motorcycle: {motorcycles}",
        (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"Congestion: {congestion_level}",
        (20, 145),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"Rash events: {rash_events}",
        (20, 165),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    # ============================================================
    # SHOW
    # ============================================================

    cv2.imshow(
        "AI Traffic Analysis",
        frame
    )


    # Press Q to stop
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
print("TRAFFIC ANALYSIS COMPLETE")
print("========================================")

print(f"Frames processed      : {frame_number}")

print(f"Maximum vehicles      : {max_vehicle_count}")

print(f"LOW congestion frames : {low_frames}")

print(f"MEDIUM frames         : {medium_frames}")

print(f"HIGH congestion frames: {high_frames}")

print(f"Rash driving events   : {rash_events}")

print()
print("Files created:")
print(f"- {CONGESTION_CSV}")
print(f"- {VIOLATION_CSV}")
print(f"- {os.path.join(OUTPUT_DIR, 'incidents.csv')}")
print(f"- {VIOLATION_DIR}")

print("========================================")