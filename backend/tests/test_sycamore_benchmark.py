# File: backend/tests/test_sycamore_benchmark.py

import time, json, os
import pytest

from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.codex.codex_metrics import score_glyph_tree
from backend.modules.consciousness.state_manager import STATE, load_container_from_file

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

def ensure_container(container_id="maxwell_core"):
    path = os.path.join(os.path.dirname(__file__), "../../dimensions/containers", f"{container_id}.dc.json")
    if os.path.exists(path):
        load_container_from_file(path)
    else:
        STATE.set_current_container({"id": container_id})
    return container_id

def test_sycamore_benchmark():
    container_id = ensure_container("maxwell_core")
    context = {
        "container_id": container_id,
        "source": "benchmark",
        "enable_sycamore_kernel": True,
    }

    start = time.perf_counter()
    result = CodexExecutor().execute_instruction_tree(
        instruction_tree=compressed_qglyph_tree,
        context=context,
        wave_beams=compressed_qglyph_tree
    )
    duration = time.perf_counter() - start

    symbolic_score = score_glyph_tree(compressed_qglyph_tree)
    entropy = len(json.dumps(compressed_qglyph_tree))
    compression_ratio = round(entropy / symbolic_score, 2) if symbolic_score else 0

    print("\n🧪 Sycamore Benchmark Complete")
    print(f"⏱ Execution Time: {duration*1000:.2f} ms")
    print(f"📏 Symbolic Score: {symbolic_score}")
    print(f"🌀 Entropy Estimate: {entropy}")
    print(f"🔁 Compression Ratio: {compression_ratio}x")
    print("✅ Collapse Result:", result)

    # Assertions (basic validation)
    assert isinstance(result, dict)
    assert symbolic_score > 0