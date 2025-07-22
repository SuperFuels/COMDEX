# ================================
# 📁 codex_emulator.py
# ================================
"""
Codex Emulator Runtime

Bridges CodexLang scroll input to symbolic virtual execution.
Connects to memory engine, metrics, and Tessaris for feedback.
"""

from typing import Dict, Any
from backend.modules.codex.virtual.codex_virtual_cpu import CodexVirtualCPU
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.tessaris.tessaris_engine import TessarisEngine

# Runtime modules
codex_cpu = CodexVirtualCPU()
metrics = CodexMetrics()
tessaris = TessarisEngine()


def run_codex_scroll(codexlang_string: str, context: Dict[str, Any] = {}) -> Dict[str, Any]:
    """
    Main entrypoint to execute a CodexLang scroll string.
    Returns result, memory entry, and metrics.
    """
    results = codex_cpu.run(codexlang_string, context)
    registers = codex_cpu.get_registers()
    metrics.record_execution()

    MEMORY.store({
        "label": "codex_scroll_execution",
        "type": "codexlang",
        "input": codexlang_string,
        "context": context,
        "results": results,
        "registers": registers
    })

    tessaris.extract_intents_from_glyphs([codexlang_string], context)

    return {
        "status": "ok",
        "results": results,
        "registers": registers
    }


# ✅ CLI test
if __name__ == "__main__":
    scroll = "⊕: Fusion ↔: Memory ⟲: Recall"
    output = run_codex_scroll(scroll)
    print("🔁 Results:", output["results"])
    print("📦 Registers:", output["registers"])