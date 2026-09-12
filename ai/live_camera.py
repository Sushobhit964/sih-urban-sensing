import os
import cv2
import time
from ultralytics import YOLO

# ============================================================
# LIVE CAMERA INPUT TEST
#
# This module proves that your architecture can accept:
#   1. MP4 video
#   2. Laptop webcam
#   3. RTSP/IP camera
#
# It does NOT replace your existing AI modules.
# It provides a common live-video source that can later be
# connected to the detection pipelines.
# ============================================================

# Choose ONE:
SOURCE_TYPE = "rtsp"       # "video", "webcam", or "rtsp"

VIDEO_SOURCE = "data/input/road.mp4"
WEBCAM_SOURCE = 0

# Example:
# RTSP_SOURCE = "rtsp://username:password@192.168.1.100:554/stream"
RTSP_SOURCE = "rtsp://username:password@192.168.1.100:554/stream"

VEHICLE_MODEL = "yolo11n.pt"

# COCO vehicle classes
VEHICLE_CLASSES = {
    1: "Motorcycle",
    2: "Car",
    5: "Bus",
    7: "Truck",
}

CONFIDENCE = 0.35


def get_source():
    if SOURCE_TYPE == "video":
        return VIDEO_SOURCE

    if SOURCE_TYPE == "webcam":
        return WEBCAM_SOURCE

    if SOURCE_TYPE == "rtsp":
        if not RTSP_SOURCE:
            raise ValueError(
                "SOURCE_TYPE is 'rtsp' but RTSP_SOURCE is empty."
            )
        return RTSP_SOURCE

    raise ValueError(
        "SOURCE_TYPE must be 'video', 'webcam', or 'rtsp'."
    )


def main():
    source = get_source()

    print("\n========================================")
    print("📡 LIVE CAMERA / VIDEO SOURCE")
    print("========================================")
    print(f"Source type : {SOURCE_TYPE}")
    print(f"Source      : {source}")
    print("========================================\n")

    model = YOLO(VEHICLE_MODEL)

    # For RTSP, OpenCV handles the network stream.
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print("\n❌ Could not open source.")
        print("Check:")
        print("  • video path")
        print("  • webcam permissions")
        print("  • RTSP URL/network")
        return

    frame_count = 0
    start_time = time.time()

    print("🟢 SOURCE CONNECTED")
    print("Press Q to stop.\n")

    while True:
        ok, frame = cap.read()

        if not ok:
            if SOURCE_TYPE == "video":
                print("Video finished.")
            else:
                print("⚠️ Frame could not be read from live source.")
            break

        frame_count += 1

        # Existing YOLO vehicle detector.
        results = model(
            frame,
            conf=CONFIDENCE,
            classes=list(VEHICLE_CLASSES.keys()),
            verbose=False,
        )

        annotated = results[0].plot()

        elapsed = max(time.time() - start_time, 0.001)
        fps = frame_count / elapsed

        cv2.putText(
            annotated,
            f"SOURCE: {SOURCE_TYPE.upper()}  |  FPS: {fps:.1f}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        cv2.imshow("SIH Urban Sensing - Live Camera", annotated)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

    print("\n========================================")
    print("✅ CAMERA SESSION ENDED")
    print("========================================")
    print(f"Frames processed: {frame_count}")
    print(f"Source type     : {SOURCE_TYPE}")
    print("========================================")


if __name__ == "__main__":
    main()
