"""
Manual Test — Fabric Stream Heartbeat
────────────────────────────────────────────
Simulates AION fusion events so the Fabric Stream
emitter outputs live σ ψ̄ κ̄ values.
"""

import time
import math
from backend.AION.fabric.aion_fabric_resonance import update_latest_fusion_tensor

print("🧠 Sending simulated AION fusion tensors to Fabric Stream ...")
t = 0.0

while True:
    # Generate a simple oscillating fusion tensor
    tensor = {
        "ψ̄": round(0.8 + 0.2 * math.sin(t), 3),
        "κ̄": round(0.9 + 0.05 * math.cos(t), 3),
        "T̄": round(0.95 + 0.03 * math.sin(t / 2), 3),
        "Φ̄": round(1.0, 3),
        "σ": round(0.95 + 0.02 * math.cos(t / 3), 3),
    }

    update_latest_fusion_tensor(tensor)
    print(f"[Simulated] ψ̄={tensor['ψ̄']} κ̄={tensor['κ̄']} σ={tensor['σ']}")
    t += 0.5
    time.sleep(3)