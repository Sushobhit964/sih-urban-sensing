import cv2
import os
import csv
from ultralytics import YOLO

from incident_logger import IncidentLogger


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "road_damage_model.pt"
)

VIDEO_PATH = os.path.join(
    BASE_DIR,
    "data",
    "input",
    "a.mp4"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

DAMAGE_DIR = os.path.join(
    OUTPUT_DIR,
    "road_damage"
)

EVIDENCE_DIR = os.path.join(
    DAMAGE_DIR,
    "evidence"
)

CSV_PATH = os.path.join(
    DAMAGE_DIR,
    "road_damage.csv"
)

os.makedirs(EVIDENCE_DIR, exist_ok=True)


# ============================================================
# LOAD MODEL
# ============================================================

print()
print("========================================")
print("ROAD DAMAGE DETECTION")
print("========================================")

model = YOLO(MODEL_PATH)

print("Model classes:")
print(model.names)


# ============================================================
# VIDEO
# ============================================================

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print("ERROR: Could not open video")
    exit()


fps = cap.get(cv2.CAP_PROP_FPS)

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
            "Damage_ID",
            "Damage_Type",
            "Severity",
            "Confidence",
            "Video_Time",
            "Evidence_File"
        ])


# ============================================================
# TRACKING
# ============================================================

logged_ids = set()


# ============================================================
# STATISTICS
# ============================================================

frame_number = 0

total_detections = 0

class_counts = {}


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

    minutes = int(video_seconds // 60)

    seconds = video_seconds % 60

    video_time = f"{minutes:02d}:{seconds:05.2f}"


    # ========================================================
    # YOLO TRACKING
    # ========================================================

    results = model.track(
        frame,
        persist=True,
        verbose=False,
        conf=0.25
    )


    if not results:
        continue


    result = results[0]


    if result.boxes is None:
        continue


    boxes = result.boxes


    # ========================================================
    # GET TRACK IDS
    # ========================================================

    if boxes.id is not None:

        track_ids = (
            boxes.id
            .cpu()
            .numpy()
            .astype(int)
        )

    else:

        # If tracking ID unavailable,
        # create temporary IDs for detections.

        track_ids = list(
            range(len(boxes))
        )


    xyxy = boxes.xyxy.cpu().numpy()

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
    # PROCESS DETECTIONS
    # ========================================================

    for track_id, box, class_id, confidence in zip(
        track_ids,
        xyxy,
        classes,
        confidences
    ):

        total_detections += 1


        # ----------------------------------------------------
        # CLASS NAME
        # ----------------------------------------------------

        damage_type = model.names[int(class_id)]


        class_counts[damage_type] = (
            class_counts.get(
                damage_type,
                0
            ) + 1
        )


        # ----------------------------------------------------
        # BOUNDING BOX
        # ----------------------------------------------------

        x1, y1, x2, y2 = map(
            int,
            box
        )


        # ----------------------------------------------------
        # AREA
        # ----------------------------------------------------

        box_width = max(
            0,
            x2 - x1
        )

        box_height = max(
            0,
            y2 - y1
        )

        box_area = (
            box_width *
            box_height
        )

        frame_area = (
            width *
            height
        )


        area_ratio = (
            box_area /
            frame_area
        )


        # ====================================================
        # SEVERITY
        # ====================================================

        if area_ratio < 0.01:

            severity = "LOW"

        elif area_ratio < 0.04:

            severity = "MEDIUM"

        else:

            severity = "HIGH"


        # ====================================================
        # DRAW DETECTION
        # ====================================================

        label = (
            f"{damage_type} "
            f"{confidence:.2f} "
            f"{severity}"
        )


        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (255, 255, 255),
            2
        )


        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2
        )


        # ====================================================
        # UNIQUE INCIDENT
        # ====================================================

        unique_id = (
            f"{damage_type}_{track_id}"
        )


        if unique_id not in logged_ids:

            logged_ids.add(unique_id)


            # ------------------------------------------------
            # EVIDENCE
            # ------------------------------------------------

            evidence_name = (
                f"{damage_type}_"
                f"{track_id}_"
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


            # ------------------------------------------------
            # DAMAGE CSV
            # ------------------------------------------------

            with open(
                CSV_PATH,
                "a",
                newline=""
            ) as file:

                writer = csv.writer(file)

                writer.writerow([
                    track_id,
                    damage_type,
                    severity,
                    round(
                        float(confidence),
                        2
                    ),
                    video_time,
                    evidence_path
                ])


            # ------------------------------------------------
            # CENTRAL INCIDENT
            # ------------------------------------------------

            incident_logger.log_incident(

                incident_id=(
                    f"ROAD_{damage_type}_"
                    f"{track_id}_"
                    f"{frame_number}"
                ),

                incident_type=(
                    "ROAD_DAMAGE"
                ),

                object_id=track_id,

                object_type=damage_type,

                severity=severity,

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
                f"🚧 ROAD DAMAGE | "
                f"{damage_type} | "
                f"ID {track_id} | "
                f"{severity} | "
                f"{confidence:.2f}"
            )


    # ========================================================
    # DISPLAY PANEL
    # ========================================================

    cv2.rectangle(
        frame,
        (10, 10),
        (360, 90),
        (0, 0, 0),
        -1
    )


    cv2.putText(
        frame,
        "ROAD CONDITION AI",
        (20, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"Detections: {total_detections}",
        (20, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    # ========================================================
    # SHOW
    # ========================================================

    cv2.imshow(
        "Road Damage Detection",
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
# SUMMARY
# ============================================================

print()
print("========================================")
print("ROAD DAMAGE ANALYSIS COMPLETE")
print("========================================")

print(
    f"Frames processed: {frame_number}"
)

print(
    f"Total detections: {total_detections}"
)

print()
print("Detection breakdown:")

for damage_type, count in class_counts.items():

    print(
        f"  {damage_type}: {count}"
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