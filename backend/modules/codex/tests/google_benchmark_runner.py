# 📁 backend/modules/codex/tests/google_benchmark_runner.py
import os, time, json, asyncio
from datetime import datetime

from backend.QQC.qqc_central_kernel import QuantumQuadCore  # ✅ Full-stack orchestrator
from backend.modules.codex.codex_metrics import (
    score_glyph_tree,
    record_sqi_score_event,
    load_last_benchmark_score,
)
from backend.modules.consciousness.state_manager import STATE, load_container_from_file
from backend.modules.sqi.sqi_event_bus import GPIO_AVAILABLE


def ensure_container(container_id="maxwell_core"):
    """Ensure that a test container is loaded and bound."""
    dc_path = os.path.join(os.path.dirname(__file__), "../../dimensions/containers", f"{container_id}.dc.json")
    if os.path.exists(dc_path):
        load_container_from_file(dc_path)
        return container_id
    STATE.set_current_container({
        "id": container_id,
        "meta": {"ghx": {"hover": True, "collapsed": True}}
    })
    return container_id


# ==============================
# ⟦ Raw compressed QGlyph benchmark tree ⟧
# ==============================
compressed_qglyph_tree = {
    "↔": [
        {
            "⊕": [
                {"⊕": ["A1", "B1"]},
                {"⟲": ["A2", "B2"]}
            ]
        },
        {
            "->": [
                {
                    "⊕": [
                        {"->": ["A3", "B3"]},
                        {"⊕": ["A4", "B4"]}
                    ]
                },
                {
                    "->": [
                        {
                            "⧖": [
                                {"⟲": ["A5", "B5"]},
                                {
                                    "↔": [
                                        {"⟲": ["C1", "D1"]},
                                        {"->": ["C2", "D2"]}
                                    ]
                                }
                            ]
                        },
                        {
                            "->": [
                                {"⊕": ["E1", {"⧖": ["E2", "E3"]}]},
                                {
                                    "->": [
                                        {"->": ["F1", "F2"]},
                                        {
                                            "->": [
                                                {"⟲": ["G1", "G2"]},
                                                {
                                                    "->": [
                                                        {"⊕": ["H1", {"↔": ["H2", "H3"]}]},
                                                        {
                                                            "->": [
                                                                {"⧖": ["I1", "I2"]},
                                                                {
                                                                    "->": [
                                                                        {"⊕": ["J1", "J2"]},
                                                                        {
                                                                            "->": [
                                                                                {"->": ["K1", "K2"]},
                                                                                {
                                                                                    "->": [
                                                                                        {"⟲": ["L1", "L2"]},
                                                                                        {
                                                                                            "->": [
                                                                                                {"⊕": ["M1", "M2"]},
                                                                                                {
                                                                                                    "->": [
                                                                                                        {"⧖": ["N1", "N2"]},
                                                                                                        {
                                                                                                            "->": [
                                                                                                                {"↔": ["O1", "O2"]},
                                                                                                                {
                                                                                                                    "->": [
                                                                                                                        {"->": ["P1", "P2"]},
                                                                                                                        {
                                                                                                                            "->": [
                                                                                                                                {"⟲": ["Q1", "Q2"]},
                                                                                                                                {
                                                                                                                                    "->": [
                                                                                                                                        {"⊕": ["R1", "R2"]},
                                                                                                                                        {
                                                                                                                                            "->": [
                                                                                                                                                {"⧖": ["S1", "S2"]},
                                                                                                                                                {
                                                                                                                                                    "->": [
                                                                                                                                                        {"↔": ["T1", "T2"]},
                                                                                                                                                        {
                                                                                                                                                            "->": [
                                                                                                                                                                {"->": ["U1", "U2"]},
                                                                                                                                                                {
                                                                                                                                                                    "->": [
                                                                                                                                                                        {"⟲": ["V1", "V2"]},
                                                                                                                                                                        {
                                                                                                                                                                            "->": [
                                                                                                                                                                                {"⊕": ["W1", "W2"]},
                                                                                                                                                                                {
                                                                                                                                                                                    "->": [
                                                                                                                                                                                        {"⧖": ["X1", "X2"]},
                                                                                                                                                                                        {
                                                                                                                                                                                            "->": [
                                                                                                                                                                                                {"↔": ["Y1", "Y2"]},
                                                                                                                                                                                                {
                                                                                                                                                                                                    "->": [
                                                                                                                                                                                                        {"->": ["Z1", "Z2"]},
                                                                                                                                                                                                        {"⟲": ["Z3", "Z4"]}
                                                                                                                                                                                                    ]
                                                                                                                                                                                                }
                                                                                                                                                                                            ]
                                                                                                                                                                                        }
                                                                                                                                                                                    ]
                                                                                                                                                                                }
                                                                                                                                                                            ]
                                                                                                                                                                        }
                                                                                                                                                                    ]
                                                                                                                                                                }
                                                                                                                                                            ]
                                                                                                                                                        }
                                                                                                                                                    ]
                                                                                                                                                }
                                                                                                                                            ]
                                                                                                                                        }
                                                                                                                                    ]
                                                                                                                                }
                                                                                                                            ]
                                                                                                                        }
                                                                                                                    ]
                                                                                                                }
                                                                                                            ]
                                                                                                        }
                                                                                                    ]
                                                                                                }
                                                                                            ]
                                                                                        }
                                                                                    ]
                                                                                }
                                                                            ]
                                                                        }
                                                                    ]
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}


# ==============================
# ⚙️ Benchmark Runner (Full QQC Stack)
# ==============================
def run_full_stack_benchmark(hyperdrive_enabled=True):
    """
    Runs a full Codex -> QQC -> SQI benchmark with optional Hyperdrive guard toggling.
    """
    print(f"\n⚡ Running QQC Benchmark | Hyperdrive={'ON' if hyperdrive_enabled else 'OFF'}")

    os.environ["AION_FORCE_HARDWARE"] = "1" if hyperdrive_enabled else "0"
    container_id = ensure_container("maxwell_core")

    # Initialize QQC
    qqc = QuantumQuadCore(container_id=container_id)
    qqc.bind_hyperdrive_guard(hyperdrive_enabled)

    # Run CodexLang programs with your symbolic tree
    programs = [
        "⟦ Logic | Test: A ⊕ B -> ↔(Ψ1, Ψ2) ⟧",
        "⟦ Logic | Cascade: (A ⊕ B) ⟲ C -> ⧖(Ψ1, ↔(Ψ2, Ψ3)) ⟧"
    ]

    for codex_program in programs:
        print(f"\n🧠 Executing CodexLang Program:\n   {codex_program}")

        # Build safe test context (bypasses QKD policy enforcement)
        context = {
            "wave_beams": compressed_qglyph_tree,
            "benchmark_mode": True,
            "disable_qkd_policy": True,   # ✅ Prevents Missing GKey errors
            "source": "QQC_Benchmark",
            "container_id": container_id,
        }

        start = time.perf_counter()
        result = qqc.run_codex_program(codex_program, context=context)
        duration = time.perf_counter() - start

        print(f"   ⏱️ Duration: {duration*1000:.2f} ms")
        print(f"   ✅ QQC Result: {result}")

    # Score symbolic structure of the benchmark tree
    symbolic_score = score_glyph_tree(compressed_qglyph_tree)
    entropy = len(json.dumps(compressed_qglyph_tree))
    ratio = round(entropy / symbolic_score, 3) if symbolic_score else 0

    # SQI metrics payload
    sqi_payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": "QQC_BENCHMARK",
        "container_id": container_id,
        "symbolic_score": symbolic_score,
        "entropy": entropy,
        "compression_ratio": ratio,
        "hardware_mode": GPIO_AVAILABLE,
        "hyperdrive_guard": hyperdrive_enabled,
        "execution_time_ms": duration * 1000,
    }
    record_sqi_score_event(sqi_payload)

    # Compare to previous benchmark
    prev = load_last_benchmark_score()
    improvement = 0.0
    if prev and prev.get("symbolic_score"):
        improvement = round((symbolic_score - prev["symbolic_score"]) / prev["symbolic_score"] * 100, 2)

    print(f"\n🧪 QQC Full-Stack Kernel Executed")
    print(f"⏱️ Execution Time: {duration*1000:.2f} ms")
    print(f"📏 Symbolic Depth Score: {symbolic_score}")
    print(f"🌀 Entropy Estimate: {entropy} chars")
    print(f"🔁 Compression Ratio: {ratio}x")
    print(f"⚙️ GPIO_AVAILABLE: {GPIO_AVAILABLE}")
    print(f"🛡️ Hyperdrive Guard: {hyperdrive_enabled}")
    print(f"📈 ΔSymbolic Score vs Last Run: {improvement:+.2f}%")
    print(f"✅ QQC Result (final):", result, "\n")

    # Save results
    metrics_path = f"./benchmarks/last_benchmark_{container_id}_{'HD' if hyperdrive_enabled else 'NOHD'}.json"
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(sqi_payload, f, indent=2)

    return symbolic_score, duration

# ==============================
# 🚀 Dual-mode comparison
# ==============================
async def async_run():
    print("\n🚀 QQC Dual-Mode Benchmark Initiated (Hyperdrive ON/OFF)\n")

    score_hd, dur_hd = run_full_stack_benchmark(hyperdrive_enabled=True)
    score_nohd, dur_nohd = run_full_stack_benchmark(hyperdrive_enabled=False)

    diff = round((score_hd - score_nohd) / (score_nohd or 1) * 100, 2)
    time_diff = round((dur_nohd - dur_hd) / (dur_nohd or 1) * 100, 2)

    print("📊 Final Comparative Report")
    print(f"   ΔSymbolic Score (HD vs NOHD): {diff:+.2f}%")
    print(f"   ΔExecution Time (NOHD -> HD): {time_diff:+.2f}% faster with Hyperdrive")
    print("✅ Benchmark completed.\n")


if __name__ == "__main__":
    asyncio.run(async_run())