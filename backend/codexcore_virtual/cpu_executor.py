# -*- coding: utf-8 -*-
# File: backend/codexcore_virtual/cpu_executor.py
"""
Virtual CPU Executor

Phase 8 (C9/I1):
- Registry delegation: all instructions routed through
  the global instruction_registry.
- Uses CPUProgramLoader to parse program lines.
- Minimal registers + memory implemented inline (no external stubs).
"""

from backend.codexcore_virtual.instruction_registry import registry
from backend.codexcore_virtual.cpu_program_loader import CPUProgramLoader


class VirtualCPU:
    def __init__(self):
        # Simple memory/register models
        self.registers = {}
        self.memory = {}
        self.instruction_pointer = 0
        self.program = []
        self.running = False
        self.loader = CPUProgramLoader()

    # ──────────────────────────────
    # Program Management
    # ──────────────────────────────
    def load_program(self, program_lines):
        """Load program from raw lines into parsed structure."""
        self.program = self.loader.load_program_from_lines(program_lines)
        self.instruction_pointer = 0

    def fetch(self):
        """Fetch the current instruction or None if past end."""
        if self.instruction_pointer >= len(self.program):
            return None
        return self.program[self.instruction_pointer]

    def decode(self, instr):
        """
        Normalize instruction into (op, args).
        Supports:
          • dict: {"operation": "MOV", "args": ["R1", "42"]}
          • tuple: ("MOV", ["R1", "42"])
        """
        if isinstance(instr, dict):
            return instr["operation"], instr.get("args", [])
        elif isinstance(instr, (tuple, list)) and len(instr) == 2:
            return instr[0], instr[1]
        else:
            raise ValueError(f"Invalid instruction format: {instr}")

    # ──────────────────────────────
    # Execution
    # ──────────────────────────────
    def execute(self, op, args):
        """Route execution through instruction_registry."""
        try:
            return registry.execute_v2(op, *args, ctx=self)
        except KeyError:
            raise ValueError(f"Unknown instruction: {op}")

    def tick(self):
        """Execute a single instruction and advance pointer."""
        instr = self.fetch()
        if instr is None:
            self.running = False
            print("🛑 End of Program")
            return

        op, args = self.decode(instr)
        print(f"🔹 Executing: {op} {args}")
        self.execute(op, args)
        self.instruction_pointer += 1

    def run(self):
        """Run until program halts or end of program."""
        self.running = True
        while self.running:
            self.tick()


# ──────────────────────────────
# Legacy Shim for Compatibility
# ──────────────────────────────
INSTRUCTION_SET = {
    op: (lambda cpu, *args, _op=op: registry.execute_v2(_op, *args, ctx=cpu))
    for op in registry.list_instructions().keys()
}


# ──────────────────────────────
# Inline Demo
# ──────────────────────────────
if __name__ == "__main__":
    program = [
        "MOV R1, 10",
        "MOV R2, 20",
        "ADD R3, R1, R2",
        "STORE R3, 100",
        "PRINT R3",
        "HALT"
    ]

    cpu = VirtualCPU()
    cpu.load_program(program)
    cpu.run()