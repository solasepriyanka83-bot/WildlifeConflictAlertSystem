"""
detector.py
YOLOv8 wildlife detection wrapper.

Two modes:
  REAL MODE  -> loads yolov8n.pt via ultralytics and runs real inference
                on an incoming image. Requires `pip install ultralytics`
                and the model weights (auto-downloaded on first run if
                you have internet access on your machine).
  MOCK MODE  -> no model / no internet needed. Simulates a detection so
                the whole dashboard, alerts, gallery, reports, etc. are
                fully demoable end-to-end without hardware.

Toggle with USE_REAL_YOLO below, or the env var USE_REAL_YOLO=1.
"""

import os
import random
import shutil
from datetime import datetime

USE_REAL_YOLO = os.environ.get("USE_REAL_YOLO", "0") == "1"

TARGET_CLASSES = [
    "person", "dog", "cat", "cow", "buffalo",
    "monkey", "deer", "elephant", "leopard", "tiger",
]

IMAGE_DIR = os.path.join("static", "images", "detections")
os.makedirs(IMAGE_DIR, exist_ok=True)

_model = None


def _load_model():
    """Lazy-load the YOLOv8 model only if real mode is enabled."""
    global _model
    if _model is None:
        from ultralytics import YOLO
        _model = YOLO("yolov8n.pt")
    return _model


def run_detection_real(image_path):
    """
    Run actual YOLOv8 inference on an image file and return
    a list of (class_name, confidence) filtered to TARGET_CLASSES.
    """
    model = _load_model()
    results = model(image_path)
    detections = []
    for r in results:
        for box in r.boxes:
            cls_name = model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            if cls_name.lower() in TARGET_CLASSES:
                detections.append((cls_name.lower(), round(conf * 100, 2)))
    return detections


def run_detection_mock(image_path=None):
    """
    Simulates one YOLOv8 detection event without needing a model
    or GPU. Used for demo / prototype / exhibition purposes.
    """
    animal = random.choice(TARGET_CLASSES)
    confidence = round(random.uniform(72.0, 98.5), 2)
    return [(animal, confidence)]


def save_incoming_image(file_storage_or_path):
    """
    Saves an uploaded image (from ESP32-CAM POST or manual upload)
    into static/images/detections/ with a unique timestamped name.
    Accepts either a Flask FileStorage object or a filesystem path.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"detection_{timestamp}.jpg"
    dest_path = os.path.join(IMAGE_DIR, filename)

    if hasattr(file_storage_or_path, "save"):
        file_storage_or_path.save(dest_path)
    else:
        shutil.copy(file_storage_or_path, dest_path)

    return filename


def save_incoming_image_placeholder():
    """
    Used when the 'Simulate Detection' button fires with no real image
    attached (e.g. no camera hardware connected yet). Copies a generated
    placeholder frame so gallery/records still have something to show.
    """
    from PIL import Image, ImageDraw

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"detection_{timestamp}.jpg"
    dest_path = os.path.join(IMAGE_DIR, filename)

    img = Image.new("RGB", (640, 480), color=(14, 42, 28))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 630, 470], outline=(60, 200, 130), width=3)
    draw.text((40, 220), "SIMULATED CAMERA FRAME", fill=(120, 255, 180))
    draw.text((40, 250), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fill=(180, 220, 200))
    img.save(dest_path, "JPEG")
    return filename


def process_and_detect(file_storage_or_path, location="Main Gate - Zone A"):
    """
    Full pipeline: save image -> run detection -> return structured result.
    Falls back to mock mode automatically if ultralytics isn't installed.
    """
    filename = save_incoming_image(file_storage_or_path)
    full_path = os.path.join(IMAGE_DIR, filename)

    detections = []
    if USE_REAL_YOLO:
        try:
            detections = run_detection_real(full_path)
        except Exception as e:
            print(f"[detector] Real YOLO failed ({e}), falling back to mock.")
            detections = run_detection_mock(full_path)
    else:
        detections = run_detection_mock(full_path)

    if not detections:
        return None

    animal_name, confidence = detections[0]
    return {
        "animal_name": animal_name,
        "confidence": confidence,
        "image_name": filename,
        "location": location,
    }
