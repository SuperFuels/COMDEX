# ===============================
# 📁 codex_virtual_cpu.py
# ===============================
"""
Codex Virtual CPU Entrypoint

Combines parser, executor, symbolic ops, and registers into a
single callable interface. Allows CodexLang string execution.
"""

from typing import Any, Dict, List

from backend.modules.codex.virtual.instruction_parser import InstructionParser
from backend.modules.codex.virtual.instruction_executor import InstructionExecutor
from backend.modules.codex.virtual.virtual_registers import VirtualRegisters


class CodexVirtualCPU:
    def __init__(self):
        self.parser = InstructionParser()
        self.executor = InstructionExecutor()
        self.registers = self.executor.registers  # Shared reference

    def run(self, codexlang_code: str, context: Dict[str, Any] = {}) -> List[Any]:
        """
        Parse and execute CodexLang code string.
        Returns list of execution results.
        """
        tree = self.parser.parse_codexlang_string(codexlang_code)
        results = self.executor.execute_tree(tree, context)
        self.registers.store("last_result", results[-1] if results else None)
        return results

    def get_registers(self) -> Dict[str, Any]:
        return self.registers.dump()


# ✅ Example CLI test runner
if __name__ == "__main__":
    cpu = CodexVirtualCPU()
    code = "⚛ → ✦ ⟲ 🧠"
    output = cpu.run(code)
    print("💡 CodexLang Output:")
    for line in output:
        print("  ", line)
    print("📦 Registers:", cpu.get_registers())