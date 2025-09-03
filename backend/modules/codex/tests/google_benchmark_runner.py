# 📁 backend/modules/codex/tests/google_benchmark_runner.py
import time, json, os, asyncio

from backend.modules.codex.codex_metrics import score_glyph_tree
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.consciousness.state_manager import STATE, load_container_from_file

def ensure_container(container_id="maxwell_core"):
    dc_path = os.path.join(os.path.dirname(__file__), "../../dimensions/containers", f"{container_id}.dc.json")
    if os.path.exists(dc_path):
        load_container_from_file(dc_path)
        return container_id
    STATE.set_current_container({"id": container_id, "meta": {"ghx": {"hover": True, "collapsed": True}}})
    return container_id

# ⟦ Raw compressed QGlyph benchmark tree ⟧
compressed_qglyph_tree = {
    "↔": [
        {
            "⊕": [
                {"⊕": ["A1", "B1"]},
                {"⟲": ["A2", "B2"]}
            ]
        },
        {
            "→": [
                {
                    "⊕": [
                        {"→": ["A3", "B3"]},
                        {"⊕": ["A4", "B4"]}
                    ]
                },
                {
                    "→": [
                        {
                            "⧖": [
                                {"⟲": ["A5", "B5"]},
                                {
                                    "↔": [
                                        {"⟲": ["C1", "D1"]},
                                        {"→": ["C2", "D2"]}
                                    ]
                                }
                            ]
                        },
                        {
                            "→": [
                                {"⊕": ["E1", {"⧖": ["E2", "E3"]}]},
                                {
                                    "→": [
                                        {"→": ["F1", "F2"]},
                                        {
                                            "→": [
                                                {"⟲": ["G1", "G2"]},
                                                {
                                                    "→": [
                                                        {"⊕": ["H1", {"↔": ["H2", "H3"]}]},
                                                        {
                                                            "→": [
                                                                {"⧖": ["I1", "I2"]},
                                                                {
                                                                    "→": [
                                                                        {"⊕": ["J1", "J2"]},
                                                                        {
                                                                            "→": [
                                                                                {"→": ["K1", "K2"]},
                                                                                {
                                                                                    "→": [
                                                                                        {"⟲": ["L1", "L2"]},
                                                                                        {
                                                                                            "→": [
                                                                                                {"⊕": ["M1", "M2"]},
                                                                                                {
                                                                                                    "→": [
                                                                                                        {"⧖": ["N1", "N2"]},
                                                                                                        {
                                                                                                            "→": [
                                                                                                                {"↔": ["O1", "O2"]},
                                                                                                                {
                                                                                                                    "→": [
                                                                                                                        {"→": ["P1", "P2"]},
                                                                                                                        {
                                                                                                                            "→": [
                                                                                                                                {"⟲": ["Q1", "Q2"]},
                                                                                                                                {
                                                                                                                                    "→": [
                                                                                                                                        {"⊕": ["R1", "R2"]},
                                                                                                                                        {
                                                                                                                                            "→": [
                                                                                                                                                {"⧖": ["S1", "S2"]},
                                                                                                                                                {
                                                                                                                                                    "→": [
                                                                                                                                                        {"↔": ["T1", "T2"]},
                                                                                                                                                        {
                                                                                                                                                            "→": [
                                                                                                                                                                {"→": ["U1", "U2"]},
                                                                                                                                                                {
                                                                                                                                                                    "→": [
                                                                                                                                                                        {"⟲": ["V1", "V2"]},
                                                                                                                                                                        {
                                                                                                                                                                            "→": [
                                                                                                                                                                                {"⊕": ["W1", "W2"]},
                                                                                                                                                                                {
                                                                                                                                                                                    "→": [
                                                                                                                                                                                        {"⧖": ["X1", "X2"]},
                                                                                                                                                                                        {
                                                                                                                                                                                            "→": [
                                                                                                                                                                                                {"↔": ["Y1", "Y2"]},
                                                                                                                                                                                                {
                                                                                                                                                                                                    "→": [
                                                                                                                                                                                                        {"→": ["Z1", "Z2"]},
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

def run_sycamore_batch_kernel_test():
    print("⚡ Running Sycamore Benchmark with Vectorized Collapse Kernel")

    # 1. Bind to container
    container_id = ensure_container("maxwell_core")
    context = {
        "container_id": container_id,
        "source": "benchmark",
        "enable_sycamore_kernel": True  # ✅ Activate the new kernel
    }

    # 2. Inject tree into execution path
    wave_beams = compressed_qglyph_tree

    # 3. Execute benchmark (⚠️ FIXED: added 'instruction_tree' arg)
    start = time.perf_counter()
    result = CodexExecutor().execute_instruction_tree(
        instruction_tree=wave_beams,
        context=context,
        wave_beams=wave_beams  # Optional: kept for compatibility with vector kernel
    )
    duration = time.perf_counter() - start

    # 4. Score symbolic structure
    symbolic_score = score_glyph_tree(wave_beams)
    entropy = len(json.dumps(wave_beams))

    print(f"\n🧪 Vector Interference Kernel Executed")
    print(f"⏱️ Execution Time: {duration*1000:.2f} ms")
    print(f"📏 Symbolic Depth Score: {symbolic_score}")
    print(f"🌀 Entropy Estimate: {entropy} chars")
    print(f"🔁 Compression Ratio: {round(entropy / symbolic_score, 2)}x\n")
    print("✅ Result:", result)

async def async_run():
    run_sycamore_batch_kernel_test()
    await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(async_run())