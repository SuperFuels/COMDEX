"""
DimensionEngine Runtime Loop
Drives 4D simulation and Avatar logic ticks inside containers.
"""

import time
from modules.avatar.avatar_core import AIONAvatar
from modules.dimensions.dc_handler import load_dimension
from modules.dimensions.glyph_logic import process_glyph_logic  # symbolic logic engine

class DimensionLoop:
    def __init__(self, container_id="default"):
        self.avatar = AIONAvatar(container_id)
        self.ticks = 0
        self.running = False
        load_dimension(container_id)  # preload if needed

    def start(self):
        self.avatar.spawn(0, 0, 0, 0)
        self.running = True
        print("🌀 Dimension Loop started.")

        while self.running:
            self.tick()
            time.sleep(1)  # 1 second per logic cycle (adjust as needed)

    def stop(self):
        self.running = False
        print("🛑 Dimension Loop stopped.")

    def tick(self):
        self.ticks += 1
        pos = self.avatar.current_location()
        glyph = self.avatar.focus_glyph()

        print(f"⏱️ Tick {self.ticks} @ {pos} → Glyph: {glyph}")

        if glyph:
            result = process_glyph_logic(glyph, avatar=self.avatar)
            print(f"🧠 Glyph processed: {result}")
        else:
            print("...no glyph found")

        # (Optional future: dream trigger, thought build, teleport portals, etc.)
