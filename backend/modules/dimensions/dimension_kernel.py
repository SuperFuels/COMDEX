"""
Dimension Kernel: 4D Runtime Control System
Powers runtime logic, space expansion, cube interaction, and dynamic glyph routing.
"""

import random
import uuid

class DimensionKernel:
    def __init__(self, container_id):
        self.container_id = container_id
        self.cubes = {}  # keyed by (x,y,z,t)
        self.runtime_ticks = 0
        self.avatar_positions = {}  # id -> position

    def register_cube(self, x, y, z, t=0, metadata=None):
        key = (x, y, z, t)
        self.cubes[key] = {
            "id": str(uuid.uuid4()),
            "glyphs": [],
            "metadata": metadata or {},
            "active": True,
        }

    def mark_avatar_location(self, avatar_id, position):
        self.avatar_positions[avatar_id] = dict(position)
        key = (position["x"], position["y"], position["z"], position["t"])
        if key not in self.cubes:
            self.register_cube(*key)
        self.cubes[key]["metadata"]["avatar_here"] = avatar_id

    def add_glyph(self, x, y, z, t, glyph):
        key = (x, y, z, t)
        if key not in self.cubes:
            self.register_cube(x, y, z, t)
        self.cubes[key]["glyphs"].append(glyph)

    def get_glyph_at(self, x, y, z, t):
        key = (x, y, z, t)
        return self.cubes.get(key, {}).get("glyphs", [])

    def place_glyph(self, x, y, z, t, glyph):
        self.add_glyph(x, y, z, t, glyph)
        return "✅ Glyph placed."

    def clear_location(self, x, y, z, t):
        key = (x, y, z, t)
        if key in self.cubes:
            self.cubes[key]["glyphs"] = []
            return "🧼 Glyphs cleared."
        return "⚠️ No cube to clear."

    def trigger_event(self, x, y, z, t, event="ping"):
        key = (x, y, z, t)
        if key not in self.cubes:
            self.register_cube(x, y, z, t)
        self.cubes[key]["metadata"]["event"] = event
        return f"⚡ Event '{event}' stored."

    def scan_area(self, x, y, z, t, radius=1):
        stimuli = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    for dt in range(-radius, radius + 1):
                        key = (x + dx, y + dy, z + dz, t + dt)
                        cube = self.cubes.get(key)
                        if cube and cube["glyphs"]:
                            stimuli.append({
                                "position": {"x": x + dx, "y": y + dy, "z": z + dz, "t": t + dt},
                                "glyphs": cube["glyphs"]
                            })
        return stimuli

    def run_glyph_programs(self):
        actions_triggered = []
        for key, cube in self.cubes.items():
            for glyph in cube.get("glyphs", []):
                if "→" in glyph:
                    parts = glyph.split("→")
                    if len(parts) == 2:
                        trigger = parts[0].strip()
                        action = parts[1].strip()
                        # Basic pattern check
                        if "if_" in trigger and "action:" in action:
                            actions_triggered.append({
                                "location": key,
                                "trigger": trigger,
                                "action": action
                            })
        return actions_triggered

    def get_active_region(self):
        return [key for key, cube in self.cubes.items() if cube["active"]]

    def tick(self):
        self.runtime_ticks += 1
        glyph_actions = self.run_glyph_programs()
        return {
            "tick": self.runtime_ticks,
            "active_cubes": len(self.get_active_region()),
            "glyph_actions": glyph_actions
        }

    def expand(self, axis="z", amount=1):
        new_keys = []
        for key in list(self.cubes.keys()):
            x, y, z, t = key
            for i in range(1, amount + 1):
                if axis == "z":
                    self.register_cube(x, y, z + i, t)
                elif axis == "x":
                    self.register_cube(x + i, y, z, t)
                elif axis == "y":
                    self.register_cube(x, y + i, z, t)
                elif axis == "t":
                    self.register_cube(x, y, z, t + i)
        return f"Expanded {axis} by {amount} units."

    def dump_snapshot(self):
        return {
            "container_id": self.container_id,
            "tick": self.runtime_ticks,
            "total_cubes": len(self.cubes),
            "glyph_count": sum(len(cube["glyphs"]) for cube in self.cubes.values())
        }