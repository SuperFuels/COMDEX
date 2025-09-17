# ===============================
# 📁 instruction_executor.py
# ===============================
"""
Codex Virtual Instruction Executor

Executes parsed CodexLang instruction trees.
Handles symbolic ops, recursive nodes, and register-aware context.

Phase 7 Update:
- Instruction-level metrics
- FP4 / FP8 / INT8 simulation for numeric results
- Metrics aggregation for benchmarking and SCI/QFC visualization
"""

from typing import Any, Dict, List, Optional, Union
from time import perf_counter
import numpy as np
from backend.modules.codex.virtual.symbolic_instruction_set import SYMBOLIC_OPS
from backend.modules.codex.virtual.virtual_registers import VirtualRegisters
from backend.modules.patterns.pattern_trace_engine import record_trace


class InstructionExecutor:
    def __init__(self):
        self.registers = VirtualRegisters()
        self.metrics: Dict[str, float] = {
            "execution_time": 0.0,
            "mutation_count": 0
        }

    # -------------------
    # Execute single instruction node
    # -------------------
    def execute_node(
        self,
        node: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a single instruction node.
        """
        if context is None:
            context = {}

        op: str = node.get("op", "")
        args: List[Any] = node.get("args", [])
        children: List[Dict[str, Any]] = node.get("children", [])

        if op not in SYMBOLIC_OPS:
            return f"[UnknownOp: {op}]"

        try:
            func = SYMBOLIC_OPS[op]
            result = func(args, self.registers, context)
        except Exception as e:
            result = f"[ExecutionError @ {op}: {str(e)}]"

        child_results = []
        for child in children:
            child_result = self.execute_node(child, context)
            child_results.append(child_result)

        return child_results[-1] if child_results else result

    # -------------------
    # Execute single instruction with metrics
    # -------------------
    def execute_instruction_with_metrics(
        self,
        instr: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a single instruction, profile time, mutations, and optional low-precision.
        """
        if context is None:
            context = {}

        start_time = perf_counter()
        result = None

        try:
            # Original execution
            result = self.execute_node(instr, context)

            # Apply FP4 / FP8 / INT8 symbolic simulation for numeric results
            if isinstance(result, float):
                context["precision"] = {
                    "fp4": self.to_fp4(result),
                    "fp8": self.to_fp8(result),
                    "int8": self.to_int8(result)
                }

            # Increment per-instruction metric
            self.metrics["mutation_count"] += 1

        except Exception as e:
            result = f"[InstructionError @ {instr.get('op', '?')}: {str(e)}]"

        finally:
            elapsed = perf_counter() - start_time
            self.metrics["execution_time"] += elapsed
            record_trace(instr.get("op", "?"), f"[CPU Instruction Metrics] exec_time={elapsed:.6f}s")

        return result

    # -------------------
    # Execute full tree
    # -------------------
    def execute_tree(
        self,
        tree: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Execute a full CodexLang instruction tree.
        Metrics are recorded per instruction.
        """
        if context is None:
            context = {}

        results: List[Any] = []
        for node in tree:
            try:
                result = self.execute_instruction_with_metrics(node, context)
                results.append(result)
            except Exception as e:
                results.append(f"[TreeExecutionError: {str(e)}]")

        return results

    # -------------------
    # FP4 / FP8 / INT8 symbolic simulation helpers
    # -------------------
    def to_fp4(self, value: float) -> float:
        try:
            quantized = np.clip(value, -1.0, 1.0)
            quantized = np.round((quantized + 1.0) * 7.5) / 7.5 - 1.0
            return float(quantized)
        except Exception:
            return value

    def to_fp8(self, value: float) -> float:
        try:
            quantized = np.clip(value, -1.0, 1.0)
            quantized = np.round((quantized + 1.0) * 127) / 127 - 1.0
            return float(quantized)
        except Exception:
            return value

    def to_int8(self, value: float) -> int:
        try:
            return int(np.clip(np.round(value * 127), -127, 127))
        except Exception:
            return int(value)

    # -------------------
    # Dump metrics
    # -------------------
    def dump_metrics(self) -> Dict[str, float]:
        return dict(self.metrics)