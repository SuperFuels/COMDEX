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
        context = dict(context)  # Avoid modifying original
        try:
            tree = self.parser.parse_codexlang_string(codexlang_code)
        except Exception as e:
            raise ValueError(f"CodexLang parse error: {e}")

        try:
            results = self.executor.execute_tree(tree, context)
        except Exception as e:
            raise RuntimeError(f"CodexLang execution error: {e}")

        last_result = results[-1] if results else None
        self.registers.store("last_result", last_result)
        return results

    def get_registers(self) -> Dict[str, Any]:
        return self.registers.dump()


# ✅ Example CLI test runner
if __name__ == "__main__":
    cpu = CodexVirtualCPU()
    code = "⚛ → ✦ ⟲ 🧠"
    try:
        output = cpu.run(code)
        print("💡 CodexLang Output:")
        for line in output:
            print("  ", line)
        print("📦 Registers:", cpu.get_registers())
    except Exception as e:
        print(f"❌ Error during execution: {e}")