# ===============================
# 📁 instruction_executor.py
# ===============================
"""
Codex Virtual Instruction Executor

Executes parsed CodexLang instruction trees.
Handles symbolic ops, recursive nodes, and register-aware context.

Phase 7 Enhancements:
- Instruction-level metrics
- FP4 / FP8 / INT8 simulation for numeric results
- Metrics aggregation for benchmarking and SCI/QFC visualization
- Structured results for child nodes

Phase 8 (C9/I1):
- Registry delegation: all ops routed through registry_bridge.resolve_and_execute
- Structured error payloads instead of bare strings.
"""

from typing import Any, Dict, List, Optional
from time import perf_counter
import numpy as np

from backend.core.registry_bridge import registry_bridge
from backend.modules.codex.virtual.virtual_registers import VirtualRegisters
from backend.modules.patterns.pattern_trace_engine import record_trace


class InstructionExecutor:
    def __init__(self):
        self.registers = VirtualRegisters()
        self.metrics: Dict[str, float] = {
            "execution_time": 0.0,
            "mutation_count": 0,
            "ops_executed": 0,
            "max_node_depth": 0
        }

    # -------------------
    # Execute a single instruction node
    # -------------------
    def execute_node(
        self,
        node: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        depth: int = 0
    ) -> Dict[str, Any]:
        """
        Execute a single instruction node recursively.
        Returns a structured dict: {"result": ..., "children": [...]}.
        """
        if context is None:
            context = {}

        op: str = node.get("op", "")
        args: List[Any] = node.get("args", [])
        kwargs: Dict[str, Any] = node.get("kwargs", {})
        children: List[Dict[str, Any]] = node.get("children", [])

        self.metrics["max_node_depth"] = max(self.metrics["max_node_depth"], depth)

        try:
            # ✅ Always go through RegistryBridge
            result = registry_bridge.resolve_and_execute(
                op, *args, ctx=self.registers, context=context, **kwargs
            )
        except Exception as e:
            result = {"status": "error", "error": f"ExecutionError @ {op}: {str(e)}"}

        # Recursively evaluate children
        child_results = []
        for child in children:
            child_result = self.execute_node(child, context, depth=depth+1)
            child_results.append(child_result)

        return {"result": result, "children": child_results} if child_results else {"result": result}

    # -------------------
    # Execute single instruction with metrics
    # -------------------
    def execute_instruction_with_metrics(
        self,
        instr: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a single instruction, profile time, mutations, node depth, and precision.
        """
        if context is None:
            context = {}

        start_time = perf_counter()
        result: Dict[str, Any]

        try:
            result = self.execute_node(instr, context)

            # ✅ Precision simulation if numeric
            numeric_result = result.get("result")
            if isinstance(numeric_result, (int, float)):
                context["precision"] = {
                    "fp4": self.to_fp4(numeric_result),
                    "fp8": self.to_fp8(numeric_result),
                    "int8": self.to_int8(numeric_result)
                }

            self.metrics["mutation_count"] += 1
            self.metrics["ops_executed"] += 1

        except Exception as e:
            result = {
                "result": {"status": "error", "error": f"InstructionError @ {instr.get('op', '?')}: {str(e)}"},
                "children": []
            }

        finally:
            elapsed = perf_counter() - start_time
            self.metrics["execution_time"] += elapsed
            record_trace(instr.get("op", "?"), f"[CPU Instruction Metrics] exec_time={elapsed:.6f}s")

        return result

    # -------------------
    # Execute full instruction tree
    # -------------------
    def execute_tree(
        self,
        tree: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a full CodexLang instruction tree.
        Returns a list of structured results.
        """
        if context is None:
            context = {}

        results: List[Dict[str, Any]] = []
        for node in tree:
            try:
                results.append(self.execute_instruction_with_metrics(node, context))
            except Exception as e:
                results.append({
                    "result": {"status": "error", "error": f"TreeExecutionError: {str(e)}"},
                    "children": []
                })
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