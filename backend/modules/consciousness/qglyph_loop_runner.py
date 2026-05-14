# backend/modules/consciousness/qglyph_loop_runner.py
# ──────────────────────────────────────────────────────────────
#  Tessaris * QGlyph Loop Runner
#  Runs a continuous loop generating and collapsing QGlyphs
#  via the GlyphQuantumCore, harmonized for QQC stack.
# ──────────────────────────────────────────────────────────────

import asyncio
import random
from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore


class QGlyphLoopRunner:
    """
    Runs a background resonance loop that generates and collapses QGlyphs.
    Used by the AION Cognitive Dispatcher's symbolic system group.
    """

    def __init__(self, container_id="main", interval_sec=2.0):
        self.container_id = container_id
        self.interval_sec = interval_sec
        self.core = GlyphQuantumCore(container_id=container_id)
        self._running = False

    async def run(self, payload=None):
        """
        Starts the QGlyph resonance loop asynchronously.
        """
        self._running = True
        print(f"[QGlyphLoopRunner] ⚛️ Starting loop for container {self.container_id}")

        while self._running:
            glyph = random.choice(["⊕", "->", "⟲", "↔", "⧖"])
            coord = f"{random.randint(0,5)}x{random.randint(0,5)}"
            qbit = self.core.generate_qbit(glyph, coord)
            print(f"[+] QBit Generated: {qbit}")

            await asyncio.sleep(self.interval_sec / 2)

            collapsed = self.core.collapse_qbit(qbit)
            print(f"[⧖] Collapsed: {collapsed}")

            await asyncio.sleep(self.interval_sec)

    def stop(self):
        """
        Stop the QGlyph loop gracefully.
        """
        self._running = False
        print(f"[QGlyphLoopRunner] ⏹️ Loop stopped for {self.container_id}")


# For standalone debugging
if __name__ == "__main__":
    runner = QGlyphLoopRunner(container_id="debug")
    asyncio.run(runner.run())