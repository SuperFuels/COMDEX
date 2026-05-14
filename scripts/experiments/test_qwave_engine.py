"""
🚀 QWave Engine Continuous Test Runner (Engine-Like Mode + SQI Analysis + Auto-Plot)
-----------------------------------------------------------------------------------
* Runs SupercontainerEngine like a real engine with fueling.
* Logs resonance/drift metrics and harmonics injection.
* Saves best state, full sweep history, and generates auto-plots of trends.
* ✅ SQI micro-analysis suggests tuning improvements based on top runs.
* ✅ Auto-plot of resonance curves, drift history, and field evolution.
"""

import os
import json
import time
import argparse
import statistics
import matplotlib.pyplot as plt
from datetime import datetime
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.supercontainer_engine import SupercontainerEngine, QWaveTuning
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer

# -------------------------
# 🧠 Config Paths
# -------------------------
BEST_STATE_PATH = "data/qwave_logs/qwave_best_state.json"
SWEEP_HISTORY_PATH = "data/qwave_logs/qwave_sweep_history.json"
GRAPH_OUTPUT_PATH = "data/qwave_logs/qwave_summary_graph.png"

# -------------------------
# 🔧 CLI ARGUMENT PARSER
# -------------------------
parser = argparse.ArgumentParser(description="QWave Engine Continuous Test Runner (with SQI analysis + plots)")
parser.add_argument("--pi", action="store_true", help="Run in Pi hardware mode (full SoulLaw & FieldBridge)")
parser.add_argument("--duration", type=int, default=90, help="Run duration per test in seconds (default=90)")
parser.add_argument("--tests", type=int, default=5, help="Number of engine tests (default=5)")
parser.add_argument("--fuel_rate", type=int, default=3, help="Inject particle every N ticks (default=3)")
parser.add_argument("--initial_particles", type=int, default=200, help="Initial particle count to prime engine (default=200)")
args = parser.parse_args()

# -------------------------
# 🌐 SoulLaw Mode Toggle
# -------------------------
os.environ["SOUL_LAW_MODE"] = "full" if args.pi else "test"
print(f"{'🔒 PI MODE' if args.pi else '🧪 SAFE MODE'}: SOUL_LAW_MODE set to {os.environ['SOUL_LAW_MODE']}")

# -------------------------
# 🧠 Score Function
# -------------------------
def score_engine(engine):
    drift_penalty = abs(engine.resonance_filtered[-1] if engine.resonance_filtered else 0)
    exhaust_penalty = sum(e["impact_speed"] for e in engine.exhaust_log[-5:]) / (len(engine.exhaust_log[-5:]) or 1)
    return -(drift_penalty * 1.5 + exhaust_penalty)

# -------------------------
# ✅ Safe QWave Tuning Serializer
# -------------------------
def safe_qwave_tuning():
    """Return only serializable attributes from QWaveTuning."""
    serializable = {}
    for k, v in vars(QWaveTuning).items():
        if not k.startswith("__") and isinstance(v, (int, float, bool, str, list, dict)):
            serializable[k] = v
    return serializable

