# 📁 backend/codexcore_virtual/cpu_runtime.py

from typing import List, Dict, Any
from backend.codexcore_virtual.instruction_parser import parse_codex_instructions
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.glyphos.glyph_logic import interpret_glyph
from backend.modules.hexcore.memory_engine import MEMORY


class VirtualCPU:
    def __init__(self):
        self.registers: Dict[str, Any] = {}
        self.stack: List[Any] = []
        self.output: List[str] = []
        self.metrics = CodexMetrics()

    def reset(self):
        self.registers.clear()
        self.stack.clear()
        self.output.clear()

    def execute_instruction(self, instr: Dict[str, Any]) -> Any:
        opcode = instr.get("opcode")
        args = instr.get("args", [])

        try:
            if opcode == "⊕":  # Store
                key, value = args
                self.registers[key] = value

            elif opcode == "→":  # Forward
                source, dest = args
                self.registers[dest] = self.registers.get(source)

            elif opcode == "⟲":  # Reflect / Mutate
                symbol = args[0]
                reflected = interpret_glyph(symbol)
                self.stack.append(reflected)

            elif opcode == "↔":  # Entangle
                a, b = args
                self.registers[a] = self.registers[b] = (self.registers.get(a), self.registers.get(b))

            elif opcode == "⧖":  # Delay / Cost
                delay = args[0]
                self.output.append(f"⧖ Delay: {delay}")

            elif opcode == "print":
                val = args[0]
                self.output.append(str(val))

            elif opcode == "mem":
                query = args[0]
                memories = MEMORY.query(filter=query)
                self.output.append(f"Memory: {memories}")

            else:
                self.output.append(f"Unknown opcode: {opcode}")

            self.metrics.record_execution()
        except Exception as e:
            self.output.append(f"Execution error in {opcode}: {e}")
            self.metrics.record_error()

    def execute_instruction_list(self, instructions: List[Dict[str, Any]]) -> List[str]:
        self.reset()
        for instr in instructions:
            self.execute_instruction(instr)
        return self.output


# 🔁 Example runner (remove in prod)
if __name__ == "__main__":
    from backend.codexcore_virtual.instruction_parser import parse_codex_instructions
    test = "Memory:Dream → Plan => ⟲(Think)"
    instrs = parse_codex_instructions(test)
    cpu = VirtualCPU()
    result = cpu.execute_instruction_list(instrs)
    print("--- Output ---")
    print("\n".join(result))