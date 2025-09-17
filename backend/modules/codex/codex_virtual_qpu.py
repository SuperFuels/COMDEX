# ===============================
# 📁 backend/modules/codex/codex_virtual_qpu.py
# ===============================
"""
CodexVirtualQPU: Phase 7 QPU ISA Execution Layer

- Executes GlyphCell logic using symbolic QPU ISA
- Stubs for entanglement, collapse, superposition
- Integration hooks for SQS, SCI, QFC
- Metrics tracking & production-ready logging
- Instruction-level profiling (G3)
- FP4/FP8/INT8 symbolic simulation
"""

from typing import Any, Dict, List, Optional
from time import perf_counter
from backend.modules.codex.hardware.symbolic_qpu_isa import (
    execute_qpu_opcode,
    SYMBOLIC_QPU_OPS
)
from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
from backend.modules.patterns.pattern_trace_engine import record_trace
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update


class CodexVirtualQPU:
    def __init__(self, use_qpu: bool = True):
        self.use_qpu: bool = use_qpu
        self.metrics_enabled: bool = True
        self.reset_metrics()
        self.opcode_metrics: Dict[str, Dict[str, Any]] = {}  # {cell_id: {opcode: {count, fp4_time, fp8_time, int8_time, total_time}}}

    # -------------------
    # Precision Simulation (FP4 / FP8 / INT8)
    # -------------------
    def to_fp4(self, value: float) -> float:
        try:
            import numpy as np
            quantized = np.clip(value, -1.0, 1.0)
            quantized = np.round((quantized + 1.0) * 7.5) / 7.5 - 1.0
            return float(quantized)
        except Exception:
            return value

    def to_fp8(self, value: float) -> float:
        try:
            import numpy as np
            quantized = np.clip(value, -1.0, 1.0)
            quantized = np.round((quantized + 1.0) * 127) / 127 - 1.0
            return float(quantized)
        except Exception:
            return value

    def to_int8(self, value: float) -> int:
        try:
            import numpy as np
            return int(np.clip(np.round(value * 127), -127, 127))
        except Exception:
            return int(value)

    # -------------------
    # Metrics
    # -------------------
    def reset_metrics(self) -> None:
        self.metrics: Dict[str, float] = {
            "execution_time": 0.0,
            "sqi_shift": 0.0,
            "mutation_count": 0
        }
        # Optional: track per-token execution times
        self.token_metrics: Dict[str, List[float]] = {}

    def dump_metrics(self) -> Dict[str, float]:
        return dict(self.metrics)

    # -------------------
    # Stubs for quantum ops
    # -------------------
    def entangle_cells(self, cell_a: GlyphCell, cell_b: GlyphCell) -> bool:
        try:
            record_trace(cell_a.id, f"[QPU Stub] Entangling {cell_a.id} ↔ {cell_b.id}")
            self.metrics["mutation_count"] += 1
            return True
        except Exception as e:
            record_trace(cell_a.id, f"[QPU Error] Entangle failed: {e}")
            return False

    def collapse_cell(self, cell: GlyphCell) -> bool:
        try:
            record_trace(cell.id, f"[QPU Stub] Collapsing {cell.id}")
            self.metrics["mutation_count"] += 1
            return True
        except Exception as e:
            record_trace(cell.id, f"[QPU Error] Collapse failed: {e}")
            return False

    def superpose_cell(self, cell: GlyphCell) -> bool:
        try:
            record_trace(cell.id, f"[QPU Stub] Superposing {cell.id}")
            return True
        except Exception as e:
            record_trace(cell.id, f"[QPU Error] Superpose failed: {e}")
            return False

    # -------------------
    # Instruction-level execution w/ metrics
    # -------------------
    def execute_cell_token(self, token: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """
        Execute a single token as a QPU instruction, with metrics, 
        optional low-precision simulation (FP4/FP8/INT8), per-op profiling (G3),
        and live HUD integration.
        """
        context = context or {}
        cell: Optional[GlyphCell] = context.get("cell")
        start_time = perf_counter()

        try:
            result = execute_qpu_opcode(token["value"], [token], cell, context)

            # -------------------
            # Track FP precision timings
            # -------------------
            if isinstance(result, float):
                # FP4
                fp4_start = perf_counter()
                result_fp4 = self.to_fp4(result)
                fp4_elapsed = perf_counter() - fp4_start

                # FP8
                fp8_start = perf_counter()
                result_fp8 = self.to_fp8(result)
                fp8_elapsed = perf_counter() - fp8_start

                # INT8
                int8_start = perf_counter()
                result_int8 = self.to_int8(result)
                int8_elapsed = perf_counter() - int8_start

                # Store in context for HUD or logging
                context["last_precision"] = {
                    "fp4": result_fp4,
                    "fp8": result_fp8,
                    "int8": result_int8
                }

                # Track per-token per-precision metrics
                self.token_metrics.setdefault(token["value"], []).append({
                    "total": elapsed,
                    "fp4": fp4_elapsed,
                    "fp8": fp8_elapsed,
                    "int8": int8_elapsed
                })

            # -------------------
            # Track per-op metrics for the cell (NEW)
            # -------------------
            if cell and cell.id:
                if cell.id not in self.opcode_metrics:
                    self.opcode_metrics[cell.id] = {}
                op_stats = self.opcode_metrics[cell.id].setdefault(token["value"], {
                    "count": 0,
                    "total_time": 0.0,
                    "fp4_time": 0.0,
                    "fp8_time": 0.0,
                    "int8_time": 0.0
                })
                op_stats["count"] += 1
                op_stats["total_time"] += elapsed
                if isinstance(result, float):
                    op_stats["fp4_time"] += fp4_elapsed
                    op_stats["fp8_time"] += fp8_elapsed
                    op_stats["int8_time"] += int8_elapsed

            # Increment mutation count per token
            self.metrics["mutation_count"] += 1

        except Exception as e:
            result = f"[QPU ERROR {token.get('value', '?')}: {str(e)}]"

        finally:
            elapsed = perf_counter() - start_time
            self.metrics["execution_time"] += elapsed
            # Track per-token total execution time for profiling
            self.token_metrics.setdefault(token.get("value", "?"), []).append({"total": elapsed})
            record_trace(token.get("value", "?"), f"[Token Metrics] exec_time={elapsed:.6f}s")

        return result

        # -------------------
        # Broadcast enhanced per-cell metrics for live HUD (G3)
        # -------------------
        if "container_id" in context and cell.id:
            try:
                broadcast_qfc_update(context["container_id"], {
                    "type": "qpu_cell_update",
                    "cell_id": cell.id,
                    "sqi": cell.sqi_score,
                    "mutation_count": self.metrics["mutation_count"],
                    "exec_time": perf_counter() - start_time,
                    "token_metrics": self.token_metrics.get(cell.logic, []),
                    "opcode_breakdown": self.opcode_metrics.get(cell.id, {})  # NEW
                })
            except Exception as e:
                record_trace(cell.id, f"[QPU Broadcast Error] {e}")

        finally:
            elapsed = perf_counter() - start_time
            self.metrics["execution_time"] += elapsed
            # Track per-token total execution time for profiling
            self.token_metrics.setdefault(token.get("value", "?"), []).append({"total": elapsed})
            record_trace(token.get("value", "?"), f"[Token Metrics] exec_time={elapsed:.6f}s")

        return result

    # -------------------
    # Integration Hooks
    # -------------------
    def hook_to_sqs_engine(self, cell: GlyphCell, context: Dict[str, Any]) -> None:
        context["sqi_update"] = cell.sqi_score
        record_trace(cell.id, f"[QPU Hook] SQI updated: {cell.sqi_score}")

    def broadcast_to_qfc(self, cell: GlyphCell, container_id: str) -> None:
        try:
            broadcast_qfc_update(container_id, {
                "type": "qpu_update",
                "cell_id": cell.id,
                "sqi": cell.sqi_score
            })
            record_trace(cell.id, f"[QPU Hook] Broadcasted to QFC container {container_id}")
        except Exception as e:
            record_trace(cell.id, f"[QPU Error] Broadcast failed: {e}")

    # -------------------
    # Execute single cell
    # -------------------
    def execute_cell(
        self,
        cell: GlyphCell,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Execute a single GlyphCell using the symbolic QPU ISA.
        Captures per-token FP precision timings, mutation counts,
        opcode breakdowns, and broadcasts enhanced metrics to LiveQpuCpuPanel (G3).
        """
        context = context or {}
        context.setdefault("entangled_cells", [])

        if not self.use_qpu:
            record_trace(cell.id, "[QPU Disabled] Skipping execution")
            return []

        start_time = perf_counter()
        results: List[Any] = []

        try:
            tokens = tokenize_symbol_text_to_glyphs(cell.logic)
            for token in tokens:
                try:
                    value = token["value"]
                    if value in SYMBOLIC_QPU_OPS:
                        res = self.execute_cell_token(token, context=context)
                        results.append(res)
                        record_trace(cell.id, f"[QPU Executed] {value}: {res}")
                    else:
                        results.append(f"[Literal {value}]")
                        record_trace(cell.id, f"[QPU Literal] {value}")
                except Exception as e:
                    record_trace(cell.id, f"[QPU Error] Token '{token.get('value', '?')}' failed: {e}")
                    results.append(f"[Error {token.get('value', '?')}]")

            # Update SQI score
            prev_sqi = cell.sqi_score or 0.0
            cell.sqi_score = score_sqi(cell)
            self.metrics["sqi_shift"] += cell.sqi_score - prev_sqi
            cell.prediction_forks = cell.prediction_forks or []

            # Hooks
            self.hook_to_sqs_engine(cell, context)

            # -------------------
            # Broadcast enhanced per-cell metrics for live HUD (G3)
            # -------------------
            if "container_id" in context and cell.id:
                try:
                    broadcast_qfc_update(context["container_id"], {
                        "type": "qpu_cell_update",
                        "cell_id": cell.id,
                        "sqi": cell.sqi_score,
                        "mutation_count": self.metrics["mutation_count"],
                        "exec_time": perf_counter() - start_time,
                        "token_metrics": self.token_metrics.get(cell.logic, []),
                        "opcode_breakdown": self.opcode_metrics.get(cell.id, {})  # NEW
                    })
                except Exception as e:
                    record_trace(cell.id, f"[QPU Broadcast Error] {e}")

        finally:
            elapsed = perf_counter() - start_time
            self.metrics["execution_time"] += elapsed
            record_trace(cell.id, f"[QPU Metrics] exec_time={elapsed:.6f}s")

        return results

# -------------------
# Execute full sheet (bulk)
# -------------------
    def execute_sheet(
        self,
        cells: List[GlyphCell],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Any]]:
        """
        Execute a full sheet of GlyphCells on the symbolic QPU.
        Captures per-token metrics, per-op metrics, and broadcasts
        both per-cell and aggregate sheet metrics (G3).
        """
        context = context or {}
        context["sheet_cells"] = cells
        sheet_results: Dict[str, List[Any]] = {}
        start_time = perf_counter()

        # Execute each cell
        for cell in cells:
            sheet_results[cell.id] = self.execute_cell(cell, context)

        # -------------------
        # Aggregate per-sheet metrics for debugging or reporting (G3)
        # -------------------
        sheet_token_metrics: Dict[str, Any] = {}
        sheet_opcode_metrics: Dict[str, Any] = {}
        for cell in cells:
            sheet_token_metrics[cell.id] = self.token_metrics.get(cell.logic, [])
            sheet_opcode_metrics[cell.id] = self.opcode_metrics.get(cell.id, {})

        record_trace("sheet", f"[QPU Sheet Metrics] {self.dump_metrics()}")
        record_trace("sheet", f"[QPU Sheet Token Metrics] {sheet_token_metrics}")
        record_trace("sheet", f"[QPU Sheet Opcode Metrics] {sheet_opcode_metrics}")

        # Optional: broadcast aggregate sheet metrics
        if context.get("container_id"):
            try:
                broadcast_qfc_update(context["container_id"], {
                    "type": "qpu_sheet_metrics",
                    "sheet_token_metrics": sheet_token_metrics,
                    "sheet_opcode_metrics": sheet_opcode_metrics,  # NEW
                    "aggregate_metrics": self.dump_metrics()
                })
            except Exception as e:
                record_trace("sheet", f"[QPU Sheet Broadcast Error] {e}")

        elapsed = perf_counter() - start_time
        record_trace("sheet", f"[Sheet Execution] elapsed={elapsed:.6f}s")
        return sheet_results

# -------------------
# Standalone CLI Test
# -------------------
if __name__ == "__main__":
    from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

    # Example test GlyphCell
    test_cell = GlyphCell(
        id="cell_001",
        logic="⊕ ↔ ⟲ → ✦",
        position=[0, 0],
        emotion="curious",
        prediction="Initial"
    )

    # Instantiate QPU
    qpu = CodexVirtualQPU()

    # Execute single cell
    print("\n💡 Executing single cell on QPU...")
    result = qpu.execute_cell(test_cell, context={"container_id": "default_container"})
    print("Execution Result:", result)
    print("Prediction Forks:", test_cell.prediction_forks)
    print("SQI Score:", test_cell.sqi_score)
    print("QPU Metrics:", qpu.dump_metrics())

    # Execute a small sheet
    print("\n💡 Executing a small sheet of 3 cells on QPU...")
    sheet = [
        GlyphCell(id=f"cell_{i}", logic="⊕ ↔ ⟲ → ✦", position=[i, 0])
        for i in range(3)
    ]
    sheet_results = qpu.execute_sheet(sheet, context={"container_id": "default_container"})
    print("Sheet Results:", sheet_results)
    print("Sheet Metrics:", qpu.dump_metrics())

    print("\n✅ QPU standalone test complete.")