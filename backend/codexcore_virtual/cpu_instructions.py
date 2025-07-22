# File: backend/codexcore/virtual_cpu/cpu_instructions.py

from backend.codexcore.virtual_cpu.cpu_state import CPUState

class CPUInstructions:
    def __init__(self, state: CPUState):
        self.state = state

    def execute(self, instr: str, *args):
        method = getattr(self, f"instr_{instr.lower()}", None)
        if not method:
            raise ValueError(f"Unknown instruction: {instr}")
        method(*args)

    # Basic Instructions
    def instr_load(self, reg: str, value):
        self.state.registers[reg] = int(value)

    def instr_add(self, reg1: str, reg2: str):
        self.state.registers[reg1] += self.state.registers[reg2]

    def instr_sub(self, reg1: str, reg2: str):
        self.state.registers[reg1] -= self.state.registers[reg2]

    def instr_mov(self, reg1: str, reg2: str):
        self.state.registers[reg1] = self.state.registers[reg2]

    def instr_cmp(self, reg1: str, reg2: str):
        val1 = self.state.registers[reg1]
        val2 = self.state.registers[reg2]
        self.state.flags['Z'] = int(val1 == val2)
        self.state.flags['N'] = int(val1 < val2)

    def instr_jmp(self, address: int):
        self.state.pc = address

    def instr_jz(self, address: int):
        if self.state.flags['Z']:
            self.state.pc = address

    def instr_jnz(self, address: int):
        if not self.state.flags['Z']:
            self.state.pc = address

    def instr_out(self, reg: str):
        value = self.state.registers[reg]
        self.state.trace.append((reg, value))
        print(f"[OUT] {reg} = {value}")

    # Symbolic Instructions
    def instr_symb(self, reg: str, symbol: str):
        self.state.symbolic_memory[reg] = symbol
        self.state.flags['S'] = 1
        print(f"[SYMB] {reg} ↔ {symbol}")

    def instr_scmp(self, reg1: str, reg2: str):
        sym1 = self.state.symbolic_memory.get(reg1, '')
        sym2 = self.state.symbolic_memory.get(reg2, '')
        self.state.flags['Z'] = int(sym1 == sym2)
        self.state.flags['S'] = 1

    def instr_sout(self, reg: str):
        sym = self.state.symbolic_memory.get(reg, '')
        self.state.trace.append((reg, sym))
        print(f"[SOUT] {reg} ↔ {sym}")

    def instr_nop(self):
        pass  # No operation