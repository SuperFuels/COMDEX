import time
import json
from pathlib import Path
from typing import List, Dict

from backend.modules.codex.codex_executor import execute_codex_instruction_tree
from backend.modules.glyphos.glyph_logic import interpret_glyph
from backend.modules.sqi.qglyph_generator import QGlyphGenerator
from backend.modules.codex.codex_metrics import log_benchmark_result
from backend.modules.consciousness.state_manager import load_container_from_file

# Paths
LEAN_CONTAINER_DIR = Path("backend/modules/dimensions/containers/lean")
BENCHMARK_OUTPUT_FILE = Path("benchmarks/lean_benchmark_results.json")

# Instantiate the QGlyph generator
generator = QGlyphGenerator()


def benchmark_execution(glyph_str: str, context: dict = None) -> dict:
    """
    Benchmarks execution time, depth, and compression of a glyph logic string
    using both classical and QGlyph (symbolic quantum) execution.
    """
    # Parse classical tree
    parsed_tree = interpret_glyph(glyph_str, context or {})

    start_classical = time.perf_counter()
    classical_result = execute_codex_instruction_tree(parsed_tree, context=context)
    end_classical = time.perf_counter()
    classical_time = end_classical - start_classical

    # QGlyph version
    qglyph = generator.generate_superposed_glyph(glyph_str)
    logic_tree = {
        "type": "qglyph",
        "depth": 1,
        "tree": qglyph["superposed"]
    }

    start_qglyph = time.perf_counter()
    qglyph_result = execute_codex_instruction_tree(logic_tree, context=context)
    end_qglyph = time.perf_counter()
    qglyph_time = end_qglyph - start_qglyph

    classical_depth = parsed_tree.get("depth", 1)
    qglyph_depth = logic_tree.get("depth", 1)

    compression_ratio = classical_depth / qglyph_depth if qglyph_depth else 1.0
    speedup = classical_time / qglyph_time if qglyph_time else 1.0

    result = {
        "glyph": glyph_str,
        "classical_time": round(classical_time, 6),
        "qglyph_time": round(qglyph_time, 6),
        "depth_classical": classical_depth,
        "depth_qglyph": qglyph_depth,
        "compression_ratio": round(compression_ratio, 3),
        "speedup_ratio": round(speedup, 3),
        "qglyph_id": qglyph["id"],
        "ethics_risk": classical_result.get("ethics_risk"),
        "mutation_score": classical_result.get("mutation_score"),
    }

    log_benchmark_result(result)
    return result


def run_batch_benchmarks(glyph_list: List[str]) -> List[Dict]:
    return [benchmark_execution(g) for g in glyph_list]


def benchmark_lean_containers() -> List[Dict]:
    """
    Scans `containers/lean/` for `.dc.json` files and benchmarks their glyph logic.
    """
    results = []
    if not LEAN_CONTAINER_DIR.exists():
        print(f"⚠️ Lean container directory not found: {LEAN_CONTAINER_DIR}")
        return []

    for file in LEAN_CONTAINER_DIR.glob("*.dc.json"):
        try:
            container = load_container_from_file(file)
            if not isinstance(container, dict):
                print(f"⚠️ Skipping {file.name} - not a valid container dict (got {type(container)})")
                continue
            for coord, cube in container.get("glyphs", {}).items():
                glyph = cube.get("value")
                if glyph:
                    print(f"🧪 Benchmarking glyph from {file.name} at {coord} -> {glyph}")
                    res = benchmark_execution(glyph, context={"coord": coord, "container": file.name})
                    res["container"] = file.name
                    res["coord"] = coord
                    results.append(res)
        except Exception as e:
            print(f"❌ Failed to benchmark {file.name}: {e}")

    # Save results
    try:
        BENCHMARK_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BENCHMARK_OUTPUT_FILE, "w") as f:
            json.dump(results, f, indent=2)
        print(f"✅ Results saved to {BENCHMARK_OUTPUT_FILE}")
    except Exception as e:
        print(f"⚠️ Failed to save benchmark results: {e}")

    return results


if __name__ == "__main__":
    print("🔬 Running benchmark on sample symbolic glyphs...")
    sample_glyphs = ["A ⊕ B", "A -> B", "[A:0 ↔ 1] -> D", "(A ⟲ B) ⧖ C"]
    sample_results = run_batch_benchmarks(sample_glyphs)
    print(json.dumps(sample_results, indent=2))

    print("\n📘 Running Lean container benchmarks...")
    lean_results = benchmark_lean_containers()
    print(json.dumps(lean_results, indent=2))