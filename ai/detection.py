from ultralytics import YOLO
import cv2
import os
import csv

from incident_logger import IncidentLogger

# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(PROJECT_DIR, "yolo11n.pt")
VIDEO_PATH = os.path.join(PROJECT_DIR, "data", "input", "road.mp4")

OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
EVIDENCE_DIR = os.path.join(OUTPUT_DIR, "violations")

VIOLATION_CSV = os.path.join(
    OUTPUT_DIR,
    "violations.csv"
)

os.makedirs(EVIDENCE_DIR, exist_ok=True)

# ============================================================
# INCIDENT LOGGER
# ============================================================

incident_logger = IncidentLogger(OUTPUT_DIR)

# ============================================================
# SETTINGS
# ============================================================

CONFIDENCE = 0.35

# COCO vehicle classes
VEHICLE_CLASSES = {
    1: "Bicycle",
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}

# ============================================================
# START
# ============================================================

print("========================================")
print("       URBAN TRAFFIC DETECTION")
print("========================================")

print("Model:", MODEL_PATH)
print("Video:", VIDEO_PATH)
print("Incident CSV:", incident_logger.csv_path)

# ============================================================
# CHECK FILES
# ============================================================

if not os.path.exists(MODEL_PATH):
    print()
    print("ERROR: yolo11n.pt not found.")
    print(MODEL_PATH)
    exit()

if not os.path.exists(VIDEO_PATH):
    print()
    print("ERROR: road.mp4 not found.")
    print(VIDEO_PATH)
    exit()

print()
print("Model found.")
print("Video found.")

# ============================================================
# LOAD MODEL
# ============================================================

print()
print("Loading YOLO model...")

model = YOLO(MODEL_PATH)

print("YOLO model loaded.")

# ============================================================
# OPEN VIDEO
# ============================================================

video = cv2.VideoCapture(VIDEO_PATH)

if not video.isOpened():
    print("ERROR: Could not open video.")
    exit()

fps = video.get(cv2.CAP_PROP_FPS)

if fps <= 0:
    fps = 30

frame_width = int(
    video.get(cv2.CAP_PROP_FRAME_WIDTH)
)

frame_height = int(
    video.get(cv2.CAP_PROP_FRAME_HEIGHT)
)

print()
print("Video opened.")
print("Resolution:", frame_width, "x", frame_height)
print("FPS:", fps)

# ============================================================
# LINE FOR TRAFFIC FLOW
# ============================================================

LINE_Y = int(frame_height * 0.55)

# ============================================================
# TRACKING VARIABLES
# ============================================================

previous_positions = {}

crossed_ids = set()

wrong_way_ids = set()

observed_vehicle_ids = set()

# ============================================================
# VIOLATION CSV
# ============================================================

csv_file = open(
    VIOLATION_CSV,
    "w",
    newline="",
    encoding="utf-8"
)

csv_writer = csv.writer(csv_file)

csv_writer.writerow([
    "Vehicle_ID",
    "Vehicle_Type",
    "Violation",
    "Video_Time",
    "Evidence_File"
])

csv_file.flush()

# ============================================================
# COUNTERS
# ============================================================

frame_number = 0

total_crossings = 0

total_wrong_way = 0

# ============================================================
# VIDEO LOOP
# ============================================================

