# 📁 backend/modules/codex/codex_emulator.py

from backend.modules.codex.virtual.codex_virtual_cpu import CodexVirtualCPU
from backend.modules.codex.codex_metrics import CodexMetrics

class CodexEmulator:
    """
    Executes symbolic instruction trees using the virtual Codex CPU.
    """

    def __init__(self):
        self.cpu = CodexVirtualCPU()
        self.metrics = CodexMetrics()

    def execute_instruction_tree(self, instruction_tree: dict, context: dict = None):
        """
        Executes a parsed instruction tree (from CodexLang or glyph structure).
        """
        if not instruction_tree or "instructions" not in instruction_tree:
            raise ValueError("Invalid instruction tree")

        instructions = instruction_tree["instructions"]
        context = context or {}

        for instr in instructions:
            try:
                # Ensure the target is present for trigger or target-based ops
                if instr.get("op") == "trigger":
                    meta = instr.get("meta", {})
                    target = meta.get("value") or instr.get("target") or "default_trigger"
                    context["target"] = target

                self.cpu.execute(instr, context=context)

                self.metrics.record_execution(
                    glyph=instr.get("glyph"),
                    source=context.get("source", "emulator"),
                    operator=instr.get("op")
                )

            except Exception as e:
                print(f"[⚠️] Runtime Error: {e}")
                self.metrics.record_error()

        return self.cpu.registers.dump()

    def get_metrics(self):
        return self.metrics.dump(detailed=True)

    def reset(self):
        self.cpu.reset()
        self.metrics.reset()