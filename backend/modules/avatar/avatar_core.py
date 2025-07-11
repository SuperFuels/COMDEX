"""
AION Avatar Core
Embodied intelligence inside a .dc container.
Tracks position, glyph interaction, movement, memory tagging, glyph reactivity.
"""

from modules.dimensions.dimension_kernel import DimensionKernel
import random

class AIONAvatar:
    def __init__(self, container_id="default"):
        self.id = "AION"
        self.container_id = container_id
        self.kernel = DimensionKernel(container_id)
        self.position = {"x": 0, "y": 0, "z": 0, "t": 0}
        self.active = False
        self.inventory = []  # 🔑 Keys, tokens, items
        self.mind_state = {
            "mode": "idle",      # think, move, react, compress
            "emotion": None,
            "glyph_focus": None,
            "last_reaction": None
        }

    def spawn(self, x=0, y=0, z=0, t=0):
        self.position = {"x": x, "y": y, "z": z, "t": t}
        self.active = True
        self.kernel.mark_avatar_location(self.id, self.position)
        return f"🧬 Avatar spawned at {self.position}"

    def move(self, dx=0, dy=0, dz=0, dt=0):
        if not self.active:
            return "⚠️ Avatar not active"
        self.position["x"] += dx
        self.position["y"] += dy
        self.position["z"] += dz
        self.position["t"] += dt
        self.kernel.mark_avatar_location(self.id, self.position)
        return f"🚶 Moved to {self.position}"

    def random_step(self):
        axis = random.choice(["x", "y", "z"])
        delta = random.choice([-1, 1])
        return self.move(**{f"d{axis}": delta})

    def focus_glyph(self):
        glyphs = self.kernel.get_glyph_at(**self.position)
        if glyphs:
            self.mind_state["glyph_focus"] = glyphs[0]
            return f"🧠 Focusing on glyph: {glyphs[0]}"
        else:
            self.mind_state["glyph_focus"] = None
            return "🔍 No glyph found here."

    def react_to_glyphs(self):
        glyphs = self.kernel.get_glyph_at(**self.position)
        reactions = []
        for glyph in glyphs:
            if "→" in glyph:
                trigger, action = map(str.strip, glyph.split("→", 1))
                if "action:move" in action:
                    reactions.append(self.random_step())
                elif "action:focus" in action:
                    reactions.append(self.focus_glyph())
        self.mind_state["last_reaction"] = reactions
        return reactions or ["😐 No reactive glyphs."]

    def tick(self):
        if not self.active:
            return "⚠️ Avatar not active"
        self.kernel.tick()
        if self.mind_state["mode"] == "react":
            return self.react_to_glyphs()
        elif self.mind_state["mode"] == "move":
            return [self.random_step()]
        return ["⏳ Idle tick."]

    def current_location(self):
        return self.position

    def set_mode(self, mode):
        self.mind_state["mode"] = mode
        return f"🧠 Mode set to {mode}"

    def state(self):
        return {
            "id": self.id,
            "position": self.position,
            "mind": self.mind_state,
            "inventory": self.inventory,
        }

    # 🔐 Inventory Logic — Key Support
    def add_key(self, key):
        if key not in self.inventory:
            self.inventory.append(key)
            return f"🔑 Key '{key}' added to inventory."
        return f"🗝️ Already has key '{key}'."

    def has_key(self, key):
        return key in self.inventory

    def list_keys(self):
        return self.inventory