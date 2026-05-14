# 📁 backend/modules/codex/virtual/virtual_registers.py

class VirtualRegisters:
    """
    Symbolic registers used by CodexVirtualCPU.
    Stores values and symbolic glyph states.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.registers = {
            "ACC": None,     # Accumulator
            "TMP": None,     # Temporary buffer
            "PC": 0,         # Program Counter
            "FLAG": None,    # Conditional flag
            "STACK": [],     # Symbolic stack
            "MEM": {},       # Temporary memory slots
        }

    def set(self, name, value):
        if name in self.registers:
            self.registers[name] = value
        elif name.startswith("MEM_"):
            self.registers["MEM"][name] = value
        else:
            raise KeyError(f"Register '{name}' not defined")

    def get(self, name):
        if name in self.registers:
            return self.registers[name]
        elif name.startswith("MEM_"):
            return self.registers["MEM"].get(name)
        else:
            raise KeyError(f"Register '{name}' not defined")

    def push_stack(self, value):
        self.registers["STACK"].append(value)

    def pop_stack(self):
        if self.registers["STACK"]:
            return self.registers["STACK"].pop()
        return None

    def dump(self):
        return {
            "ACC": self.registers["ACC"],
            "TMP": self.registers["TMP"],
            "PC": self.registers["PC"],
            "FLAG": self.registers["FLAG"],
            "STACK": list(self.registers["STACK"]),
            "MEM": dict(self.registers["MEM"]),
        }