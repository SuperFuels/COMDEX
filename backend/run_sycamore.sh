#!/bin/bash

echo "🧪 Launching Symbolic Sycamore Benchmark (CodexLang 53-symbol QGlyph test)..."

python3 backend/modules/codex/tests/google_benchmark_runner.py > codex_sycamore_output.log

echo ""
echo "✅ Benchmark complete. Results saved to: codex_sycamore_output.log"
echo ""
echo "📂 Preview (tail):"
tail -n 30 codex_sycamore_output.log