while True:

    success, frame = video.read()

    if not success:
        break

    frame_number += 1

    # --------------------------------------------------------
    # VIDEO TIME
    # --------------------------------------------------------

    video_seconds = frame_number / fps

    minutes = int(video_seconds // 60)

    seconds = video_seconds % 60

    video_time = f"{minutes:02d}:{seconds:05.2f}"

    # --------------------------------------------------------
    # YOLO TRACKING
    # --------------------------------------------------------

    results = model.track(
        frame,
        persist=True,
        conf=CONFIDENCE,
        classes=list(VEHICLE_CLASSES.keys()),
        verbose=False
    )

    result = results[0]

    current_vehicles = 0

    # ========================================================
    # DETECTIONS
    # ========================================================

    if (
        result.boxes is not None
        and len(result.boxes) > 0
    ):

        boxes = result.boxes.xyxy.cpu().numpy()

        confidences = result.boxes.conf.cpu().numpy()

        classes = (
            result.boxes.cls
            .int()
            .cpu()
            .tolist()
        )

        if result.boxes.id is not None:

            track_ids = (
                result.boxes.id
                .int()
                .cpu()
                .tolist()
            )

        else:

            track_ids = [
                None
                for _ in boxes
            ]

        # ====================================================
        # EACH VEHICLE
        # ====================================================

        for box, confidence, class_id, track_id in zip(
            boxes,
            confidences,
            classes,
            track_ids
        ):

            x1, y1, x2, y2 = map(int, box)

            vehicle_type = VEHICLE_CLASSES.get(
                class_id,
                "Vehicle"
            )

            current_vehicles += 1

            # ------------------------------------------------
            # CENTER
            # ------------------------------------------------

            center_x = int(
                (x1 + x2) / 2
            )

            center_y = int(
                (y1 + y2) / 2
            )

            # ------------------------------------------------
            # UNIQUE VEHICLES
            # ------------------------------------------------

            if track_id is not None:

                observed_vehicle_ids.add(
                    track_id
                )

            # ------------------------------------------------
            # DRAW VEHICLE
            # ------------------------------------------------

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            label = (
                f"{vehicle_type}"
            )

            if track_id is not None:

                label += (
                    f" ID:{track_id}"
                )

            label += (
                f" {confidence:.2f}"
            )

            cv2.putText(
                frame,
                label,
                (x1, max(25, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

            # =================================================
            # TRACKING LOGIC
            # =================================================

            if track_id is not None:

                previous_y = previous_positions.get(
                    track_id
                )

                # ---------------------------------------------
                # LINE CROSSING
                # ---------------------------------------------

                if previous_y is not None:

                    crossed_line = (
                        previous_y < LINE_Y
                        and center_y >= LINE_Y
                    )

                    if (
                        crossed_line
                        and track_id not in crossed_ids
                    ):

                        crossed_ids.add(
                            track_id
                        )

                        total_crossings += 1

                        print()
                        print(
                            "🚗 VEHICLE CROSSED LINE"
                        )
                        print(
                            "ID:",
                            track_id
                        )
                        print(
                            "Type:",
                            vehicle_type
                        )
                        print(
                            "Time:",
                            video_time
                        )

                # ---------------------------------------------
                # WRONG-WAY DETECTION
                # ---------------------------------------------

                if previous_y is not None:

                    movement = (
                        center_y - previous_y
                    )

                    # Vehicle moving upward
                    # after being detected below line
                    wrong_way = (
                        previous_y > LINE_Y
                        and movement < -2
                    )

                    if (
                        wrong_way
                        and track_id
                        not in wrong_way_ids
                    ):

                        wrong_way_ids.add(
                            track_id
                        )

                        total_wrong_way += 1

                        # -------------------------------------
                        # EVIDENCE
                        # -------------------------------------

                        evidence_filename = (
                            f"wrong_way_ID"
                            f"{track_id}_"
                            f"{video_time.replace(':', '_').replace('.', '_')}"
                            f".jpg"
                        )

                        evidence_path = os.path.join(
                            EVIDENCE_DIR,
                            evidence_filename
                        )

                        saved = cv2.imwrite(
                            evidence_path,
                            frame
                        )

                        print()
                        print(
                            "========================================"
                        )
                        print(
                            "🚨 WRONG-WAY VEHICLE DETECTED"
                        )
                        print(
                            "========================================"
                        )
                        print(
                            "Vehicle ID :",
                            track_id
                        )
                        print(
                            "Vehicle    :",
                            vehicle_type
                        )
                        print(
                            "Time       :",
                            video_time
                        )
                        print(
                            "Evidence   :",
                            evidence_path
                        )
                        print(
                            "Evidence saved:",
                            saved
                        )
                        print(
                            "========================================"
                        )

                        # -------------------------------------
                        # VIOLATION CSV
                        # -------------------------------------

                        if saved:

                            csv_writer.writerow([
                                track_id,
                                vehicle_type,
                                "WRONG_WAY",
                                video_time,
                                evidence_path
                            ])

                            csv_file.flush()

                            # ---------------------------------
                            # CENTRAL INCIDENT LOGGER
                            # ---------------------------------

                            try:

                                incident_logger.log_incident(

                                    incident_id=(
                                        f"WRONG_{track_id}"
                                    ),

                                    incident_type=(
                                        "WRONG_WAY"
                                    ),

                                    object_id=track_id,

                                    object_type=(
                                        vehicle_type
                                    ),

                                    severity="HIGH",

                                    confidence=round(
                                        float(confidence),
                                        3
                                    ),

                                    video_time=video_time,

                                    latitude="N/A",

                                    longitude="N/A",

                                    evidence=evidence_path
                                )

                                print(
                                    "DEBUG: "
                                    "Wrong-way incident logged."
                                )

                            except Exception as e:

                                print(
                                    "ERROR: "
                                    "IncidentLogger failed:",
                                    repr(e)
                                )

                previous_positions[
                    track_id
                ] = center_y

    # ========================================================
    # DRAW TRAFFIC LINE
    # ========================================================

    cv2.line(
        frame,
        (0, LINE_Y),
        (frame_width, LINE_Y),
        (255, 0, 0),
        3
    )

    cv2.putText(
        frame,
        "TRAFFIC LINE",
        (20, LINE_Y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 0, 0),
        2
    )

    # ========================================================
    # INFORMATION PANEL
    # ========================================================

    cv2.rectangle(
        frame,
        (10, 10),
        (430, 150),
        (0, 0, 0),
        -1
    )

    cv2.putText(
        frame,
        f"Vehicles: {current_vehicles}",
        (25, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Unique Vehicles: {len(observed_vehicle_ids)}",
        (25, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Line Crossings: {total_crossings}",
        (25, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Wrong Way: {total_wrong_way}",
        (25, 135),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.imshow(
        "Urban Sensing - Traffic Detection",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break


# ============================================================
# CLEANUP
# ============================================================

video.release()

csv_file.close()

cv2.destroyAllWindows()

# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("========================================")
print("       TRAFFIC ANALYSIS COMPLETE")
print("========================================")

print(
    "Unique vehicles:",
    len(observed_vehicle_ids)
)

print(
    "Line crossings:",
    total_crossings
)

print(
    "Wrong-way violations:",
    total_wrong_way
)

print(
    "Violation CSV:",
    VIOLATION_CSV
)

print(
    "Incident CSV:",
    incident_logger.csv_path
)

print("========================================")