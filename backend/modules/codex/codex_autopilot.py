# 📁 codex_autopilot.py
# ============================

import random
import time
from datetime import datetime

from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
from backend.modules.glyphos.glyph_mutator import propose_mutation as score_and_propose_mutation
from backend.modules.glyphos.glyph_trace_logger import GlyphTraceLogger
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# ✅ DNA Switch registration
DNA_SWITCH.register(__file__)


class CodexAutopilot:
    def __init__(self):
        self.codex = CodexCore()
        self.logger = GlyphTraceLogger()
        self.metrics = CodexMetrics()

    def evolve(self):
        recent = self.logger.get_recent_traces(limit=10)
        mutation_count = 0

        for trace in recent:
            glyph = trace.get("glyph")
            result = trace.get("result")
            timestamp = trace.get("timestamp")

            if not glyph or not result:
                continue

            if random.random() < 0.25:  # 25% mutation chance
                print(f"🧬 Proposing mutation based on runtime: {glyph}")
                score_and_propose_mutation(
                    glyph,
                    context="autopilot",
                    result=result
                )
                mutation_count += 1

                # 🔁 WebSocket broadcast
                send_codex_ws_event("autopilot_mutation", {
                    "glyph": glyph,
                    "result": result,
                    "timestamp": timestamp,
                    "mutation_reason": "runtime feedback",
                    "source": "CodexAutopilot"
                })

        self.metrics.record_autopilot(mutation_count)

    def loop(self, interval=10, max_cycles=None):
        """
        Run autopilot in a continuous loop with optional limit.
        """
        print(f"[Autopilot] Starting loop every {interval}s")
        cycle = 0
        while True:
            self.evolve()
            cycle += 1
            if max_cycles and cycle >= max_cycles:
                print(f"[Autopilot] Completed {cycle} cycles")
                break
            time.sleep(interval)

    def run_once(self):
        """
        Run a single evolution cycle.
        """
        self.evolve()