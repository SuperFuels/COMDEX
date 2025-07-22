# File: backend/codexcore_virtual/cpu_state.py

from typing import Dict, Any

class CPUState:
    def __init__(self):
        # General-purpose registers (R0–R7)
        self.registers: Dict[str, Any] = {f"R{i}": 0 for i in range(8)}

        # Special registers
        self.pc: int = 0       # Program Counter
        self.sp: int = 0xFF    # Stack Pointer (arbitrary top of memory)
        self.flags: Dict[str, bool] = {
            "Z": False,  # Zero flag
            "N": False,  # Negative flag
            "S": False,  # Symbolic mode flag
        }

        # Memory simulation (1KB default)
        self.memory: Dict[int, Any] = {i: 0 for i in range(1024)}

        # Symbolic memory
        self.symbolic_memory: Dict[str, Any] = {}

        # Output/trace
        self.output: list[str] = []

    def dump_state(self) -> Dict[str, Any]:
        return {
            "registers": self.registers,
            "pc": self.pc,
            "sp": self.sp,
            "flags": self.flags,
            "symbolic_memory": self.symbolic_memory,
            "output": self.output[-10:],
        }

    def reset(self):
        self.__init__()