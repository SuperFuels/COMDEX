"""
🧪 QWave Engine Test Runner (Safe Mode or Pi Mode)
-----------------------------------------------------
• Runs SupercontainerEngine in SAFE MODE (Mac debug) or PI MODE (full hardware loop).
• Logs resonance phase, particle velocity deltas, and exhaust impact speeds.
• Auto-advances stages during runtime (proton → plasma → wave focus).
• Exports logs & graphs for offline analysis.
"""

import os
import argparse
import matplotlib.pyplot as plt
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.supercontainer_engine import SupercontainerEngine
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer

# -------------------------
# 🔧 CLI ARGUMENT PARSER
# -------------------------
parser = argparse.ArgumentParser(description="QWave Engine Test Runner")
parser.add_argument("--pi", action="store_true", help="Run in Pi hardware mode (full SoulLaw & FieldBridge)")
parser.add_argument("--ticks", type=int, default=300, help="Number of simulation ticks (default=300)")
args = parser.parse_args()

# -------------------------
# 🌐 SoulLaw Mode Toggle
# -------------------------
if args.pi:
    os.environ["SOUL_LAW_MODE"] = "full"   # ✅ Full enforcement for Pi hardware
    print("🔒 Running in PI MODE (SOUL_LAW_MODE=full)")
else:
    os.environ["SOUL_LAW_MODE"] = "test"   # ✅ Relaxed validation for MacBook debug
    print("🧪 Running in SAFE MODE (SOUL_LAW_MODE=test)")

# -------------------------
# ⚙️ Engine Initialization
# -------------------------
sec = SymbolicExpansionContainer(container_id="test-sec")
engine = SupercontainerEngine(
    container=sec,
    safe_mode=not args.pi,          # ✅ Hardware bypass in safe-mode (MacBook debug)
    stage_lock=3 if not args.pi else None,  # Limit to first 3 stages in debug only
    virtual_absorber=not args.pi    # Enable exhaust logging in safe-mode
)

print(f"🚀 QWave Engine Simulation: {'Hardware (Pi)' if args.pi else 'Debug (Mac Safe-Mode)'}")

# -------------------------
# 🔄 Tick Loop
# -------------------------
for i in range(args.ticks):
    engine.tick()  # Advance engine physics
    if not args.pi and i in [100, 200]:
        engine.advance_stage()  # Controlled stage advance in debug mode

print("✅ Simulation complete.")

# -------------------------
# 📊 Extract Metrics
# -------------------------
velocity_deltas = [p.get("velocity_delta", 0) for p in engine.particles]
resonance = engine.resonance_log
exhaust_speeds = [e["impact_speed"] for e in engine.exhaust_log]

# -------------------------
# 📈 Plot Key Metrics
# -------------------------
plt.figure(figsize=(14, 4))

# 1️⃣ Velocity Δ (Particle acceleration profile)
plt.subplot(1, 3, 1)
plt.plot(velocity_deltas, color='cyan')
plt.title("Velocity Δ (Particle Acceleration)")
plt.xlabel("Particles")
plt.ylabel("Δv per Tick")

# 2️⃣ Wave Resonance Phase
plt.subplot(1, 3, 2)
plt.plot(resonance, color='yellow')
plt.title("Wave Resonance Phase (sin)")
plt.xlabel("Ticks")
plt.ylabel("Resonance")

# 3️⃣ Exhaust Impact Speeds (Virtual Absorber)
plt.subplot(1, 3, 3)
plt.plot(exhaust_speeds if exhaust_speeds else [0], color='red')
plt.title("Exhaust Impact Speeds")
plt.xlabel("Impact Events")
plt.ylabel("Speed (m/s)")

plt.tight_layout()
plt.show()

# ✅ Export logs & graphs
engine.export_logs()
print("📂 Logs and graphs exported to: data/qwave_logs/")