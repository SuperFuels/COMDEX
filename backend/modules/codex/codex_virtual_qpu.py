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
        Execute a single token as a QPU instruction, with metrics and optional low-precision.
        """
        context = context or {}
        cell: Optional[GlyphCell] = context.get("cell")
        start_time = perf_counter()

        try:
            result = execute_qpu_opcode(token["value"], [token], cell, context)

            # Apply symbolic FP4/FP8/INT8 transformation to numeric results
            if isinstance(result, float):
                result_fp4 = self.to_fp4(result)
                result_fp8 = self.to_fp8(result)
                result_int8 = self.to_int8(result)
                context["last_precision"] = {"fp4": result_fp4, "fp8": result_fp8, "int8": result_int8}

            # Increment per-token metric
            self.metrics["mutation_count"] += 1

        except Exception as e:
            result = f"[QPU ERROR {token.get('value', '?')}: {str(e)}]"

        finally:
            elapsed = perf_counter() - start_time
            self.metrics["execution_time"] += elapsed
            # Track per-token timings for profiling (G3)
            self.token_metrics.setdefault(token.get("value", "?"), []).append(elapsed)
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

            prev_sqi = cell.sqi_score or 0.0
            cell.sqi_score = score_sqi(cell)
            self.metrics["sqi_shift"] += cell.sqi_score - prev_sqi
            cell.prediction_forks = cell.prediction_forks or []

            self.hook_to_sqs_engine(cell, context)
            if "container_id" in context:
                self.broadcast_to_qfc(cell, context["container_id"])

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
        context = context or {}
        context["sheet_cells"] = cells
        sheet_results: Dict[str, List[Any]] = {}
        start_time = perf_counter()

        for cell in cells:
            sheet_results[cell.id] = self.execute_cell(cell, context)

        # Aggregate metrics for sheet
        record_trace("sheet", f"[QPU Sheet Metrics] {self.dump_metrics()}")

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
    result = qpu.execute_cell(test_cell, context={"container_id": "default_container"})
    print("Execution Result:", result)
    print("Prediction Forks:", test_cell.prediction_forks)
    print("SQI Score:", test_cell.sqi_score)
    print("QPU Metrics:", qpu.dump_metrics())

    # Optional: Execute a small sheet
    sheet = [
        GlyphCell(id=f"cell_{i}", logic="⊕ ↔ ⟲ → ✦", position=[i, 0])
        for i in range(3)
    ]
    sheet_results = qpu.execute_sheet(sheet, context={"container_id": "default_container"})
    print("Sheet Results:", sheet_results)
    print("Sheet Metrics:", qpu.dump_metrics())