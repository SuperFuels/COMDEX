# ===============================
# 📁 backend/modules/codex/codex_virtual_cpu.py
# ===============================
"""
Codex Virtual CPU Entrypoint (Phase 7 Enhancements)

- Executes CodexLang strings symbolically
- Tracks per-instruction metrics (ops executed, execution time, register access)
- Optional FP4/FP8/INT8 low-precision simulation
- Fully compatible with SQS/SCI sheets and SQI scoring
"""

from time import perf_counter
from typing import Any, Dict, List, Optional
from time import perf_counter
import logging

logger = logging.getLogger(__name__)

from backend.modules.codex.virtual.instruction_parser import InstructionParser
from backend.modules.codex.virtual.instruction_executor import InstructionExecutor
from backend.modules.codex.virtual.virtual_registers import VirtualRegisters
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update

# -------------------------------
# Precision simulation stubs
# -------------------------------
def to_fp4(value: float) -> float:
    """Simulate FP4 precision (4-bit float)."""
    return round(value * 16) / 16

def to_fp8(value: float) -> float:
    """Simulate FP8 precision (8-bit float)."""
    return round(value * 256) / 256

def to_int8(value: float) -> int:
    """Simulate INT8 (8-bit integer)."""
    return max(-128, min(127, int(round(value))))

# -------------------------------
# CPU Metrics
# -------------------------------
CPU_METRICS: Dict[str, Any] = {
    "ops_executed": 0,
    "execution_time": 0.0,
    "register_reads": 0,
    "register_writes": 0,
    "stack_max_depth": 0
}

# -------------------------------
# CodexVirtualCPU
# -------------------------------
class CodexVirtualCPU:
    def __init__(self, enable_metrics: bool = True, low_precision: Optional[str] = None):
        """
        Args:
            enable_metrics: Track CPU instruction metrics if True
            low_precision: Optional precision mode: "FP4", "FP8", "INT8"
        """
        self.parser = InstructionParser()
        self.executor = InstructionExecutor()
        self.registers = self.executor.registers  # shared reference
        self.enable_metrics = enable_metrics
        self.low_precision = low_precision  # FP4 / FP8 / INT8

        # Wrap VirtualRegisters to count reads/writes for metrics
        if self.enable_metrics:
            self._wrap_registers_for_metrics()

    # -------------------------------
    # Metrics helpers
    # -------------------------------
    def _wrap_registers_for_metrics(self):
        orig_get = self.registers.get
        orig_set = self.registers.set
        orig_push = self.registers.push_stack
        orig_pop = self.registers.pop_stack

        def counted_get(name):
            CPU_METRICS["register_reads"] += 1
            return orig_get(name)

        def counted_set(name, value):
            CPU_METRICS["register_writes"] += 1
            return orig_set(name, value)

        def counted_push(value):
            orig_push(value)
            CPU_METRICS["stack_max_depth"] = max(CPU_METRICS["stack_max_depth"], len(self.registers.registers["STACK"]))

        def counted_pop():
            val = orig_pop()
            return val

        self.registers.get = counted_get
        self.registers.set = counted_set
        self.registers.push_stack = counted_push
        self.registers.pop_stack = counted_pop

    def reset_metrics(self):
        for k in CPU_METRICS:
            if isinstance(CPU_METRICS[k], (int, float)):
                CPU_METRICS[k] = 0

    def dump_metrics(self) -> Dict[str, Any]:
        return dict(CPU_METRICS)

    # -------------------------------
    # Symbolic value precision helper
    # -------------------------------
    def _apply_precision(self, value: Any) -> Any:
        if not self.low_precision or not isinstance(value, (int, float)):
            return value
        if self.low_precision == "FP4":
            return to_fp4(value)
        elif self.low_precision == "FP8":
            return to_fp8(value)
        elif self.low_precision == "INT8":
            return to_int8(value)
        return value

    # -------------------------------
    # Core run method
    # -------------------------------
    def run(self, codexlang_code: str, context: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Parse and execute a CodexLang string.
        Returns execution results as a list.
        """
        context = dict(context or {})
        results: List[Any] = []

        try:
            tree = self.parser.parse_codexlang_string(codexlang_code)
        except Exception as e:
            raise ValueError(f"CodexLang parse error: {e}")

        start_time = perf_counter()
        try:
            for node in tree:
                node_result = self.executor.execute_node(node, context)
                node_result = self._apply_precision(node_result)
                results.append(node_result)
                if self.enable_metrics:
                    CPU_METRICS["ops_executed"] += 1
        except Exception as e:
            raise RuntimeError(f"CodexLang execution error: {e}")

        elapsed = perf_counter() - start_time
        if self.enable_metrics:
            CPU_METRICS["execution_time"] += elapsed

        last_result = results[-1] if results else None
        self.registers.store("last_result", last_result)
        return results

    # -------------------------------
    # Direct register access
    # -------------------------------
    def get_registers(self) -> Dict[str, Any]:
        return self.registers.dump()


# -------------------------------
# CLI / Standalone test
# -------------------------------
if __name__ == "__main__":
    cpu = CodexVirtualCPU(enable_metrics=True, low_precision="FP4")
    code = "⚛ → ✦ ⟲ 🧠"
    try:
        output = cpu.run(code)
        print("💡 CodexLang Output:", output)
        print("📦 Registers:", cpu.get_registers())
        print("📊 CPU Metrics:", cpu.dump_metrics())
    except Exception as e:
        print(f"❌ Error during execution: {e}")