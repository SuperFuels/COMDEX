import cv2
import numpy as np

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class VisionCore:
    def __init__(self):
        print("[VisionCore] Initialized")

    def process_image(self, image_path: str, save_output=True) -> dict:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image at: {image_path}")

        # Simulate object detection
        height, width, _ = image.shape
        detections = [
            {"label": "object_1", "bbox": [int(0.1*width), int(0.1*height), int(0.3*width), int(0.3*height)]},
            {"label": "object_2", "bbox": [int(0.5*width), int(0.4*height), int(0.7*width), int(0.6*height)]}
        ]

        # Draw boxes
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cv2.rectangle(image, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(image, det["label"], (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        if save_output:
            output_path = image_path.replace(".jpg", "_vision.jpg")
            cv2.imwrite(output_path, image)
            print(f"[VisionCore] Saved output to {output_path}")

        return {
            "input": image_path,
            "detections": detections
        }