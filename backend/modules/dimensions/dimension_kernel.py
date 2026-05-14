"""
Dimension Kernel: 4D Runtime Control System
Powers runtime logic, space expansion, cube interaction, dynamic glyph routing, and symbolic-quantum execution.
"""

import uuid
import logging
import time

from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore
from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.teleport.portal_registry import PORTALS
from backend.modules.consciousness.state_manager import STATE

# ✅ Optional hub connector (safe fallback if helper isn't present)
try:
    from backend.modules.dimensions.container_helpers import connect_container_to_hub
except Exception:  # pragma: no cover
    def connect_container_to_hub(*_a, **_k):
        pass

# ✅ KG writer + Microgrid singleton (best-effort)
try:
    from backend.modules.knowledge_graph.knowledge_graph_writer import kg_writer
except Exception:  # pragma: no cover
    kg_writer = None

try:
    from backend.modules.glyphos.microgrid_index import MicrogridIndex
    MICROGRID = getattr(MicrogridIndex, "_GLOBAL", None) or MicrogridIndex()
    MicrogridIndex._GLOBAL = MICROGRID
except Exception:  # pragma: no cover
    MICROGRID = None

logger = logging.getLogger(__name__)


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

        # ✅ Register kernel as a container-like node in the HQ graph (idempotent)
        try:
            doc = {
                "id": self.container_id,
                "name": f"DK-{self.container_id}",
                "geometry": "Dimension Kernel",
                "type": "dimension_kernel",
                "meta": {"address": f"ucs://local/{self.container_id}#dimension"},
            }
            connect_container_to_hub(doc)  # safe no-op if helper is stubbed
        except Exception as e:
            logger.debug(f"[DimensionKernel] connect_container_to_hub skipped: {e}")

    # ─────────────────────────────────────────────
    # Internal taps: KG emit + Microgrid register
    # ─────────────────────────────────────────────
    def _kg_emit(self, glyph_type, content, *, tags=None):
        """
        Best-effort KG journaling for DK events. This feeds:
        - glyph_grid (live KG),
        - SQLite ledger via kg_writer._write_to_container(),
        - Microgrid HUD (because _write_to_container has the tap).
        """
        if not kg_writer:
            return
        try:
            # prefer an explicit API if present
            if hasattr(kg_writer, "inject_glyph"):
                kg_writer.inject_glyph(
                    content=content,
                    glyph_type=glyph_type,
                    metadata={"container_id": self.container_id},
                    tags=tags or ["dk"],
                    agent_id="dimension_kernel",
                )
            elif hasattr(kg_writer, "write_glyph_entry"):
                entry = {
                    "id": f"dk_{uuid.uuid4().hex}",
                    "type": glyph_type,
                    "content": content,
                    "timestamp": time.time(),
                    "metadata": {"container_id": self.container_id, "tags": tags or ["dk"]},
                    "tags": tags or ["dk"],
                    "agent_id": "dimension_kernel",
                }
                kg_writer.write_glyph_entry(entry)
        except Exception:
            # never break runtime on telemetry
            pass

    def _mg_register(self, x, y, z, t, glyph, meta=None):
        """Register a visual blip for HUDs (small 16×16×16 window by modulo)."""
        if not MICROGRID:
            return
        try:
            MICROGRID.register_glyph(
                x % 16, y % 16, z % 16,
                glyph=str(glyph),
                layer=int(t) if t is not None else None,
                metadata={
                    "type": (meta or {}).get("type", "dk"),
                    "tags": (meta or {}).get("tags", []),
                    "energy": (meta or {}).get("energy", 1.0),
                    "container": self.container_id,
                },
            )
        except Exception:
            pass

    # ─────────────────────────────────────────────

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

        # 🧭 taps
        try:
            self._kg_emit(
                "dk_register_cube",
                {"event": "register_cube", "pos": {"x": x, "y": y, "z": z, "t": t}},
                tags=["dk", "cube"],
            )
            self._mg_register(x, y, z, t, glyph=f"cube@{x},{y},{z},{t}", meta={"type": "cube", "tags": ["dk", "cube"]})
        except Exception:
            pass

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

        # 🧭 taps
        try:
            self._kg_emit(
                "dk_place_glyph",
                {"event": "place_glyph", "pos": {"x": x, "y": y, "z": z, "t": t}, "glyph": glyph},
                tags=["dk", "glyph"],
            )
            self._mg_register(x, y, z, t, glyph=str(glyph), meta={"type": "glyph", "tags": ["dk", "glyph"]})
        except Exception:
            pass

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

        # 🧭 taps
        try:
            self._kg_emit(
                "dk_event",
                {"event": event, "pos": {"x": x, "y": y, "z": z, "t": t}},
                tags=["dk", "event"],
            )
            self._mg_register(x, y, z, t, glyph=f"evt:{event}", meta={"type": "event", "tags": ["dk", "event"]})
        except Exception:
            pass

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
                        # 🧭 taps
                        try:
                            x, y, z, t = key
                            self._kg_emit(
                                "dk_teleport_dispatch",
                                {"event": "teleport_dispatch", "portal_id": portal_id, "pos": {"x": x, "y": y, "z": z, "t": t}},
                                tags=["dk", "teleport"],
                            )
                            self._mg_register(x, y, z, t, glyph=f"tp:{portal_id}", meta={"type": "teleport", "tags": ["dk", "teleport"]})
                        except Exception:
                            pass

                elif "->" in glyph:
                    parts = glyph.split("->")
                    if len(parts) == 2:
                        trigger = parts[0].strip()
                        action = parts[1].strip()
                        if "if_" in trigger and "action:" in action:
                            actions_triggered.append({
                                "location": key,
                                "trigger": trigger,
                                "action": action
                            })
                            # 🧭 taps
                            try:
                                x, y, z, t = key
                                self._kg_emit(
                                    "dk_action_trigger",
                                    {"event": "action_trigger", "trigger": trigger, "action": action, "pos": {"x": x, "y": y, "z": z, "t": t}},
                                    tags=["dk", "rule"],
                                )
                            except Exception:
                                pass
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
                # 🧭 taps
                try:
                    x, y, z, t = key
                    self._kg_emit(
                        "dk_qbit_collapse",
                        {"event": "qbit_collapse", "pos": {"x": x, "y": y, "z": z, "t": t}, "to": collapsed["collapsed"]},
                        tags=["dk", "qbit"],
                    )
                    self._mg_register(x, y, z, t, glyph=f"⧖:{collapsed['collapsed']}", meta={"type": "qbit", "tags": ["dk", "qbit", "collapse"]})
                except Exception:
                    pass
        return results

    def get_active_region(self):
        return [key for key, cube in self.cubes.items() if cube["active"]]

    def tick(self):
        self.runtime_ticks += 1
        glyph_actions = self.run_glyph_programs()

        if self.physics == "symbolic-quantum":
            self.collapse_all_qbits()

        snapshot = {
            "tick": self.runtime_ticks,
            "active_cubes": len(self.get_active_region()),
            "glyph_actions": glyph_actions
        }

        # 🧭 taps (every 10 ticks to keep noise down)
        try:
            if self.runtime_ticks % 10 == 0:
                self._kg_emit("dk_tick", {"event": "tick", "snapshot": snapshot}, tags=["dk", "tick"])
        except Exception:
            pass

        return snapshot

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

        # 🧭 taps
        try:
            self._kg_emit("dk_expand", {"event": "expand", "axis": axis, "amount": amount}, tags=["dk", "expand"])
        except Exception:
            pass

        return f"Expanded {axis} by {amount} units."

    def dump_snapshot(self):
        return {
            "container_id": self.container_id,
            "tick": self.runtime_ticks,
            "total_cubes": len(self.cubes),
            "glyph_count": sum(len(cube["glyphs"]) for cube in self.cubes.values())
        }