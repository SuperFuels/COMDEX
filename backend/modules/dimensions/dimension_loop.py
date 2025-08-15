"""
Dimension Kernel: 4D Runtime Control System
Powers runtime logic, space expansion, cube interaction, dynamic glyph routing, and symbolic-quantum execution.
"""

import random
import uuid

from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore
from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.teleport.portal_registry import PORTALS
from backend.modules.consciousness.state_manager import STATE

# ─────────────────────────────────────────────────────────────────────────────
# Address book + wormhole (optional, safe stubs if unavailable)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from backend.modules.aion.address_book import address_book
except Exception:  # pragma: no cover
    class _AddressBookStub:
        def register_container(self, *a, **k):
            pass
    address_book = _AddressBookStub()

try:
    from backend.modules.dna_chain.container_linker import link_wormhole
except Exception:  # pragma: no cover
    def link_wormhole(*a, **k):
        return False
# ─────────────────────────────────────────────────────────────────────────────


class DimensionKernel:
    def __init__(self, container_id, physics="default"):
        self.container_id = container_id
        self.physics = physics
        self.cubes = {}  # keyed by (x,y,z,t)
        self.runtime_ticks = 0
        self.avatar_positions = {}  # id -> position

        if physics == "symbolic-quantum":
            self.quantum_core = GlyphQuantumCore(container_id)
        else:
            self.quantum_core = None

        # ✅ Ensure this container is registered and (optionally) linked
        self._ensure_registered()

    # ── Address/Wormhole helpers (idempotent) ────────────────────────────────
    def _ensure_registered(self):
        """
        Register this container in the global address book and try to link a
        wormhole to the hub. Both operations are idempotent and safe.
        """
        try:
            container_doc = {
                "id": self.container_id,
                "name": self.container_id,
                "type": "kernel",
                "meta": {"source": "DimensionKernel"},
            }
            address_book.register_container(container_doc)
        except Exception:
            # keep silent; kernel must not fail because of address book
            pass

        try:
            # best-effort link into your default hub; returns False if not available
            link_wormhole(self.container_id, "ucs_hub")
        except Exception:
            # also silent; treat as optional
            pass
    # ─────────────────────────────────────────────────────────────────────────

    def register_cube(self, x, y, z, t=0, metadata=None):
        key = (x, y, z, t)
        self.cubes[key] = {
            "id": str(uuid.uuid4()),
            "glyphs": [],
            "metadata": metadata or {},
            "active": True,
        }

        if self.physics == "symbolic-quantum":
            glyph = "∿"  # symbolic QBit seed
            qbit = self.quantum_core.generate_qbit(glyph, coord=f"{x},{y},{z},{t}")
            self.cubes[key]["metadata"]["qbit"] = qbit

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
                if glyph.startswith("⌘TELEPORT"):
                    parts = glyph.split("::")
                    if len(parts) == 2:
                        portal_id = parts[1].strip()
                        payload = {
                            "source_cube": key,
                            "initiated_by": "DimensionKernel",
                            "runtime_tick": self.runtime_ticks
                        }
                        packet = TeleportPacket(
                            source=self.container_id,
                            destination="*",  # resolved by portal
                            payload=payload,
                            container_id=self.container_id,
                            portal_id=portal_id
                        )
                        PORTALS.teleport(packet)
                        actions_triggered.append({
                            "location": key,
                            "action": "teleport_dispatch",
                            "portal_id": portal_id
                        })

                elif "→" in glyph:
                    parts = glyph.split("→")
                    if len(parts) == 2:
                        trigger = parts[0].strip()
                        action = parts[1].strip()
                        if "if_" in trigger and "action:" in action:
                            actions_triggered.append({
                                "location": key,
                                "trigger": trigger,
                                "action": action
                            })
        return actions_triggered

    def collapse_all_qbits(self):
        if not self.quantum_core:
            return []

        results = []
        for key, cube in self.cubes.items():
            qbit = cube["metadata"].get("qbit")
            if qbit and qbit.get("state") != "collapsed":
                collapsed = self.quantum_core.collapse_qbit(qbit)
                cube["metadata"]["qbit"] = collapsed
                results.append({
                    "location": key,
                    "collapsed_to": collapsed["collapsed"]
                })
        return results

    def get_active_region(self):
        return [key for key, cube in self.cubes.items() if cube["active"]]

    def tick(self):
        self.runtime_ticks += 1
        glyph_actions = self.run_glyph_programs()

        if self.physics == "symbolic-quantum":
            self.collapse_all_qbits()

        return {
            "tick": self.runtime_ticks,
            "active_cubes": len(self.get_active_region()),
            "glyph_actions": glyph_actions
        }

    def expand(self, axis="z", amount=1):
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

        # After growth, re-ensure registration & wormhole link (idempotent)
        self._ensure_registered()
        return f"Expanded {axis} by {amount} units."

    def dump_snapshot(self):
        return {
            "container_id": self.container_id,
            "tick": self.runtime_ticks,
            "total_cubes": len(self.cubes),
            "glyph_count": sum(len(cube["glyphs"]) for cube in self.cubes.values())
        }