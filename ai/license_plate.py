import os
import csv
import re
import time
import urllib.request
from collections import defaultdict

import cv2
import numpy as np
from ultralytics import YOLO

# ============================================================
# GENERIC VEHICLE + LICENSE-PLATE / ANPR PIPELINE
# Input:  data/input/road.mp4
# Output: output/vehicle_registry/vehicle_registry.csv
#         output/vehicle_registry/evidence/
#
# Plate detector:
# morsetechlab/yolov11-license-plate-detection
# Uses its lightweight v1n model.
#
# OCR:
# EasyOCR. If EasyOCR is unavailable, the script tells you how
# to install it. OCR is never invented: unreadable plates are
# recorded as UNKNOWN.
# ============================================================

VIDEO_SOURCE = "data/input/road.mp4"
VEHICLE_MODEL = "yolo11n.pt"
PLATE_MODEL = "license_plate_model.pt"

OUTPUT_DIR = "output/vehicle_registry"
EVIDENCE_DIR = os.path.join(OUTPUT_DIR, "evidence")
CSV_PATH = os.path.join(OUTPUT_DIR, "vehicle_registry.csv")

PLATE_MODEL_URL = (
    "https://huggingface.co/morsetechlab/yolov11-license-plate-detection/"
    "resolve/main/license-plate-finetune-v1n.pt"
)

VEHICLE_CLASSES = {
    1: "Motorcycle",
    2: "Car",
    5: "Bus",
    7: "Truck",
}

VEHICLE_CONF = 0.35
PLATE_CONF = 0.25

# OCR is expensive, so don't OCR every frame.
OCR_EVERY_N_FRAMES = 5

MIN_PLATE_WIDTH = 35
MIN_PLATE_HEIGHT = 10

# Only accept useful-looking plate strings.
MIN_TEXT_LEN = 4
MAX_TEXT_LEN = 12


def ensure_dirs():
    os.makedirs(EVIDENCE_DIR, exist_ok=True)


def ensure_plate_model():
    if os.path.exists(PLATE_MODEL):
        return

    print("\n[INFO] Downloading license-plate detector...")
    print("[INFO] One-time download (~10 MB).\n")

    try:
        urllib.request.urlretrieve(PLATE_MODEL_URL, PLATE_MODEL)
    except Exception as exc:
        raise RuntimeError(
            "\nCould not download the plate model automatically.\n"
            "Download license-plate-finetune-v1n.pt from the model repository "
            "and save it as license_plate_model.pt.\n\n"
            f"Original error: {exc}"
        )


def clean_plate_text(text):
    """
    OCR cleanup for Indian-style registration plates.

    We keep only A-Z and 0-9 and remove spaces/hyphens.
    We do NOT invent missing characters.
    """
    text = str(text).upper()
    text = re.sub(r"[^A-Z0-9]", "", text)

    if not (MIN_TEXT_LEN <= len(text) <= MAX_TEXT_LEN):
        return ""

    # A useful plate normally contains both letters and digits.
    if not re.search(r"[A-Z]", text):
        return ""
    if not re.search(r"[0-9]", text):
        return ""

    return text


def preprocess_plate(crop):
    """Create a few OCR-friendly versions of the plate crop."""
    if crop is None or crop.size == 0:
        return []

    h, w = crop.shape[:2]
    scale = max(2.0, 180.0 / max(h, 1))
    resized = cv2.resize(
        crop,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC,
    )

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # Mild denoise + contrast.
    gray = cv2.bilateralFilter(gray, 7, 50, 50)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    sharp = cv2.detailEnhance(resized, sigma_s=10, sigma_r=0.15)

    return [resized, gray, sharp]


