# backend/codexcore/virtual_cpu/cpu_program_loader.py

from typing import List, Tuple, Dict
from backend.codexcore.virtual_cpu.cpu_instructions import INSTRUCTION_SET

class CPUProgramLoader:
    def __init__(self):
        self.program_memory: List[Tuple[str, List[str]]] = []

    def parse_instruction_line(self, line: str) -> Tuple[str, List[str]]:
        """
        Parses a single line of instruction like:
        MOV R1, 5
        Returns ('MOV', ['R1', '5'])
        """
        line = line.strip()
        if not line or line.startswith("#"):
            return ("NOP", [])  # comment or empty

        parts = line.split()
        instr = parts[0].upper()
        args = " ".join(parts[1:]).split(",")
        args = [arg.strip() for arg in args if arg.strip()]
        return (instr, args)

    def load_program_from_lines(self, lines: List[str]) -> List[Tuple[str, List[str]]]:
        self.program_memory = [self.parse_instruction_line(line) for line in lines]
        return self.program_memory

    def get_loaded_program(self) -> List[Tuple[str, List[str]]]:
        return self.program_memory


# Optional test harness
if __name__ == "__main__":
    loader = CPUProgramLoader()
    program_lines = [
        "MOV R1, 10",
        "ADD R1, 5",
        "SYMB R1, ↔",
        "OUT R1",
        "SOUT R1"
    ]
    prog = loader.load_program_from_lines(program_lines)
    for instr, args in prog:
        print(f"{instr} {args}")