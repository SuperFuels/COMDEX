# backend/devtools/generate_resonance_trends.py
import csv, math, time, random
from pathlib import Path

OUT = Path("data/telemetry/resonance_trends.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["ts", "SQI"])
    writer.writeheader()
    base = time.time()
    for i in range(60):
        # Generate a smooth pseudo-resonant SQI curve with noise
        sqi = 0.7 + 0.2 * math.sin(i / 8.0) + random.uniform(-0.03, 0.03)
        writer.writerow({"ts": base + i * 60, "SQI": round(sqi, 4)})

print(f"[Seed] Wrote synthetic trend data -> {OUT}")