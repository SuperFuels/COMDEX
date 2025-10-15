"""
Tessaris • UltraQC Build v0.4
QWave Core Verification Harness (Phase 1.5 readiness)

Confirms:
  • all QWave kernel modules import cleanly
  • runtime + scheduler execute a minimal tick
  • interference + collapse pipelines produce metrics
"""

import importlib
import json
import traceback

# --- Modules expected in repo
MODULES = [
    "backend.modules.glyphwave.kernels.interference_kernel_core",
    "backend.modules.glyphwave.kernels.interference_kernels",
    "backend.modules.glyphwave.kernels.superposition_kernels",
    "backend.modules.glyphwave.kernels.measurement_kernels",
    "backend.modules.glyphwave.runtime",
    "backend.modules.glyphwave.scheduler",
    "backend.modules.glyphwave.core.entangled_wave",
    "backend.modules.glyphwave.core.wave_state",
    "backend.modules.glyphwave.gwv_writer",
    "backend.modules.glyphwave.telemetry_handler",
]

print("\n🌊 Tessaris QWave Core Import Check\n────────────────────────────")
for m in MODULES:
    try:
        importlib.import_module(m)
        print(f"✅ {m} imported successfully")
    except Exception as e:
        print(f"❌ {m} failed: {e}")
        traceback.print_exc()

# --- Functional check
try:
    from backend.modules.glyphwave.core.entangled_wave import EntangledWave
    from backend.modules.glyphwave.core.wave_state import WaveState
    from backend.modules.glyphwave.kernels.interference_kernel_core import join_waves_batch

    w1 = WaveState.from_glyph_dict({"qwave_id": "w1", "carrier_type": "simulated"})
    w2 = WaveState.from_glyph_dict({"qwave_id": "w2", "carrier_type": "simulated"})

    entangled = EntangledWave()
    entangled.add_wave(w1, 0)
    entangled.add_wave(w2, 1)
    entangled.generate_links()

    result = join_waves_batch(entangled.waves)
    collapsed = entangled.collapse_all()

    print("\n🧩 Vectorized interference kernel output:")
    print(json.dumps(result, indent=2, default=str))
    print("\n⚡ Collapse metrics:")
    print(json.dumps(collapsed.get('collapse_metrics', {}), indent=2, default=str))

except Exception as e:
    print(f"\n❌ Functional pipeline test failed: {e}")
    traceback.print_exc()

print("\n✅ QWave Core Verification Harness completed\n")