# -------------------------
# ✅ Safe Sweep History Loader
# -------------------------
def safe_load_history():
    if not os.path.exists(SWEEP_HISTORY_PATH):
        return []
    try:
        with open(SWEEP_HISTORY_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Corrupted sweep history detected. Attempting recovery...")
        with open(SWEEP_HISTORY_PATH, "r") as f:
            raw = f.read()
        try:
            last_valid_idx = raw.rfind("}")
            fixed_json = raw[:last_valid_idx+1] + "]"
            if fixed_json.strip().startswith("["):
                return json.loads(fixed_json)
        except Exception:
            print("⚠️ Recovery failed. Resetting sweep history.")
        return []

# -------------------------
# 💾 Best State Save/Load
# -------------------------
def save_best_state(engine, score):
    state = {
        "score": score,
        "timestamp": datetime.now().isoformat(),
        "fields": engine.fields,
        "stage": engine.stages[engine.current_stage],
        "resonance_phase": engine.resonance_phase,
        "resonance_filtered": engine.resonance_filtered[-20:],
        "harmonics": {
            "values": QWaveTuning.HARMONICS,
            "gain": QWaveTuning.HARMONIC_GAIN,
            "scaled_gain": QWaveTuning.harmonic_for_stage(engine.stages[engine.current_stage])
        },
        "qwave_tuning": safe_qwave_tuning(),
    }
    os.makedirs(os.path.dirname(BEST_STATE_PATH), exist_ok=True)
    with open(BEST_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
    print(f"💾 Best state saved: {BEST_STATE_PATH}")

def load_best_state(engine):
    if not os.path.exists(BEST_STATE_PATH):
        print("⚠️ No saved best state found.")
        return
    with open(BEST_STATE_PATH, "r") as f:
        state = json.load(f)
    engine.fields.update(state.get("fields", {}))
    stage_name = state.get("stage", "plasma_excitation")
    engine.current_stage = engine.stages.index(stage_name)
    print(f"✅ Restored best state: Score={state.get('score', 0):.4f}, Stage={stage_name}")

# -------------------------
# 📜 Sweep History Logger
# -------------------------
def log_sweep_history(test_idx, engine, score):
    record = {
        "test": test_idx,
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "fields": engine.fields,
        "stage": engine.stages[engine.current_stage],
        "resonance_last": engine.resonance_filtered[-1] if engine.resonance_filtered else None,
        "resonance_drift": max(engine.resonance_filtered) - min(engine.resonance_filtered) if engine.resonance_filtered else None,
        "particles": len(engine.particles),
        "harmonics": QWaveTuning.HARMONICS,
        "qwave_tuning": safe_qwave_tuning(),
    }
    history = safe_load_history()
    history.append(record)

    # Backup before overwriting
    if os.path.exists(SWEEP_HISTORY_PATH):
        os.rename(SWEEP_HISTORY_PATH, SWEEP_HISTORY_PATH + ".bak")

    with open(SWEEP_HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)
    print(f"📜 Sweep history appended: {SWEEP_HISTORY_PATH}")

# -------------------------
# 🔬 SQI Micro-Analysis
# -------------------------
def run_sqi_micro_analysis():
    history = safe_load_history()
    if not history:
        print("⚠️ No sweep history found. SQI analysis skipped.")
        return

    sorted_runs = sorted(history, key=lambda r: r["score"], reverse=True)
    top_runs = sorted_runs[:max(1, len(sorted_runs)//4)]

    field_avgs = {f: statistics.mean([r["fields"][f] for r in top_runs]) for f in ["gravity","magnetism","wave_frequency"]}
    drift_avgs = statistics.mean([r["resonance_drift"] or 0 for r in top_runs])

    print("\n🔬 [SQI Micro-Analysis Results]")
    print(f"📈 Top {len(top_runs)} runs analyzed.")
    print(f"⚙ Recommended field targets: Gravity={field_avgs['gravity']:.3f}, Magnetism={field_avgs['magnetism']:.3f}, Wave_Freq={field_avgs['wave_frequency']:.3f}")
    print(f"🔎 Avg Drift (top runs): {drift_avgs:.4f}")
    print("🎯 Suggestion: Tune engine fields towards these averages and re-run for tighter resonance stability.\n")

# -------------------------
# 📊 Auto-Plot Sweep Data
# -------------------------
def plot_sweep_history():
    history = safe_load_history()
    if not history:
        print("⚠️ No sweep history found for plotting.")
        return

    tests = [r["test"]+1 for r in history]
    resonance = [r["resonance_last"] or 0 for r in history]
    drift = [r["resonance_drift"] or 0 for r in history]
    gravity = [r["fields"]["gravity"] for r in history]
    magnetism = [r["fields"]["magnetism"] for r in history]
    wave_freq = [r["fields"]["wave_frequency"] for r in history]

    plt.figure(figsize=(14, 10))

    # Resonance Curve
    plt.subplot(3, 1, 1)
    plt.plot(tests, resonance, marker='o', label="Resonance (Last)")
    plt.axhline(0, color='gray', linestyle='--')
    plt.title("QWave Resonance Over Tests")
    plt.ylabel("Resonance Level")
    plt.grid(True)
    plt.legend()

    # Drift Curve
    plt.subplot(3, 1, 2)
    plt.plot(tests, drift, marker='x', color='orange', label="Resonance Drift")
    plt.axhline(0, color='gray', linestyle='--')
    plt.ylabel("Drift")
    plt.title("Resonance Drift Stability")
    plt.grid(True)
    plt.legend()

    # Field Evolution
    plt.subplot(3, 1, 3)
    plt.plot(tests, gravity, label="Gravity")
    plt.plot(tests, magnetism, label="Magnetism")
    plt.plot(tests, wave_freq, label="Wave Frequency")
    plt.title("Field Evolution Across Tests")
    plt.xlabel("Test #")
    plt.ylabel("Field Strengths")
    plt.legend()
    plt.grid(True)

    os.makedirs(os.path.dirname(GRAPH_OUTPUT_PATH), exist_ok=True)
    plt.tight_layout()
    plt.savefig(GRAPH_OUTPUT_PATH)
    print(f"📊 Sweep graphs saved: {GRAPH_OUTPUT_PATH}")

# -------------------------
# 🚀 Continuous Engine Test Loop
# -------------------------
best_score = None

for test in range(args.tests):
    print(f"\n🚀 Test {test+1}/{args.tests}: Spooling engine...")

    sec = SymbolicExpansionContainer(container_id=f"test-{test}")
    engine = SupercontainerEngine(
        container=sec,
        safe_mode=not args.pi,
        stage_lock=None if args.pi else 4,
        virtual_absorber=True
    )

    load_best_state(engine)

    for _ in range(args.initial_particles):
        engine.inject_proton()

    start_time = time.time()
    tick_counter = 0

    while time.time() - start_time < args.duration:
        engine.tick()
        tick_counter += 1

        if engine.stages[engine.current_stage] in ["plasma_excitation", "wave_focus"]:
            engine._inject_harmonics(QWaveTuning.HARMONICS)

        if tick_counter % args.fuel_rate == 0:
            engine.inject_proton()

        if tick_counter % int(5 / engine.tick_delay) == 0:
            drift = max(engine.resonance_filtered[-20:], default=0) - min(engine.resonance_filtered[-20:], default=0)
            print(f"⏱ Tick {tick_counter} | Resonance={engine.resonance_phase:.4f} | Drift={drift:.4f}")

    current_score = score_engine(engine)
    log_sweep_history(test, engine, current_score)

    if best_score is None or current_score > best_score:
        best_score = current_score
        save_best_state(engine, current_score)

    engine.export_logs()
    engine._export_dc_trace()

    if engine.resonance_filtered:
        drift = max(engine.resonance_filtered) - min(engine.resonance_filtered)
        print(f"🔎 End Test Resonance: Last={engine.resonance_filtered[-1]:.4f} | Drift={drift:.4f}")

# ✅ SQI Analysis + Graph Plot
run_sqi_micro_analysis()
plot_sweep_history()