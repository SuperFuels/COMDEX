from backend.modules.aion_prediction.fusion_core import FusionCore
import time

fc = FusionCore()

events = [
    {"symbol": "Φ", "vector": [0.1, 0.2, 0.3], "timestamp": time.time()},
    {"symbol": "λ", "vector": [0.2, 0.3, 0.4], "timestamp": time.time() + 0.5},
    {"symbol": "Ω", "vector": [0.3, 0.2, 0.1], "timestamp": time.time() + 1.0},
]

for e in events:
    result = fc.update(e)
    print(result)

fc.summarize()