def choose_best_ocr(reader, crop):
    """
    Run OCR on several preprocessing variants and return the
    most plausible result. Returns ("UNKNOWN", 0.0) if unreadable.
    """
    best_text = ""
    best_conf = 0.0

    for image in preprocess_plate(crop):
        try:
            results = reader.readtext(
                image,
                detail=1,
                paragraph=False,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            )
        except Exception:
            continue

        for item in results:
            if len(item) < 3:
                continue

            raw_text = item[1]
            confidence = float(item[2])

            text = clean_plate_text(raw_text)

            if not text:
                continue

            # Confidence is OCR confidence, not legal certainty.
            score = confidence

            if score > best_conf:
                best_text = text
                best_conf = score

    if not best_text:
        return "UNKNOWN", 0.0

    return best_text, best_conf


def point_inside(box, point):
    x1, y1, x2, y2 = box
    x, y = point
    return x1 <= x <= x2 and y1 <= y <= y2


def associate_plate_to_vehicle(plate_box, vehicle_boxes):
    """
    Associate a detected plate with the vehicle whose bounding box
    contains the plate center. If none contains it, use nearest
    vehicle center as a fallback.
    """
    px1, py1, px2, py2 = plate_box
    pcx = (px1 + px2) / 2
    pcy = (py1 + py2) / 2

    containing = []

    for vehicle_id, data in vehicle_boxes.items():
        box = data["box"]

        if point_inside(box, (pcx, pcy)):
            area = max(1.0, (box[2] - box[0]) * (box[3] - box[1]))
            containing.append((area, vehicle_id))

    if containing:
        containing.sort()
        return containing[0][1]

    # Fallback: nearest vehicle center.
    best_id = None
    best_distance = float("inf")

    for vehicle_id, data in vehicle_boxes.items():
        x1, y1, x2, y2 = data["box"]
        vcx = (x1 + x2) / 2
        vcy = (y1 + y2) / 2

        distance = ((pcx - vcx) ** 2 + (pcy - vcy) ** 2) ** 0.5

        if distance < best_distance:
            best_distance = distance
            best_id = vehicle_id

    return best_id


