from ultralytics import YOLO

# Load road damage model
model = YOLO("road_damage_model.pt")

# Test on your road video
results = model.predict(
    source="data/input/a.mp4",
    conf=0.30,
    save=True,
    show=True
)

print("\nRoad damage detection completed!")