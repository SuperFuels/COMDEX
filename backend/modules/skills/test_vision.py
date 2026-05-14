from vision_core import VisionCore

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

vc = VisionCore()
results = vc.process_image("test_image.jpg")
print("[VisionCore] Detections:", results)