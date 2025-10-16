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
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.codex.codex_cost_estimator import CodexCostEstimator
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.consciousness.state_manager import STATE

# ✅ New: QWave emitter
from backend.modules.codex.codex_executor import emit_qwave_beam_ff  

# ✅ Tessaris utils
from backend.modules.tessaris.tessaris_utils import _get_tessaris  

# ✅ Cost threshold + toggle
COST_THRESHOLD = 100
QWAVE_EXEC_ON = True


class CodexScheduler:
    def __init__(self):
        print("📅 Initializing Codex Scheduler...")
        self.codex = CodexCore()
        self.feedback = CodexFeedbackLoop()
        self.metrics = CodexMetrics()
        self.mind_model = CodexMindModel()
        self.trigger = CodexMemoryTrigger()
        self.autopilot = CodexAutopilot()
        self.executor = CodexExecutor()

        self.estimator = CodexCostEstimator()  # ✅ Cost estimator instance
        self.tasks = []
        self.running = False

    def add_task(self, glyph: str, trigger: dict, metadata: dict = {}):
        self.tasks.append({
            "glyph": glyph,
            "trigger": trigger,
            "metadata": metadata,
            "executed": False
        })
        print(f"📅 Scheduled glyph {glyph} with trigger: {trigger}")

    def _check_trigger(self, trigger: dict) -> bool:
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
            context = {
                "memory": MEMORY.query(limit=10),
                "tick": MEMORY.get_tick(),
                "metadata": metadata
            }
            cost = self.estimator.estimate_glyph_cost(glyph, context)

            # ✅ Hybrid Router
            if QWAVE_EXEC_ON and glyph in {"∇", "⊗", "□"}:
                print(f"🌊 Routing glyph {glyph} → QWave (cost={cost.total()})")
                emit_qwave_beam_ff(
                    source="codex_scheduler",
                    payload={
                        "wave_id": f"sched_{int(time.time()*1000)}",
                        "event": "scheduled_exec",
                        "mutation_type": "qwave",
                        "container_id": metadata.get("container_id", "unknown"),
                        "glow": getattr(cost, "energy", 0.0),
                        "pulse": getattr(cost, "complexity", 0.0),
                        "glyph": glyph,
                        "cost": cost.total(),
                    },
                    context={"container_id": metadata.get("container_id", "unknown")}
                )
                return

            elif cost.total() > COST_THRESHOLD:
                print(f"⚠️ Cost {cost.total()} exceeds threshold. Triggering collapse.")
                self._collapse_container(metadata)
                return

        except Exception as e:
            print(f"⚠️ Cost estimation failed: {e}")

        # ✅ Default: symbolic execution
        try:
            result = self.executor.execute(glyph, metadata)
            self.metrics.record_execution()
            print(f"✅ CodexScheduler executed: {glyph} → {result}")

            MEMORY.store({
                "label": "codex_scheduler_execution",
                "type": "auto_glyph",
                "glyph": glyph,
                "trigger": task["trigger"],
                "result": result
            })

            # 🔮 Tessaris alignment (photon-aware)
            try:
                _get_tessaris().extract_intents_from_glyphs(
                    [glyph],
                    origin="photon",
                    context=metadata
                )
            except Exception as e:
                print(f"⚠️ Tessaris alignment failed for glyph {glyph}: {e}")

        except Exception as e:
            self.metrics.record_error()
            print(f"🚨 CodexScheduler execution error: {e}")

    def _collapse_container(self, metadata: dict):
        """Collapse or freeze the current container (placeholder logic)."""
        try:
            container_id = metadata.get("container_id", "unknown")
            print(f"🧊 Collapsing container: {container_id}")
            # TODO: Replace with real collapse logic if needed
        except Exception as e:
            print(f"❌ Collapse failed: {e}")

    def tick(self):
        if STATE.is_paused():
            print("⏸️ Codex Tick paused by StateManager.")
            return

        print("🔁 Codex Tick Started")

        for task in self.tasks:
            if task["executed"]:
                continue
            if self._check_trigger(task["trigger"]):
                self._run_task(task)
                task["executed"] = True

        triggered_glyphs = self.trigger.scan_and_trigger()
        for glyph in triggered_glyphs or []:
            self.mind_model.observe(glyph)
            self.metrics.record_execution()

        self.autopilot.evolve()
        self.metrics.record_mutation()

        try:
            print("🔁 Running Codex feedback analysis...")
            self.feedback.reinforce_or_mutate()
        except Exception as e:
            print(f"⚠️ Codex feedback loop failed: {e}")

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
    scheduler.add_task("🜂", {"type": "tick_multiple", "mod": 3})
    scheduler.run(interval_seconds=5)