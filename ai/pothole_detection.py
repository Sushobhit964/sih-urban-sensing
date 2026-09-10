from ultralytics import YOLO
import cv2
import os
import csv

from incident_logger import IncidentLogger

# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(PROJECT_DIR, "pothole_model.pt")
VIDEO_PATH = os.path.join(PROJECT_DIR, "data", "input", "a.mp4")

OUTPUT_DIR = os.path.join(PROJECT_DIR, "output", "potholes")
EVIDENCE_DIR = os.path.join(OUTPUT_DIR, "evidence")
CSV_PATH = os.path.join(OUTPUT_DIR, "potholes.csv")

# Central incident log
INCIDENT_OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")

incident_logger = IncidentLogger(INCIDENT_OUTPUT_DIR)

CONFIDENCE = 0.40

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)

# ============================================================
# START
# ============================================================

print("========================================")
print("       POTHOLE DETECTION SYSTEM")
print("========================================")
print("Model:", MODEL_PATH)
print("Video:", VIDEO_PATH)
print("Output:", OUTPUT_DIR)
print("Incident CSV:", incident_logger.csv_path)

# ============================================================
# CHECK FILES
# ============================================================

if not os.path.exists(MODEL_PATH):
    print()
    print("ERROR: pothole_model.pt was not found.")
    print("Expected location:")
    print(MODEL_PATH)
    exit()

if not os.path.exists(VIDEO_PATH):
    print()
    print("ERROR: a.mp4 was not found.")
    print("Expected location:")
    print(VIDEO_PATH)
    exit()

print()
print("Model file found.")
print("Video file found.")

# ============================================================
# LOAD MODEL
# ============================================================

print()
print("Loading pothole model...")

model = YOLO(MODEL_PATH)

print("Pothole model loaded successfully.")

# ============================================================
# OPEN VIDEO
# ============================================================

print()
print("Opening video...")

video = cv2.VideoCapture(VIDEO_PATH)

if not video.isOpened():
    print("ERROR: Could not open video.")
    exit()

print("Video opened successfully.")

fps = video.get(cv2.CAP_PROP_FPS)

if fps <= 0:
    fps = 30

frame_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

print("FPS:", fps)
print("Resolution:", frame_width, "x", frame_height)

# ============================================================
# VARIABLES
# ============================================================

frame_number = 0
total_potholes = 0

reported_potholes = set()

# ============================================================
# CSV SETUP
# ============================================================

csv_file = open(
    CSV_PATH,
    "w",
    newline="",
    encoding="utf-8"
)

csv_writer = csv.writer(csv_file)

csv_writer.writerow([
    "Pothole_ID",
    "Severity",
    "Confidence",
    "Video_Time",
    "Latitude",
    "Longitude",
    "Evidence_File"
])

csv_file.flush()

# ============================================================
# SEVERITY FUNCTION
# ============================================================

