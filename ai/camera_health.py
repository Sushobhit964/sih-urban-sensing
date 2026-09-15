import os
import csv
import cv2
import time
from datetime import datetime

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

VIDEO_FILE = os.path.join(
    BASE_DIR,
    "data",
    "input",
    "road.mp4"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "camera_health.csv"
)

CAMERA_ID = "CAM-001"


# ============================================================
# THRESHOLDS
# ============================================================

MIN_HEALTHY_FPS = 10
MAX_INFERENCE_LATENCY_MS = 150


# ============================================================
# STATUS
# ============================================================

def get_health_status(
    fps,
    latency,
    frames_processed
):

    if frames_processed == 0:
        return "AI OFFLINE"

    if fps < MIN_HEALTHY_FPS:
        return "LOW FPS"

    if latency > MAX_INFERENCE_LATENCY_MS:
        return "HIGH LATENCY"

    return "HEALTHY"


# ============================================================
# CAMERA HEALTH MONITOR
# ============================================================

def monitor_camera():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    print()
    print("========================================")
    print("📹 CAMERA & EDGE-AI HEALTH MONITOR")
    print("========================================")

    if not os.path.exists(VIDEO_FILE):

        print("❌ Camera/video source not found:")
        print(VIDEO_FILE)

        save_health(
            camera_status="OFFLINE",
            fps=0,
            frames_processed=0,
            latency=0,
            health_status="CAMERA OFFLINE"
        )

        return

    cap = cv2.VideoCapture(
        VIDEO_FILE
    )

    if not cap.isOpened():

        print("❌ Unable to open camera source.")

        save_health(
            camera_status="OFFLINE",
            fps=0,
            frames_processed=0,
            latency=0,
            health_status="CAMERA OFFLINE"
        )

        return

    source_fps = cap.get(
        cv2.CAP_PROP_FPS
    )

    if source_fps <= 0:
        source_fps = 30

    total_frames = int(
        cap.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )

    width = int(
        cap.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )

    height = int(
        cap.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )

    frames_processed = 0

    processing_times = []

    start_time = time.perf_counter()

    # --------------------------------------------------------
    # PROCESS VIDEO
    # --------------------------------------------------------

    while True:

        frame_start = time.perf_counter()

        success, frame = cap.read()

        if not success:
            break

        # Simulates the edge-processing loop.
        # In production this is where YOLO inference runs.
        _ = frame.shape

        frames_processed += 1

        frame_end = time.perf_counter()

        processing_ms = (
            frame_end - frame_start
        ) * 1000

        processing_times.append(
            processing_ms
        )

    end_time = time.perf_counter()

    cap.release()

    elapsed = (
        end_time - start_time
    )

    # --------------------------------------------------------
    # CALCULATE HEALTH
    # --------------------------------------------------------

    if elapsed > 0:

        processing_fps = (
            frames_processed / elapsed
        )

    else:

        processing_fps = 0

    if processing_times:

        average_latency = (
            sum(processing_times)
            / len(processing_times)
        )

    else:

        average_latency = 0

    health_status = get_health_status(
        processing_fps,
        average_latency,
        frames_processed
    )

    camera_status = "ONLINE"

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_health(
        camera_status=camera_status,
        fps=processing_fps,
        frames_processed=frames_processed,
        latency=average_latency,
        health_status=health_status,
        source_fps=source_fps,
        total_frames=total_frames,
        width=width,
        height=height
    )

    # --------------------------------------------------------
    # TERMINAL
    # --------------------------------------------------------

    print(
        f"Camera ID        : {CAMERA_ID}"
    )

    print(
        f"Camera Status    : {camera_status}"
    )

    print(
        f"Source FPS       : {source_fps:.1f}"
    )

    print(
        f"Processing FPS   : {processing_fps:.1f}"
    )

    print(
        f"Frames Processed : {frames_processed}"
    )

    print(
        f"Resolution       : {width}x{height}"
    )

    print(
        f"Latency          : {average_latency:.2f} ms"
    )

    print(
        f"AI Health        : {health_status}"
    )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )

    print("========================================")


# ============================================================
# SAVE HEALTH RECORD
# ============================================================

def save_health(
    camera_status,
    fps,
    frames_processed,
    latency,
    health_status,
    source_fps=0,
    total_frames=0,
    width=0,
    height=0
):

    file_exists = os.path.exists(
        OUTPUT_FILE
    )

    with open(
        OUTPUT_FILE,
        "a",
        newline=""
    ) as file:

        writer = csv.writer(file)

        if not file_exists:

            writer.writerow([
                "Camera_ID",
                "Timestamp",
                "Camera_Status",
                "Source_FPS",
                "Processing_FPS",
                "Frames_Processed",
                "Total_Frames",
                "Resolution",
                "Inference_Latency_MS",
                "AI_Health",
            ])

        writer.writerow([
            CAMERA_ID,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            camera_status,
            round(source_fps, 2),
            round(fps, 2),
            frames_processed,
            total_frames,
            f"{width}x{height}",
            round(latency, 2),
            health_status,
        ])


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    monitor_camera()