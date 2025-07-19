# ============================
# 📁 codex_scheduler.py
# ============================

import time
import threading
from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_feedback_loop import CodexFeedbackLoop
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.codex_mind_model import CodexMindModel
from backend.modules.codex.codex_memory_triggers import CodexMemoryTrigger
from backend.modules.codex.codex_autopilot import CodexAutopilot
from backend.modules.codex.codex_boot import boot_codex_runtime
from backend.modules.codex.codex_executor import CodexExecutor  # ✅ NEW
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.hexcore.memory_engine import MEMORY

# ✅ Pause/resume support
from backend.modules.state_manager import STATE


class CodexScheduler:
    def __init__(self):
        print("📅 Initializing Codex Scheduler...")
        self.codex = CodexCore()
        self.feedback = CodexFeedbackLoop()
        self.metrics = CodexMetrics()
        self.mind_model = CodexMindModel()
        self.trigger = CodexMemoryTrigger()
        self.autopilot = CodexAutopilot()
        self.tessaris = TessarisEngine()
        self.executor = CodexExecutor()  # ✅ NEW

        self.tasks = []
        self.running = False

    def add_task(self, glyph: str, trigger: dict, metadata: dict = {}):
        """Schedule a glyph execution when condition is met."""
        self.tasks.append({
            "glyph": glyph,
            "trigger": trigger,
            "metadata": metadata,
            "executed": False
        })
        print(f"📅 Scheduled glyph {glyph} with trigger: {trigger}")

    def _check_trigger(self, trigger: dict) -> bool:
        """
        Check if the symbolic condition is satisfied.
        Supported trigger types:
        - {"type": "interval", "seconds": 10}
        - {"type": "memory_contains", "keyword": "dream"}
        - {"type": "tick_multiple", "mod": 5}
        """
        ttype = trigger.get("type")
        if ttype == "interval":
            return time.time() % trigger.get("seconds", 10) < 1
        elif ttype == "memory_contains":
            keyword = trigger.get("keyword", "")
            recent = MEMORY.query(limit=5)
            return any(keyword in m.get("content", "") for m in recent)
        elif ttype == "tick_multiple":
            tick = MEMORY.get_tick()
            return tick % trigger.get("mod", 5) == 0
        return False

    def _run_task(self, task):
        glyph = task["glyph"]
        metadata = task.get("metadata", {})
        try:
            result = self.executor.execute(glyph, metadata)  # ✅ UPDATED
            self.metrics.record_execution()
            print(f"✅ CodexScheduler executed: {glyph} → {result}")

            MEMORY.store({
                "label": "codex_scheduler_execution",
                "type": "auto_glyph",
                "glyph": glyph,
                "trigger": task["trigger"],
                "result": result
            })

            self.tessaris.extract_intents_from_glyphs([glyph], metadata)
        except Exception as e:
            self.metrics.record_error()
            print(f"🚨 CodexScheduler execution error: {e}")

    def tick(self):
        if STATE.is_paused():
            print("⏸️ Codex Tick paused by StateManager.")
            return

        print("🔁 Codex Tick Started")

        # Step 1: Scheduled task execution
        for task in self.tasks:
            if task["executed"]:
                continue
            if self._check_trigger(task["trigger"]):
                self._run_task(task)
                task["executed"] = True

        # Step 2: Scan memory and trigger glyphs
        triggered_glyphs = self.trigger.scan_and_trigger()
        for glyph in triggered_glyphs or []:
            self.mind_model.observe(glyph)
            self.metrics.record_execution()

        # Step 3: Run symbolic evolution via autopilot
        self.autopilot.evolve()
        self.metrics.record_mutation()

        # Step 4: Feedback analysis
        try:
            print("🔁 Running Codex feedback analysis...")
            self.feedback.reinforce_or_mutate()
        except Exception as e:
            print(f"⚠️ Codex feedback loop failed: {e}")

        # Step 5: Metrics + Predictions
        try:
            print("📊 Codex Metrics:", self.metrics.dump())
            print("🧠 Codex Predictions:", self.mind_model.symbol_predictions)
        except Exception as e:
            print(f"⚠️ Codex metrics or prediction dump failed: {e}")

        print("✅ Codex Tick Complete\n")

    def run(self, interval_seconds=10):
        if self.running:
            return
        self.running = True
        print("🚀 CodexScheduler Loop Running...")
        while self.running:
            self.tick()
            time.sleep(interval_seconds)


if __name__ == "__main__":
    boot_codex_runtime()
    scheduler = CodexScheduler()

    # 🧪 Example: schedule a test glyph
    scheduler.add_task("🜂", {"type": "tick_multiple", "mod": 3})
    scheduler.run(interval_seconds=5)