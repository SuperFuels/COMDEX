#!/usr/bin/env python3
from backend.modules.aion_prediction.fusion_core import FusionCore
import json
import time
from pathlib import Path

fc = FusionCore()
stream_path = Path("data/feedback/resonance_stream.jsonl")
stream_path.parent.mkdir(parents=True, exist_ok=True)

events = [
    {"symbol": "Φ", "vector": [0.1, 0.2, 0.3], "timestamp": time.time()},
    {"symbol": "λ", "vector": [0.2, 0.3, 0.4], "timestamp": time.time() + 0.5},
    {"symbol": "Ω", "vector": [0.3, 0.2, 0.1], "timestamp": time.time() + 1.0},
]

for e in events:
    result = fc.update(e)
    e["RSI"] = result.get("RSI", 0.0)
    e["epsilon"] = result.get("ε", 0.0)
    e["k"] = result.get("k", 0)
    # Write to shared resonance log
    with open(stream_path, "a") as f:
        f.write(json.dumps(e) + "\n")
    print("Logged:", e)

fc.summarize()
print("✅ Symbolized resonance stream updated.")