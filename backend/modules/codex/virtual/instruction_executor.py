# ===============================
# 📁 instruction_executor.py
# ===============================
"""
Codex Virtual Instruction Executor

Executes parsed CodexLang instruction trees.
Handles symbolic ops, recursive nodes, and register-aware context.
"""

from typing import Any, Dict, List, Optional, Union
from backend.modules.codex.virtual.symbolic_instruction_set import SYMBOLIC_OPS
from backend.modules.codex.virtual.virtual_registers import VirtualRegisters


class InstructionExecutor:
    def __init__(self):
        self.registers = VirtualRegisters()

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
            return f"[ExecutionError @ {op}: {str(e)}]"

        child_results = []
        for child in children:
            child_result = self.execute_node(child, context)
            child_results.append(child_result)

        return child_results[-1] if child_results else result

    def execute_tree(
        self,
        tree: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Execute a full CodexLang instruction tree.
        """
        if context is None:
            context = {}

        results: List[Any] = []
        for node in tree:
            try:
                result = self.execute_node(node, context)
                results.append(result)
            except Exception as e:
                results.append(f"[TreeExecutionError: {str(e)}]")

        return results