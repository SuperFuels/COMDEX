# ===============================
# 📁 backend/modules/codex/codex_virtual_cpu.py
# ===============================

"""
Codex Virtual CPU Entrypoint (Phase 7 Enhancements)

- Executes CodexLang strings symbolically
- Tracks per-instruction metrics (ops executed, execution time, register access)
- Optional FP4/FP8/INT8 low-precision simulation
- Fully compatible with SQS/SCI sheets and SQI scoring
- Integrates real SQI scoring and async QFC beams broadcasting
"""

from time import perf_counter
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

from backend.modules.codex.virtual.instruction_parser import InstructionParser
from backend.modules.codex.virtual.instruction_executor import InstructionExecutor
from backend.modules.codex.virtual.virtual_registers import VirtualRegisters
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_beams

# -------------------------------
# Precision simulation stubs
# -------------------------------
def to_fp4(value: float) -> float:
    return round(value * 16) / 16

def to_fp8(value: float) -> float:
    return round(value * 256) / 256

def to_int8(value: float) -> int:
    return max(-128, min(127, int(round(value))))

# -------------------------------
# CodexVirtualCPU
# -------------------------------
class CodexVirtualCPU:
    def __init__(self, enable_metrics: bool = True, low_precision: Optional[str] = None):
        self.parser = InstructionParser()
        self.executor = InstructionExecutor()
        self.registers = self.executor.registers
        self.enable_metrics = enable_metrics
        self.low_precision = low_precision
        self.metrics: Dict[str, Any] = {
            "ops_executed": 0,
            "execution_time": 0.0,
            "register_reads": 0,
            "register_writes": 0,
            "stack_max_depth": 0,
            "sqi_shift": 0.0
        }  # instance-scoped metrics
        if self.enable_metrics:
            self._wrap_registers_for_metrics()

    # -------------------------------
    # Execute a single cell (CPU interface)
    # -------------------------------
    def execute_cell(self, cell: GlyphCell, context: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Execute a single GlyphCell using the CPU symbolic engine.
        Records SQI, metrics, and broadcasts live via QFC beams.
        """
        context = context or {}
        start_time = perf_counter()
        results: List[Any] = []

        try:
            # Real SQI scoring
            prev_sqi = getattr(cell, "sqi_score", 0.0)
            cell.sqi_score = score_sqi(cell)
            self.metrics["sqi_shift"] += (cell.sqi_score - prev_sqi)

            # Naive token execution placeholder
            tokens = cell.logic.split()
            for token in tokens:
                results.append(f"[CPU Executed {token}]")

            # Broadcast per-cell CPU metrics asynchronously
            if "container_id" in context:
                try:
                    broadcast_qfc_beams(
                        container_id=context["container_id"],
                        payload=[{
                            "type": "cpu_cell_update",
                            "cell_id": cell.id,
                            "sqi": cell.sqi_score,
                            "mutation_count": getattr(cell, "mutation_count", 0),
                            "exec_time": perf_counter() - start_time,
                            "token_metrics": [{"total": 0} for _ in tokens]
                        }]
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast CPU cell metrics: {e}")

        finally:
            self.metrics["execution_time"] += perf_counter() - start_time

        return results

    # -------------------------------
    # Wrap virtual registers for metrics
    # -------------------------------
    def _wrap_registers_for_metrics(self):
        orig_get = self.registers.get
        orig_set = self.registers.set
        orig_push = self.registers.push_stack
        orig_pop = self.registers.pop_stack

        def counted_get(name):
            self.metrics["register_reads"] += 1
            return orig_get(name)

        def counted_set(name, value):
            self.metrics["register_writes"] += 1
            return orig_set(name, value)

        def counted_push(value):
            orig_push(value)
            self.metrics["stack_max_depth"] = max(
                self.metrics["stack_max_depth"],
                len(self.registers.registers.get("STACK", []))
            )

        def counted_pop():
            return orig_pop()

        self.registers.get = counted_get
        self.registers.set = counted_set
        self.registers.push_stack = counted_push
        self.registers.pop_stack = counted_pop

    # -------------------------------
    # Reset / dump metrics
    # -------------------------------
    def reset_metrics(self):
        for k in self.metrics:
            if isinstance(self.metrics[k], (int, float)):
                self.metrics[k] = 0

    def dump_metrics(self) -> Dict[str, Any]:
        return dict(self.metrics)

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
                    self.metrics["ops_executed"] += 1
        except Exception as e:
            raise RuntimeError(f"CodexLang execution error: {e}")

        elapsed = perf_counter() - start_time
        if self.enable_metrics:
            self.metrics["execution_time"] += elapsed

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