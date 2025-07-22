# codex_core_fpga.py

from .instruction_parser import parse_codexlang
from .execution_unit import execute_instruction_tree
from .virtual_clock import VirtualClock
from .feedback_monitor import FeedbackMonitor

class CodexCoreFPGA:
    def __init__(self):
        self.clock = VirtualClock()
        self.feedback = FeedbackMonitor()

    def run_codex_program(self, codex_str: str, context: dict = {}):
        tree = parse_codexlang(codex_str)
        results = execute_instruction_tree(tree, context)
        self.feedback.log_execution(codex_str, results, context)
        self.clock.tick()
        return results

# 🔁 Simple test runner
if __name__ == "__main__":
    program = "⟦ Logic | Reflect: Self → ⟲(Dream) ⟧"
    codex = CodexCoreFPGA()
    output = codex.run_codex_program(program)
    print("Execution Output:", output)