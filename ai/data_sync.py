import os
import csv
import json
import time
import shutil
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

OUTPUT_DIR = os.path.join(BASE_DIR, "output")

INCIDENT_FILE = os.path.join(
    OUTPUT_DIR,
    "incidents.csv"
)

SYNC_DIR = os.path.join(
    OUTPUT_DIR,
    "sync_queue"
)

SYNCED_DIR = os.path.join(
    OUTPUT_DIR,
    "synced_events"
)

SYNC_LOG = os.path.join(
    OUTPUT_DIR,
    "sync_log.csv"
)

os.makedirs(SYNC_DIR, exist_ok=True)
os.makedirs(SYNCED_DIR, exist_ok=True)


# ============================================================
# PRIORITY
# ============================================================

PRIORITY = {
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 3,
    "LOW": 4
}


def get_priority(severity):

    severity = str(
        severity
    ).upper().strip()

    return PRIORITY.get(
        severity,
        5
    )


# ============================================================
# EVENT ID
# ============================================================

def create_event_id(row, index):

    incident_id = row.get(
        "Incident_ID",
        f"INC-{index}"
    )

    return f"EDGE-{incident_id}"


# ============================================================
# CREATE EDGE EVENT
# ============================================================

def create_edge_event(row, index):

    severity = str(
        row.get(
            "Severity",
            "LOW"
        )
    ).upper()

    event = {

        "event_id": create_event_id(
            row,
            index
        ),

        "incident_id": row.get(
            "Incident_ID",
            "N/A"
        ),

        "incident_type": row.get(
            "Type",
            "UNKNOWN"
        ),

        "object_id": row.get(
            "Object_ID",
            "N/A"
        ),

        "object_type": row.get(
            "Object_Type",
            "N/A"
        ),

        "severity": severity,

        "confidence": row.get(
            "Confidence",
            "N/A"
        ),

        "video_time": row.get(
            "Video_Time",
            "N/A"
        ),

        "latitude": row.get(
            "Latitude",
            "N/A"
        ),

        "longitude": row.get(
            "Longitude",
            "N/A"
        ),

        "evidence": row.get(
            "Evidence",
            "N/A"
        ),

        "source": "EDGE_AI",

        "created_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "sync_status": "QUEUED",

        "priority": get_priority(
            severity
        )
    }

    return event


# ============================================================
# LOAD INCIDENTS
# ============================================================