def save_evidence(frame, vehicle_id, plate_box, plate_text):
    x1, y1, x2, y2 = plate_box

    annotated = frame.copy()
    cv2.rectangle(
        annotated,
        (x1, y1),
        (x2, y2),
        (0, 255, 0),
        2,
    )

    label = f"Vehicle {vehicle_id} | Plate: {plate_text}"

    cv2.rectangle(
        annotated,
        (x1, max(0, y1 - 32)),
        (x1 + max(250, len(label) * 11), y1),
        (0, 255, 0),
        -1,
    )

    cv2.putText(
        annotated,
        label,
        (x1 + 5, max(20, y1 - 9)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )

    filename = (
        f"vehicle_{vehicle_id}_"
        f"{plate_text}_"
        f"{int(time.time() * 1000)}.jpg"
    )

    path = os.path.join(EVIDENCE_DIR, filename)
    cv2.imwrite(path, annotated)

    return path


def main():
    ensure_dirs()
    ensure_plate_model()

    try:
        import easyocr
    except ImportError:
        print("\nEasyOCR is not installed.")
        print("Run:")
        print("    pip install easyocr")
        print("\nThen run this script again.")
        return

    print("\n========================================")
    print("🚗 VEHICLE + LICENSE PLATE DETECTION")
    print("========================================")
    print(f"Video        : {VIDEO_SOURCE}")
    print(f"Vehicle model: {VEHICLE_MODEL}")
    print(f"Plate model  : {PLATE_MODEL}")
    print("========================================\n")

    vehicle_model = YOLO(VEHICLE_MODEL)
    plate_model = YOLO(PLATE_MODEL)

    print("[INFO] Loading OCR...")
    reader = easyocr.Reader(["en"], gpu=False)

    cap = cv2.VideoCapture(VIDEO_SOURCE)

    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {VIDEO_SOURCE}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0

    frame_number = 0

    # vehicle_id -> observed plate texts and confidences
    plate_observations = defaultdict(lambda: defaultdict(list))

    # Prevent saving hundreds of duplicate evidence images.
    last_saved_text = {}

    # Create/overwrite CSV for this run.
    with open(CSV_PATH, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "Vehicle_ID",
                "Vehicle_Type",
                "License_Plate",
                "OCR_Confidence",
                "Video_Time",
                "Evidence",
            ]
        )

    while True:
        ok, frame = cap.read()

        if not ok:
            break

        frame_number += 1
        video_time = frame_number / fps

        # --------------------------------------------------------
        # 1. TRACK VEHICLES
        # --------------------------------------------------------
        vehicle_results = vehicle_model.track(
            frame,
            persist=True,
            conf=VEHICLE_CONF,
            classes=list(VEHICLE_CLASSES.keys()),
            verbose=False,
        )

        vehicle_boxes = {}

        if vehicle_results and vehicle_results[0].boxes is not None:
            boxes = vehicle_results[0].boxes

            ids = (
                boxes.id.int().cpu().tolist()
                if boxes.id is not None
                else []
            )

            for i, box in enumerate(boxes):
                if i >= len(ids):
                    continue

                vehicle_id = int(ids[i])
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0].cpu().tolist(),
                )

                vehicle_boxes[vehicle_id] = {
                    "box": (x1, y1, x2, y2),
                    "type": VEHICLE_CLASSES.get(cls_id, "Vehicle"),
                    "confidence": conf,
                }

        if not vehicle_boxes:
            continue

        # --------------------------------------------------------
        # 2. DETECT PLATES
        # --------------------------------------------------------
        if frame_number % OCR_EVERY_N_FRAMES != 0:
            continue

        plate_results = plate_model(
            frame,
            conf=PLATE_CONF,
            verbose=False,
        )

        if not plate_results or plate_results[0].boxes is None:
            continue

        for plate in plate_results[0].boxes:
            px1, py1, px2, py2 = map(
                int,
                plate.xyxy[0].cpu().tolist(),
            )

            plate_conf = float(plate.conf[0].item())

            width = px2 - px1
            height = py2 - py1

            if width < MIN_PLATE_WIDTH or height < MIN_PLATE_HEIGHT:
                continue

            vehicle_id = associate_plate_to_vehicle(
                (px1, py1, px2, py2),
                vehicle_boxes,
            )

            if vehicle_id is None:
                continue

            # Add a small crop margin.
            margin_x = max(3, int(width * 0.08))
            margin_y = max(3, int(height * 0.20))

            cx1 = max(0, px1 - margin_x)
            cy1 = max(0, py1 - margin_y)
            cx2 = min(frame.shape[1], px2 + margin_x)
            cy2 = min(frame.shape[0], py2 + margin_y)

            crop = frame[cy1:cy2, cx1:cx2]

            plate_text, ocr_conf = choose_best_ocr(
                reader,
                crop,
            )

            if plate_text == "UNKNOWN":
                continue

            plate_observations[vehicle_id][plate_text].append(
                ocr_conf
            )

            # Use the most frequently observed text for the vehicle.
            candidates = plate_observations[vehicle_id]

            best_text = max(
                candidates,
                key=lambda text: (
                    len(candidates[text]),
                    np.mean(candidates[text]),
                ),
            )

            best_conf = float(np.mean(candidates[best_text]))

            previous = last_saved_text.get(vehicle_id)

            if previous != best_text:
                evidence = save_evidence(
                    frame,
                    vehicle_id,
                    (px1, py1, px2, py2),
                    best_text,
                )

                last_saved_text[vehicle_id] = best_text

                with open(CSV_PATH, "a", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(
                        [
                            vehicle_id,
                            vehicle_boxes[vehicle_id]["type"],
                            best_text,
                            round(best_conf, 3),
                            f"{video_time:.2f}",
                            evidence,
                        ]
                    )

                print(
                    f"[PLATE] Vehicle {vehicle_id} | "
                    f"{vehicle_boxes[vehicle_id]['type']} | "
                    f"{best_text} | "
                    f"OCR={best_conf:.2f}"
                )

    cap.release()

    print("\n========================================")
    print("✅ ANPR PROCESSING COMPLETE")
    print("========================================")
    print(f"CSV      : {CSV_PATH}")
    print(f"Evidence : {EVIDENCE_DIR}")
    print("========================================\n")


if __name__ == "__main__":
    main()
