from vision_core import VisionCore

vc = VisionCore()
results = vc.process_image("test_image.jpg")
print("[VisionCore] Detections:", results)