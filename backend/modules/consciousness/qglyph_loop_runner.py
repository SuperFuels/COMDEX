# Runs a continuous loop generating and collapsing QGlyphs via GlyphQuantumCore

import asyncio
import random
from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore

async def qglyph_loop(container_id="main", interval_sec=2):
    core = GlyphQuantumCore(container_id=container_id)

    while True:
        glyph = random.choice(["⊕", "→", "⟲", "↔", "⧖"])
        coord = f"{random.randint(0,5)}x{random.randint(0,5)}"
        qbit = core.generate_qbit(glyph, coord)
        print(f"[+] QBit Generated: {qbit}")

        await asyncio.sleep(interval_sec / 2)

        collapsed = core.collapse_qbit(qbit)
        print(f"[⧖] Collapsed: {collapsed}")

        await asyncio.sleep(interval_sec)

if __name__ == "__main__":
    asyncio.run(qglyph_loop())