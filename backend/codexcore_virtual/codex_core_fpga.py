"""
CodexCoreFPGA
=============
A lightweight FPGA-style wrapper around the Codex executor pipeline.

- Parses CodexLang → AST
- Executes instruction tree via CodexExecutor
- Logs execution feedback
- Advances a symbolic virtual clock (via QWave beam tick loop)
"""

from typing import Dict, Any, List

# ✅ Canonical parser
from backend.modules.codex.virtual.instruction_parser import parse_codexlang

# ✅ Codex runtime
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.codex.codex_feedback_loop import CodexFeedbackLoop
from backend.modules.codex.codex_metrics import CodexMetrics

# ✅ Beam + clock
from backend.modules.runtime.beam_tick_loop import beam_tick_loop


class CodexCoreFPGA:
    def __init__(self):
        # Core components
        self.executor = CodexExecutor()
        self.feedback = CodexFeedbackLoop()
        self.metrics = CodexMetrics()

        # Track ticks
        self.tick_count = 0

    def run_codex_program(self, codex_str: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Parse and execute a CodexLang string.
        - Parse CodexLang → AST
        - Execute AST via CodexExecutor
        - Record metrics + feedback
        - Advance symbolic clock (beam_tick_loop)
        """
        context = context or {}

        # 1. Parse CodexLang → AST
        ast = parse_codexlang(codex_str)
        if not ast:
            raise ValueError("CodexLang parse failed: empty AST")

        # ✅ Normalize AST
        if isinstance(ast, list):
            if len(ast) == 1:
                tree = ast[0]  # unwrap single node
            else:
                # wrap multiple nodes into synthetic root
                tree = {"op": "program", "children": ast}
        elif isinstance(ast, dict):
            tree = ast
        else:
            raise ValueError(f"CodexLang parse failed: unexpected AST type {type(ast)}")

        # 2. Execute AST
        result = self.executor.execute_instruction_tree(tree, context=context)

        # 3. Log metrics + feedback
        self.metrics.record_execution()
        self.feedback.reinforce_or_mutate()

        # 4. Advance symbolic clock
        beam_tick_loop(max_ticks=1)
        self.tick_count += 1

        return result


# 🔁 Simple test runner
if __name__ == "__main__":
    program = "⟦ Logic | Reflect: Self → ⟲(Dream) ⟧"
    codex = CodexCoreFPGA()
    output = codex.run_codex_program(program)
    print("Execution Output:", output)