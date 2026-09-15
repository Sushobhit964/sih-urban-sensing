import os
import csv
import json
import hmac
import hashlib
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

INCIDENT_FILE = "output/incidents.csv"
AUDIT_FILE = "output/security_audit.csv"
CHAIN_FILE = "output/event_chain.json"

SECRET_ENV = "SIH_SECURITY_SECRET"


# ============================================================
# SECURITY ENGINE
# ============================================================

class SecurityAudit:

    def __init__(self):
        self.audit_file = AUDIT_FILE
        self.chain_file = CHAIN_FILE

        os.makedirs("output", exist_ok=True)

        # Never hard-code a production secret.
        # A demo fallback is provided so the prototype runs immediately.
        self.secret = os.getenv(
            SECRET_ENV,
            "SIH-DEMO-SECRET-CHANGE-IN-PRODUCTION"
        ).encode()

        self._ensure_audit_file()
        self.chain = self._load_chain()

    # --------------------------------------------------------
    # CREATE AUDIT FILE
    # --------------------------------------------------------

    def _ensure_audit_file(self):

        if not os.path.exists(self.audit_file):

            with open(self.audit_file, "w", newline="") as file:

                writer = csv.writer(file)

                writer.writerow([
                    "Audit_ID",
                    "Incident_ID",
                    "Event_Hash",
                    "HMAC_Signature",
                    "Previous_Hash",
                    "Timestamp",
                    "Verification_Status"
                ])

    # --------------------------------------------------------
    # LOAD HASH CHAIN
    # --------------------------------------------------------

    def _load_chain(self):

        if os.path.exists(self.chain_file):

            try:

                with open(self.chain_file, "r") as file:
                    return json.load(file)

            except Exception:
                return []

        return []

    # --------------------------------------------------------
    # SAVE HASH CHAIN
    # --------------------------------------------------------

    def _save_chain(self):

        with open(self.chain_file, "w") as file:

            json.dump(
                self.chain,
                file,
                indent=4
            )

    # --------------------------------------------------------
    # CREATE EVENT HASH
    # --------------------------------------------------------

    def create_event_hash(self, incident):

        event_string = json.dumps(
            incident,
            sort_keys=True,
            separators=(",", ":")
        )

        return hashlib.sha256(
            event_string.encode()
        ).hexdigest()

    # --------------------------------------------------------
    # CREATE HMAC SIGNATURE
    # --------------------------------------------------------

    def create_signature(self, event_hash):

        return hmac.new(
            self.secret,
            event_hash.encode(),
            hashlib.sha256
        ).hexdigest()

    # --------------------------------------------------------
    # ADD SECURE INCIDENT
    # --------------------------------------------------------

    def secure_incident(self, incident):

        incident_id = str(
            incident.get("Incident_ID", "UNKNOWN")
        )

        timestamp = datetime.now().isoformat()

        # Previous event hash
        if self.chain:

            previous_hash = self.chain[-1]["Event_Hash"]

        else:

            previous_hash = "GENESIS"

        # Create event hash
        event_hash = self.create_event_hash(incident)

        # Create HMAC signature
        signature = self.create_signature(event_hash)

        audit_id = (
            "AUD-"
            + hashlib.sha256(
                (incident_id + timestamp).encode()
            ).hexdigest()[:12]
        )

        event = {

            "Audit_ID": audit_id,

            "Incident_ID": incident_id,

            "Event_Hash": event_hash,

            "HMAC_Signature": signature,

            "Previous_Hash": previous_hash,

            "Timestamp": timestamp,

            "Verification_Status": "VERIFIED"
        }

        # Add to chain
        self.chain.append(event)

        self._save_chain()

        # Write audit record
        with open(
            self.audit_file,
            "a",
            newline=""
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                audit_id,
                incident_id,
                event_hash,
                signature,
                previous_hash,
                timestamp,
                "VERIFIED"
            ])

        print()
        print("========================================")
        print("🔐 SECURE EVENT CREATED")
        print("========================================")
        print(f"Audit ID       : {audit_id}")
        print(f"Incident ID    : {incident_id}")
        print(f"Event Hash     : {event_hash[:20]}...")
        print(f"HMAC Signature : {signature[:20]}...")
        print(f"Previous Hash  : {previous_hash[:20]}...")
        print("Status         : VERIFIED")
        print("========================================")

        return event

    # --------------------------------------------------------
    # VERIFY HMAC
    # --------------------------------------------------------

    def verify_signature(
        self,
        event_hash,
        signature
    ):

        expected_signature = self.create_signature(
            event_hash
        )

        return hmac.compare_digest(
            expected_signature,
            signature
        )

    # --------------------------------------------------------
    # VERIFY HASH CHAIN
    # --------------------------------------------------------

    def verify_chain(self):

        if not self.chain:

            print("⚠️ No security events found.")

            return True

        previous_hash = "GENESIS"

        for event in self.chain:

            # Check chain connection
            if event["Previous_Hash"] != previous_hash:

                print()
                print("🚨 CHAIN TAMPERING DETECTED")
                print(
                    f"Incident: {event['Incident_ID']}"
                )

                return False

            # Check HMAC
            valid_signature = self.verify_signature(
                event["Event_Hash"],
                event["HMAC_Signature"]
            )

            if not valid_signature:

                print()
                print("🚨 SIGNATURE INVALID")
                print(
                    f"Incident: {event['Incident_ID']}"
                )

                return False

            previous_hash = event["Event_Hash"]

        print()
        print("========================================")
        print("🛡️ SECURITY VERIFICATION")
        print("========================================")
        print(f"Events Checked : {len(self.chain)}")
        print("Hash Chain     : VALID")
        print("HMAC           : VALID")
        print("Tampering      : NOT DETECTED")
        print("Status         : TRUSTED")
        print("========================================")

        return True


# ============================================================
# READ INCIDENTS
# ============================================================

def load_incidents():

    if not os.path.exists(INCIDENT_FILE):

        print(
            f"❌ Incident file not found: "
            f"{INCIDENT_FILE}"
        )

        return []

    with open(
        INCIDENT_FILE,
        "r",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        return list(reader)


# ============================================================
# SECURE EXISTING INCIDENTS
# ============================================================

def secure_existing_incidents():

    incidents = load_incidents()

    if not incidents:

        print("⚠️ No incidents available.")

        return

    security = SecurityAudit()

    existing_ids = {
        event["Incident_ID"]
        for event in security.chain
    }

    secured_count = 0

    for incident in incidents:

        incident_id = incident.get(
            "Incident_ID",
            "UNKNOWN"
        )

        # Don't secure the same incident twice
        if incident_id in existing_ids:

            continue

        security.secure_incident(
            incident
        )

        secured_count += 1

    print()
    print(
        f"🔐 Newly secured incidents: "
        f"{secured_count}"
    )

    print(
        f"📦 Total chain events: "
        f"{len(security.chain)}"
    )

    # Verify everything after processing
    security.verify_chain()


# ============================================================
# DEMO / MAIN
# ============================================================

if __name__ == "__main__":

    print()
    print("========================================")
    print("🔐 SIH CENTRAL SECURITY AUDIT")
    print("========================================")

    secure_existing_incidents()