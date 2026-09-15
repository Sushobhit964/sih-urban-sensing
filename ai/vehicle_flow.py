import os
import csv
from collections import defaultdict
from ultralytics import YOLO
import cv2

# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VIDEO_FILE = os.path.join(
    BASE_DIR,
    "data",
    "input",
    "road.mp4"
)

MODEL_FILE = os.path.join(
    BASE_DIR,
    "yolo11n.pt"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "vehicle_flow.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

# COCO vehicle classes
VEHICLE_CLASSES = {
    1: "Bicycle",
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck",
}

# Virtual horizontal counting line
LINE_POSITION = 0.55

# Minimum movement required before deciding direction
MIN_MOVEMENT = 8


# ============================================================
# HELPERS
# ============================================================

def get_direction(previous_y, current_y):

    movement = current_y - previous_y

    if movement < -MIN_MOVEMENT:
        return "NORTH"

    if movement > MIN_MOVEMENT:
        return "SOUTH"

    return None


def classify_flow(direction):

    if direction == "NORTH":
        return "SOUTH_TO_NORTH"

    if direction == "SOUTH":
        return "NORTH_TO_SOUTH"

    return "UNKNOWN"


# ============================================================
# MAIN
# ============================================================

def analyze_vehicle_flow():

    if not os.path.exists(VIDEO_FILE):

        print("❌ Video not found:")
        print(VIDEO_FILE)
        return

    if not os.path.exists(MODEL_FILE):

        print("❌ YOLO model not found:")
        print(MODEL_FILE)
        return

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    print()
    print("========================================")
    print("🚦 VEHICLE FLOW ANALYSIS")
    print("========================================")

    model = YOLO(MODEL_FILE)

    cap = cv2.VideoCapture(
        VIDEO_FILE
    )

    if not cap.isOpened():

        print("❌ Could not open video.")
        return

    fps = cap.get(
        cv2.CAP_PROP_FPS
    )

    if fps <= 0:
        fps = 30

    frame_width = int(
        cap.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )

    frame_height = int(
        cap.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )

    line_y = int(
        frame_height * LINE_POSITION
    )

    # --------------------------------------------------------
    # TRACKING STATE
    # --------------------------------------------------------

    previous_positions = {}

    counted_vehicles = set()

    flow_counts = defaultdict(int)

    vehicle_type_counts = defaultdict(int)

    direction_vehicle_types = defaultdict(
        lambda: defaultdict(int)
    )

    total_frames = 0

    # --------------------------------------------------------
    # PROCESS VIDEO
    # --------------------------------------------------------

    while True:

        success, frame = cap.read()

        if not success:
            break

        total_frames += 1

        results = model.track(
            frame,
            persist=True,
            classes=list(
                VEHICLE_CLASSES.keys()
            ),
            verbose=False
        )

        if not results:
            continue

        result = results[0]

        if result.boxes is None:
            continue

        if result.boxes.id is None:
            continue

        boxes = result.boxes.xyxy.cpu().numpy()

        classes = (
            result.boxes.cls
            .cpu()
            .numpy()
            .astype(int)
        )

        track_ids = (
            result.boxes.id
            .cpu()
            .numpy()
            .astype(int)
        )

        for box, cls, track_id in zip(
            boxes,
            classes,
            track_ids
        ):

            if cls not in VEHICLE_CLASSES:
                continue

            x1, y1, x2, y2 = box

            center_x = int(
                (x1 + x2) / 2
            )

            center_y = int(
                (y1 + y2) / 2
            )

            vehicle_type = VEHICLE_CLASSES[
                cls
            ]

            # ------------------------------------------------
            # FIRST OBSERVATION
            # ------------------------------------------------

            if track_id not in previous_positions:

                previous_positions[
                    track_id
                ] = (
                    center_x,
                    center_y
                )

                continue

            previous_x, previous_y = (
                previous_positions[
                    track_id
                ]
            )

            # ------------------------------------------------
            # DETERMINE DIRECTION
            # ------------------------------------------------

            direction = get_direction(
                previous_y,
                center_y
            )

            previous_positions[
                track_id
            ] = (
                center_x,
                center_y
            )

            if direction is None:
                continue

            # ------------------------------------------------
            # COUNT EACH VEHICLE ONCE
            # ------------------------------------------------

            if track_id in counted_vehicles:
                continue

            # Count only vehicles crossing the
            # virtual line.

            crossed_line = (
                (
                    previous_y < line_y
                    and center_y >= line_y
                )
                or
                (
                    previous_y > line_y
                    and center_y <= line_y
                )
            )

            if not crossed_line:
                continue

            counted_vehicles.add(
                track_id
            )

            flow_direction = classify_flow(
                direction
            )

            if flow_direction == "UNKNOWN":
                continue

            # ------------------------------------------------
            # GLOBAL COUNTS
            # ------------------------------------------------

            flow_counts[
                flow_direction
            ] += 1

            vehicle_type_counts[
                vehicle_type
            ] += 1

            direction_vehicle_types[
                flow_direction
            ][vehicle_type] += 1

    cap.release()

    # ========================================================
    # CALCULATE FLOW INTENSITY
    # ========================================================

    north_flow = flow_counts[
        "SOUTH_TO_NORTH"
    ]

    south_flow = flow_counts[
        "NORTH_TO_SOUTH"
    ]

    total_flow = (
        north_flow
        + south_flow
    )

    if total_flow > 0:

        imbalance = round(
            abs(
                north_flow
                - south_flow
            )
            / total_flow
            * 100,
            1
        )

    else:

        imbalance = 0

    # --------------------------------------------------------
    # DOMINANT DIRECTION
    # --------------------------------------------------------

    if north_flow > south_flow:

        dominant_direction = (
            "SOUTH_TO_NORTH"
        )

    elif south_flow > north_flow:

        dominant_direction = (
            "NORTH_TO_SOUTH"
        )

    else:

        dominant_direction = "BALANCED"

    # --------------------------------------------------------
    # SAVE FLOW SUMMARY
    # --------------------------------------------------------

    rows = []

    directions = [
        "NORTH_TO_SOUTH",
        "SOUTH_TO_NORTH",
    ]

    for direction in directions:

        count = flow_counts[
            direction
        ]

        cars = direction_vehicle_types[
            direction
        ]["Car"]

        motorcycles = direction_vehicle_types[
            direction
        ]["Motorcycle"]

        buses = direction_vehicle_types[
            direction
        ]["Bus"]

        trucks = direction_vehicle_types[
            direction
        ]["Truck"]

        bicycles = direction_vehicle_types[
            direction
        ]["Bicycle"]

        rows.append({

            "Direction":
                direction,

            "Vehicle_Count":
                count,

            "Cars":
                cars,

            "Motorcycles":
                motorcycles,

            "Buses":
                buses,

            "Trucks":
                trucks,

            "Bicycles":
                bicycles,

            "Flow_Share_Percent":
                round(
                    count / total_flow * 100,
                    1
                )
                if total_flow > 0
                else 0,

            "Dominant_Direction":
                dominant_direction,

            "Directional_Imbalance_Percent":
                imbalance,
        })

    fieldnames = [
        "Direction",
        "Vehicle_Count",
        "Cars",
        "Motorcycles",
        "Buses",
        "Trucks",
        "Bicycles",
        "Flow_Share_Percent",
        "Dominant_Direction",
        "Directional_Imbalance_Percent",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(rows)

    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    print(
        f"Frames analysed : {total_frames}"
    )

    print(
        f"Total vehicles  : {total_flow}"
    )

    print(
        f"North flow      : {north_flow}"
    )

    print(
        f"South flow      : {south_flow}"
    )

    print(
        f"Dominant flow   : {dominant_direction}"
    )

    print(
        f"Imbalance       : {imbalance}%"
    )

    print()

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print("========================================")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    analyze_vehicle_flow()