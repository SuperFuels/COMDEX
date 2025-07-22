# File: backend/codexcore/virtual_cpu/cpu_executor.py

from backend.codexcore.virtual_cpu.cpu_instruction_set import INSTRUCTION_SET
from backend.codexcore.virtual_cpu.cpu_registers import CPURegisters
from backend.codexcore.virtual_cpu.cpu_memory import CPUMemory
from backend.codexcore.virtual_cpu.cpu_program_loader import load_program


class VirtualCPU:
    def __init__(self):
        self.registers = CPURegisters()
        self.memory = CPUMemory()
        self.instruction_pointer = 0
        self.program = []
        self.running = False

    def load_program(self, program_lines):
        self.program = load_program(program_lines)
        self.instruction_pointer = 0

    def fetch(self):
        if self.instruction_pointer >= len(self.program):
            return None
        return self.program[self.instruction_pointer]

    def decode(self, instr):
        op = instr['operation']
        args = instr['args']
        return op, args

    def execute(self, op, args):
        if op not in INSTRUCTION_SET:
            raise ValueError(f"Unknown instruction: {op}")
        INSTRUCTION_SET[op](self, *args)

    def tick(self):
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
        self.running = True
        while self.running:
            self.tick()


# Optional inline test
if __name__ == "__main__":
    program = [
        "LOAD R1, 10",
        "LOAD R2, 20",
        "ADD R3, R1, R2",
        "STORE R3, 100",
        "PRINT R3",
        "HALT"
    ]

    cpu = VirtualCPU()
    cpu.load_program(program)
    cpu.run()