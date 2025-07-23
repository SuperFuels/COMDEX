# 📁 backend/modules/codex/tests/google_benchmark_runner.py

import time
import json
import os
import asyncio

from backend.modules.glyphos.codexlang_translator import run_codexlang_string
from backend.modules.codex.codex_metrics import score_glyph_tree
from backend.modules.codex.codex_executor import execute_codex_instruction_tree
from backend.modules.glyphos.glyph_quantum_core import generate_qglyph_from_string

def load_codex_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def run_google_sycamore_simulation():
    codex_path = os.path.join(os.path.dirname(__file__), "google_benchmark_test.codex")
    codex_string = load_codex_file(codex_path)

    print("🚀 Running Google Sycamore Benchmark Simulation (Symbolic QGlyph Runtime)...")
    print(f"📄 File: {codex_path}")
    print()

    # Classical parse
    start_classical = time.perf_counter()
    instruction_tree = run_codexlang_string(codex_string)
    end_classical = time.perf_counter()
    classical_time = end_classical - start_classical

    # QGlyph compression
    start_qglyph = time.perf_counter()
    qglyph = generate_qglyph_from_string(codex_string)
    qglyph_time = time.perf_counter() - start_qglyph

    # Simulate execution
    result = execute_codex_instruction_tree(instruction_tree)

    # Score symbolic complexity
    symbolic_score = score_glyph_tree(instruction_tree)
    entropy = len(json.dumps(instruction_tree))  # simple entropy estimate

    print("🧠 CodexLang Instruction Tree Executed")
    print(f"⏱️ Classical Parse Time: {classical_time:.4f}s")
    print(f"🧬 QGlyph Generation Time: {qglyph_time:.4f}s")
    print(f"📏 Symbolic Depth Score: {symbolic_score}")
    print(f"🌀 Entropy Estimate: {entropy} chars")
    print(f"🧿 QGlyph ID: {qglyph.get('id')}")
    print(f"🔁 Compression Ratio: {round(entropy / symbolic_score, 2)}x (approx.)")
    print()
    print("✅ Result:", result)

async def async_run():
    run_google_sycamore_simulation()
    await asyncio.sleep(0.1)  # Give time for background tasks like send_codex_ws_event

if __name__ == "__main__":
    asyncio.run(async_run())