def load_incidents():

    if not os.path.exists(
        INCIDENT_FILE
    ):
        print(
            "❌ incidents.csv not found."
        )
        return []

    with open(
        INCIDENT_FILE,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(
            file
        )

        return list(reader)


# ============================================================
# CREATE SYNC QUEUE
# ============================================================

def build_sync_queue():

    incidents = load_incidents()

    if not incidents:
        return

    print()
    print(
        "========================================"
    )
    print(
        "📡 EDGE → CENTRAL DATA SYNC"
    )
    print(
        "========================================"
    )

    events = []

    for index, row in enumerate(
        incidents,
        start=1
    ):

        event = create_edge_event(
            row,
            index
        )

        events.append(
            event
        )

    # Highest priority first
    events.sort(
        key=lambda x: x["priority"]
    )

    created = 0

    for event in events:

        event_id = event[
            "event_id"
        ]

        event_file = os.path.join(
            SYNC_DIR,
            f"{event_id}.json"
        )

        if os.path.exists(
            event_file
        ):
            continue

        with open(
            event_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                event,
                file,
                indent=4
            )

        created += 1

    print(
        f"Incidents found : {len(incidents)}"
    )

    print(
        f"Events queued   : {created}"
    )

    print(
        f"Queue directory : {SYNC_DIR}"
    )

    print(
        "========================================"
    )


# ============================================================
# SIMULATED CENTRAL SERVER
# ============================================================

def send_to_central(event):

    """
    Prototype representation of sending an event
    from the bus/edge device to the central server.

    In production this function can be replaced with:
        requests.post(...)
        MQTT
        WebSocket
        Kafka
        cloud API
    """

    # --------------------------------------------------------
    # Simulate successful network transmission
    # --------------------------------------------------------

    time.sleep(0.05)

    return True


# ============================================================
# SYNC QUEUE
# ============================================================

def sync_queue():

    files = [
        file
        for file in os.listdir(
            SYNC_DIR
        )
        if file.endswith(".json")
    ]

    if not files:

        print(
            "ℹ️ No events waiting for sync."
        )

        return

    # --------------------------------------------------------
    # Read events
    # --------------------------------------------------------

    events = []

    for filename in files:

        path = os.path.join(
            SYNC_DIR,
            filename
        )

        try:

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as file:

                event = json.load(
                    file
                )

            events.append(
                (
                    get_priority(
                        event.get(
                            "severity",
                            "LOW"
                        )
                    ),
                    path,
                    event
                )
            )

        except Exception as error:

            print(
                f"⚠️ Could not read {filename}: {error}"
            )

    # --------------------------------------------------------
    # Priority ordering
    # --------------------------------------------------------

    events.sort(
        key=lambda x: x[0]
    )

    synced = 0
    failed = 0

    for _, path, event in events:

        event_id = event[
            "event_id"
        ]

        print(
            f"📤 Sending {event_id} "
            f"[{event['severity']}]"
        )

        success = send_to_central(
            event
        )

        if success:

            event[
                "sync_status"
            ] = "SYNCED"

            event[
                "synced_at"
            ] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            destination = os.path.join(
                SYNCED_DIR,
                os.path.basename(path)
            )

            with open(
                destination,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    event,
                    file,
                    indent=4
                )

            os.remove(path)

            log_sync(
                event,
                "SYNCED"
            )

            synced += 1

            print(
                f"   ✅ {event_id} synced"
            )

        else:

            event[
                "sync_status"
            ] = "RETRY"

            log_sync(
                event,
                "RETRY"
            )

            failed += 1

            print(
                f"   ❌ {event_id} failed"
            )

    print()
    print(
        "========================================"
    )
    print(
        "SYNC COMPLETE"
    )
    print(
        "========================================"
    )
    print(
        f"Synced : {synced}"
    )
    print(
        f"Failed : {failed}"
    )
    print(
        f"Remaining queue : "
        f"{len(os.listdir(SYNC_DIR))}"
    )
    print(
        "========================================"
    )


# ============================================================
# SYNC LOG
# ============================================================

def log_sync(
    event,
    status
):

    file_exists = os.path.exists(
        SYNC_LOG
    )

    with open(
        SYNC_LOG,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(
            file
        )

        if not file_exists:

            writer.writerow([
                "Event_ID",
                "Incident_ID",
                "Incident_Type",
                "Severity",
                "Priority",
                "Sync_Status",
                "Timestamp"
            ])

        writer.writerow([
            event.get(
                "event_id",
                "N/A"
            ),
            event.get(
                "incident_id",
                "N/A"
            ),
            event.get(
                "incident_type",
                "N/A"
            ),
            event.get(
                "severity",
                "N/A"
            ),
            event.get(
                "priority",
                "N/A"
            ),
            status,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ])


# ============================================================
# BANDWIDTH SAVING ESTIMATE
# ============================================================

def calculate_bandwidth_saving():

    incidents = load_incidents()

    if not incidents:
        return

    # Approximate conceptual comparison:
    #
    # Sending 1 minute of 720p video continuously
    # can be tens of MB.
    #
    # Sending a small JSON event is usually only a few KB.
    #
    # These are estimates for demonstrating the
    # edge-AI architecture, NOT measured network usage.

    estimated_video_mb = (
        len(incidents) * 5
    )

    estimated_metadata_mb = (
        len(incidents) * 0.01
    )

    if estimated_video_mb > 0:

        saving = (
            1
            -
            (
                estimated_metadata_mb
                /
                estimated_video_mb
            )
        ) * 100

    else:

        saving = 0

    print()
    print(
        "📊 EDGE BANDWIDTH CONCEPT"
    )
    print(
        f"Estimated video transfer : "
        f"{estimated_video_mb:.2f} MB"
    )
    print(
        f"Estimated event transfer : "
        f"{estimated_metadata_mb:.2f} MB"
    )
    print(
        f"Potential reduction      : "
        f"{saving:.1f}%"
    )
    print(
        "Note: illustrative estimate, "
        "not measured network traffic."
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    build_sync_queue()

    sync_queue()

    calculate_bandwidth_saving()