# 📁 backend/modules/codex/sycamore_runner.py
import time
import uuid
import json
from backend.modules.codex.codex_executor import run_codexlang_string
from backend.modules.codex.codex_metrics import score_glyph_tree

# Load symbolic Sycamore test
with open("backend/modules/codex/tests/google_benchmark_test.codex", "r") as f:
    codex_program = f.read()

print("\n🚀 Running Symbolic Sycamore Benchmark...\n")

start_classical = time.time()
# Simulated classical interpretation (linear parse only)
_ = codex_program.count("->") + codex_program.count("⊕") + codex_program.count("⧖") + codex_program.count("↔")
end_classical = time.time()

start_qglyph = time.time()
result = run_codexlang_string(codex_program)
end_qglyph = time.time()

# Score compression and complexity
score = score_glyph_tree(result)

benchmark = {
    "benchmark": "Symbolic Sycamore Test",
    "uuid": str(uuid.uuid4()),
    "classical_time": round(end_classical - start_classical, 6),
    "qglyph_time": round(end_qglyph - start_qglyph, 6),
    "symbolic_score": score,
    "compression_ratio": round(score / 53, 2),
    "result": result,
}

print(json.dumps(benchmark, indent=2))