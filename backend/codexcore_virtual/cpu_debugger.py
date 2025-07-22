# File: backend/modules/codexcore_virtual/cpu_debugger.py

class CPUDebugger:
    def __init__(self, cpu):
        self.cpu = cpu
        self.breakpoints = set()
        self.step_mode = False
        self.enabled = True

    def add_breakpoint(self, addr: int):
        self.breakpoints.add(addr)
        print(f"🔖 Breakpoint added at address {addr}")

    def remove_breakpoint(self, addr: int):
        self.breakpoints.discard(addr)
        print(f"🚫 Breakpoint removed from address {addr}")

    def toggle_step_mode(self):
        self.step_mode = not self.step_mode
        print(f"⏱️ Step mode {'enabled' if self.step_mode else 'disabled'}")

    def debug_tick(self):
        if not self.enabled:
            return

        pc = self.cpu.pc
        if pc in self.breakpoints:
            print(f"🛑 Hit breakpoint at address {pc}")
            self.dump_state()
            self.wait_for_user()
        elif self.step_mode:
            print(f"🔬 Stepping into instruction at address {pc}")
            self.dump_state()
            self.wait_for_user()

    def wait_for_user(self):
        input("⏸️ Press Enter to continue...")

    def dump_state(self):
        print("\n===== CPU STATE DUMP =====")
        print(f"PC: {self.cpu.pc}")
        print("Registers:")
        for k, v in self.cpu.registers.items():
            print(f"  {k}: {v}")
        print("Memory (non-zero):")
        for k, v in sorted(self.cpu.memory.items()):
            if v != 0:
                print(f"  {k}: {v}")
        print("==========================\n")