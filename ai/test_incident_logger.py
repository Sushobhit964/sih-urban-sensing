from incident_logger import IncidentLogger


logger = IncidentLogger()


logger.log_incident(
    incident_id="TEST001",
    incident_type="POTHOLE",
    object_id=1,
    object_type="Road",
    severity="HIGH",
    confidence=0.91,
    video_time="00:12.50",
    latitude="N/A",
    longitude="N/A",
    evidence="test.jpg"
)


print()
print("Incident logger working!")