# File: backend/codexcore_virtual/virtual_cpu_beam_core.py

from typing import Dict, Any, List
from backend.codexcore_virtual.symbolic_register import SymbolicRegister
from backend.codexcore_virtual.instruction_registry import SymbolicOpCode, OPCODE_HANDLER_MAP, registry
from backend.codexcore_virtual.opcode_wave_handler import OpcodeWaveHandler, OPCODE_HANDLER_MAP
from backend.modules.sqi.metrics_bus import metrics_bus
import time


class VirtualCPUBeamCore:
    """
    Beam-native symbolic CPU core using SymbolicRegister.
    Supports parallel symbolic execution, SQI metrics, and entangled register logic.
    """

    def __init__(self):
        self.registers: Dict[str, SymbolicRegister] = self._init_registers()
        self.wave_handler = OpcodeWaveHandler()
        self.stack: List[Any] = []
        self.instruction_pointer: int = 0
        self.output: List[str] = []
        self.running: bool = False
        self.ticks: int = 0
        self.trace_log: List[Dict[str, Any]] = []

    def _init_registers(self) -> Dict[str, SymbolicRegister]:
        return {f"R{i}": SymbolicRegister(f"R{i}") for i in range(8)}

    def reset(self):
        self.registers = self._init_registers()
        self.stack.clear()
        self.output.clear()
        self.ticks = 0
        self.instruction_pointer = 0
        self.running = False

    def load_program(self, instructions: List[Dict[str, Any]]):
        self.program = instructions
        self.instruction_pointer = 0

    def tick(self):
        if self.instruction_pointer >= len(self.program):
            self.running = False
            return

        instr = self.program[self.instruction_pointer]
        opcode = instr.get("opcode")
        args = instr.get("args", [])

        # ✅ Direct Symatics Wave Opcode Path
        if opcode in OPCODE_HANDLER_MAP:
            result = self.wave_handler.handle(opcode, args)

            # Push to metrics bus for consistency
            metrics_bus.push({
                "event": "wave_tick",
                "opcode": opcode,
                "args": args,
                "tick": self.ticks,
                "collapse_metrics": result.get("collapse_metrics", {}),
                "timestamp": result.get("timestamp", time.time()),
            })

            self.ticks += 1
            self.instruction_pointer += 1
            return result

        # ───────────────────────────────────────────────
        # Standard symbolic execution fallback
        # ───────────────────────────────────────────────
        tick_start = time.time()
        self._execute(opcode, args)
        tick_duration = time.time() - tick_start

        # Log to SQI MetricsBus
        metrics_bus.push({
            "event": "beam_tick",
            "opcode": opcode,
            "args": args,
            "tick": self.ticks,
            "duration": tick_duration
        })

        self.ticks += 1
        self.instruction_pointer += 1

    def run(self):
        self.running = True
        while self.running:
            self.tick()

    def _execute(self, opcode: str, args: List[Any]):
        handler_name = OPCODE_HANDLER_MAP.get(SymbolicOpCode(opcode), None)
        if handler_name and hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            handler(args)
        else:
            self._handle_unknown(opcode, args)

    def _handle_unknown(self, opcode: str, args: List[Any]):
        self.output.append(f"[??] Unknown opcode: {opcode} args={args}")

    # ------------------------
    # 🔧 Handler Implementations
    # ------------------------

    def handle_add(self, args):
        a, b, dest = args

        va = self.registers[a].get()
        vb = self.registers[b].get()

        # 🧠 Defensive fallback — interpret None as 0
        if va is None:
            va = 0
        if vb is None:
            vb = 0

        # Support numeric or string concatenation gracefully
        try:
            val = va + vb
        except TypeError:
            val = f"{va}{vb}"

        self.registers[dest].set(val)
        print(f"[⊕] {a} + {b} → {dest} = {val}")

    def handle_sequence(self, args):
        src, dest = args
        val = self.registers[src].get()
        self.registers[dest].set(val)
        self._log(f"[→] {src} → {dest} = {val}")

    def handle_bidir(self, args):
        a, b = args
        shared = (self.registers[a].get(), self.registers[b].get())
        self.registers[a].set(shared)
        self.registers[b].set(shared)
        self._log(f"[↔] Entangled {a} ↔ {b} = {shared}")

    def handle_loop(self, args):
        target = args[0]
        val = self.registers[target].get()
        self.stack.append(val)
        self._log(f"[⟲] Loop push: {val}")

    def handle_delay(self, args):
        duration = float(args[0])
        self._log(f"[⧖] Delay {duration}s")
        time.sleep(duration)

    def handle_store(self, args):
        reg, val = args
        self.registers[reg].set(val)
        self._log(f"[≡] Store {val} in {reg}")

    def handle_reflect(self, args):
        value = args[0]
        reflected = f"🪞{value}"
        self.stack.append(reflected)
        self._log(f"[🧽] Reflect: {value} → {reflected}")

    def handle_dream(self, args):
        topic = args[0]
        dream = f"✨{topic}"  # Placeholder
        self.stack.append(dream)
        self._log(f"[✦] Dream: {dream}")

    def handle_boot(self, args):
        target = args[0]
        self._log(f"[⚛] Boot sequence initiated for: {target}")

    def handle_mutate(self, args):
        reg = args[0]
        val = self.registers[reg].get()
        mutated = f"{val}*"
        self.registers[reg].set(mutated)
        self._log(f"[⬁] Mutate {reg}: {val} → {mutated}")

    def handle_q_superpose(self, args):
        reg = args[0]
        val = self.registers[reg].get()
        superposed = f"{val}|ψ⟩"
        self.registers[reg].set(superposed)
        self._log(f"[⧜] Superpose {reg}: {val} → {superposed}")

    def handle_q_collapse(self, args):
        reg = args[0]
        val = self.registers[reg].get()
        collapsed = str(val).split("|")[0]
        self.registers[reg].set(collapsed)
        self._log(f"[⧝] Collapse {reg}: {val} → {collapsed}")

    def handle_q_entangle(self, args):
        a, b = args
        state = f"{a}<=>{b}"
        self.registers[a].set(state)
        self.registers[b].set(state)
        self._log(f"[⧠] Quantum entangle: {a}, {b} → {state}")

    def handle_compress(self, args):
        reg = args[0]
        val = self.registers[reg].get()
        compressed = str(val)[:4] + "…"
        self.registers[reg].set(compressed)
        self._log(f"[⋰] Compress {reg}: {val} → {compressed}")

    def handle_expand(self, args):
        reg = args[0]
        val = self.registers[reg].get()
        expanded = f"{val}...EXPANDED"
        self.registers[reg].set(expanded)
        self._log(f"[⋱] Expand {reg}: {val} → {expanded}")

    # ------------------------
    # 🧠 Debugging & Logging
    # ------------------------

    def _log(self, msg: str):
        self.output.append(msg)
        self.trace_log.append({
            "tick": self.ticks,
            "ip": self.instruction_pointer,
            "msg": msg
        })
        print(msg)  # Optional for dev


# Example CLI runner
if __name__ == "__main__":
    test_program = [
        {"opcode": "≡", "args": ["R1", "Dream"]},
        {"opcode": "⟲", "args": ["R1"]},
        {"opcode": "↔", "args": ["R1", "R2"]},
        {"opcode": "✦", "args": ["Future"]},
        {"opcode": "⧖", "args": ["0.1"]},
        {"opcode": "⧠", "args": ["R1", "R2"]},
    ]

    cpu = VirtualCPUBeamCore()
    cpu.load_program(test_program)
    cpu.run()