def calculate_severity(
    box_width,
    box_height,
    frame_width,
    frame_height
):

    box_area = box_width * box_height
    frame_area = frame_width * frame_height

    if frame_area == 0:
        return "UNKNOWN"

    area_ratio = box_area / frame_area

    if area_ratio < 0.01:
        return "LOW"

    elif area_ratio < 0.04:
        return "MEDIUM"

    else:
        return "HIGH"


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
        verbose=False
    )

    result = results[0]

    current_potholes = 0

    # --------------------------------------------------------
    # DETECTIONS
    # --------------------------------------------------------

    if result.boxes is not None and len(result.boxes) > 0:

        boxes = result.boxes.xyxy.cpu().numpy()

        confidences = result.boxes.conf.cpu().numpy()

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

        # ----------------------------------------------------
        # EACH POTHOLE
        # ----------------------------------------------------

        for box, confidence, track_id in zip(
            boxes,
            confidences,
            track_ids
        ):

            x1, y1, x2, y2 = map(int, box)

            current_potholes += 1

            box_width = x2 - x1

            box_height = y2 - y1

            severity = calculate_severity(
                box_width,
                box_height,
                frame_width,
                frame_height
            )

            # ------------------------------------------------
            # DRAW BOX
            # ------------------------------------------------

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 0, 255),
                3
            )

            # ------------------------------------------------
            # LABEL
            # ------------------------------------------------

            if track_id is not None:

                label = (
                    f"POTHOLE | ID {track_id} | "
                    f"{severity} | {confidence:.2f}"
                )

            else:

                label = (
                    f"POTHOLE | "
                    f"{severity} | {confidence:.2f}"
                )

            cv2.putText(
                frame,
                label,
                (x1, max(25, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 255),
                2
            )

            # =================================================
            # UNIQUE POTHOLE
            # =================================================

            if (
                track_id is not None
                and track_id not in reported_potholes
            ):

                reported_potholes.add(track_id)

                total_potholes += 1

                # ------------------------------------------------
                # EVIDENCE FILENAME
                # ------------------------------------------------

                safe_time = (
                    video_time
                    .replace(":", "_")
                    .replace(".", "_")
                )

                evidence_filename = (
                    f"pothole_ID{track_id}_"
                    f"{safe_time}.jpg"
                )

                evidence_path = os.path.join(
                    EVIDENCE_DIR,
                    evidence_filename
                )

                # ------------------------------------------------
                # SAVE EVIDENCE
                # ------------------------------------------------

                saved = cv2.imwrite(
                    evidence_path,
                    frame
                )

                print()
                print("----------------------------------------")
                print("DEBUG: POTHOLE EVENT")
                print("----------------------------------------")
                print("ID:", track_id)
                print("Severity:", severity)
                print("Confidence:", round(float(confidence), 3))
                print("Time:", video_time)
                print("Evidence:", evidence_path)
                print("Evidence saved:", saved)
                print("----------------------------------------")

                latitude = "N/A"
                longitude = "N/A"

                # =================================================
                # SAVE REPORT + INCIDENT
                # =================================================

                if saved:

                    # ---------------------------------------------
                    # POTHOLE CSV
                    # ---------------------------------------------

                    csv_writer.writerow([
                        track_id,
                        severity,
                        f"{confidence:.3f}",
                        video_time,
                        latitude,
                        longitude,
                        evidence_path
                    ])

                    csv_file.flush()

                    print(
                        "DEBUG: Pothole CSV updated."
                    )

                    # ---------------------------------------------
                    # CENTRAL INCIDENT LOGGER
                    # ---------------------------------------------

                    print(
                        "DEBUG: Calling IncidentLogger..."
                    )

                    try:

                        incident_logger.log_incident(

                            incident_id=f"POT_{track_id}",

                            incident_type="POTHOLE",

                            object_id=track_id,

                            object_type="Road",

                            severity=severity,

                            confidence=round(
                                float(confidence),
                                3
                            ),

                            video_time=video_time,

                            latitude=latitude,

                            longitude=longitude,

                            evidence=evidence_path
                        )

                        print(
                            "DEBUG: Incident successfully logged."
                        )

                    except Exception as e:

                        print()
                        print(
                            "ERROR: IncidentLogger failed!"
                        )

                        print(
                            "Reason:",
                            repr(e)
                        )

                else:

                    print()
                    print(
                        "WARNING: Evidence image "
                        "could not be saved."
                    )

                # =================================================
                # POTHOLE MESSAGE
                # =================================================

                print()
                print("========================================")
                print("🚧 POTHOLE DETECTED")
                print("========================================")
                print(f"Pothole ID : {track_id}")
                print(f"Severity   : {severity}")
                print(
                    f"Confidence : {float(confidence):.2f}"
                )
                print(f"Time       : {video_time}")
                print(
                    f"Evidence   : {evidence_path}"
                )
                print("========================================")

    # =========================================================
    # INFORMATION PANEL
    # =========================================================

    cv2.rectangle(
        frame,
        (10, 10),
        (390, 150),
        (0, 0, 0),
        -1
    )

    cv2.putText(
        frame,
        f"Current Potholes: {current_potholes}",
        (25, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Total Potholes: {total_potholes}",
        (25, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Video Time: {video_time}",
        (25, 115),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    # =========================================================
    # DISPLAY
    # =========================================================

    cv2.imshow(
        "Urban Sensing - Pothole Detection",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break


# =============================================================
# CLEANUP
# =============================================================

video.release()

csv_file.close()

cv2.destroyAllWindows()

# =============================================================
# FINAL
# =============================================================

print()

print("========================================")
print("       POTHOLE ANALYSIS COMPLETE")
print("========================================")

print(
    f"Unique potholes: {total_potholes}"
)

print(
    f"CSV report: {CSV_PATH}"
)

print(
    f"Evidence folder: {EVIDENCE_DIR}"
)

print(
    f"Incident CSV: {incident_logger.csv_path}"
)

print("========================================")