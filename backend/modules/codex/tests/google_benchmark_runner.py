# 📁 backend/modules/codex/tests/google_benchmark_runner.py
import time, json, os, asyncio

from backend.modules.glyphos.codexlang_translator import run_codexlang_string
from backend.modules.codex.codex_metrics import score_glyph_tree
from backend.modules.codex.codex_executor import execute_codex_instruction_tree
from backend.modules.glyphos.glyph_quantum_core import generate_qglyph_from_string

# 👇 NEW: bind to a real container so KG/SQI hooks know where to write
from backend.modules.consciousness.state_manager import STATE, load_container_from_file, get_dc_path

def load_codex_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def ensure_container(container_id="maxwell_core"):
    # Try to load the .dc from UCS path; fall back to allocate+materialize if needed
    dc_path = os.path.join(os.path.dirname(__file__), "../../dimensions/containers", f"{container_id}.dc.json")
    if os.path.exists(dc_path):
        load_container_from_file(dc_path)  # sets STATE.current_container
        return container_id
    # As a fallback, just set a minimal placeholder container in STATE so KG writes have a target
    STATE.set_current_container({"id": container_id, "meta": {"ghx": {"hover": True, "collapsed": True}}})
    return container_id

def run_google_sycamore_simulation():
    # 1) Ensure we have an active container for KG/SQI
    container_id = ensure_container("maxwell_core")
    context = {"container_id": container_id, "source": "benchmark"}

    # 2) Load test codex script
    codex_path = os.path.join(os.path.dirname(__file__), "google_benchmark_test.codex")
    codex_string = load_codex_file(codex_path)

    print("🚀 Running Google Sycamore Benchmark Simulation (Symbolic QGlyph Runtime)...")
    print(f"📄 File: {codex_path}\n")

    # Classical parse
    start_classical = time.perf_counter()
    instruction_tree = run_codexlang_string(codex_string)
    classical_time = time.perf_counter() - start_classical

    # QGlyph compression
    start_qglyph = time.perf_counter()
    qglyph = generate_qglyph_from_string(codex_string)
    qglyph_time = time.perf_counter() - start_qglyph

    # Execute (now with context → KG/SQI wiring active)
    result = execute_codex_instruction_tree(instruction_tree, context=context)

    # Score symbolic complexity
    symbolic_score = score_glyph_tree(instruction_tree)
    entropy = len(json.dumps(instruction_tree))

    print("🧠 CodexLang Instruction Tree Executed")
    print(f"⏱️ Classical Parse Time: {classical_time:.4f}s")
    print(f"🧬 QGlyph Generation Time: {qglyph_time:.4f}s")
    print(f"📏 Symbolic Depth Score: {symbolic_score}")
    print(f"🌀 Entropy Estimate: {entropy} chars")
    print(f"🧿 QGlyph ID: {qglyph.get('id')}")
    print(f"🔁 Compression Ratio: {round(entropy / symbolic_score, 2)}x (approx.)\n")
    print("✅ Result:", result)

async def async_run():
    run_google_sycamore_simulation()
    await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(async_run())