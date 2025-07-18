# 📁 codex_boot.py

from backend.modules.codex.codex_runtime_loop import CodexRuntimeLoop
from backend.modules.codex.codex_memory_triggers import CodexMemoryTrigger
from backend.modules.codex.codex_autopilot import CodexAutopilot


def boot_codex_runtime():
    print("🚀 Booting Codex Runtime...")
    runtime = CodexRuntimeLoop()
    trigger = CodexMemoryTrigger()
    autopilot = CodexAutopilot()

    runtime.run_once()
    trigger.scan_and_trigger()
    autopilot.evolve()

    print("✅ Codex Runtime initialized.")