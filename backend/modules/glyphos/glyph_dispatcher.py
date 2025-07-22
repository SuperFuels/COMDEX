# backend/modules/glyphos/glyph_dispatcher.py

from datetime import datetime
from typing import Dict

from backend.modules.consciousness.state_manager import StateManager
from backend.modules.dna_chain.crispr_ai import generate_mutation_proposal
from backend.modules.dna_chain.dc_handler import carve_glyph_cube
from backend.modules.glyphos.glyph_mutator import run_self_rewrite

class GlyphDispatcher:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def dispatch(self, parsed_glyph: Dict):
        action = parsed_glyph.get("action", "unknown")
        print(f"🔁 Dispatching glyph action: {action}")

        match action:
            case "teleport":
                self._handle_teleport(parsed_glyph)
            case "write_cube":
                self._handle_write_cube(parsed_glyph)
            case "run_mutation":
                self._handle_mutation(parsed_glyph)
            case "rewrite":
                self._handle_rewrite(parsed_glyph)
            case "log":
                self._handle_log(parsed_glyph)
            case _:
                print(f"❓ Unknown glyph action: {action}")

    def _handle_teleport(self, glyph: Dict):
        destination = glyph.get("target")
        if destination:
            print(f"🌀 Teleporting to: {destination}")
            self.state_manager.teleport(destination)
        else:
            print("❌ No destination provided.")

    def _handle_write_cube(self, glyph: Dict):
        coords = glyph.get("target", [0, 0, 0])
        x, y, z = coords if len(coords) == 3 else (0, 0, 0)
        value = glyph.get("value", "⛓️")

        meta = glyph.get("meta") or {
            "source": "glyph_dispatcher",
            "label": "auto_write",
            "action": "write_cube",
            "timestamp": datetime.utcnow().isoformat()
        }

        self._write_cube(x, y, z, value, meta)

    def _handle_mutation(self, glyph: Dict):
        module = glyph.get("module")
        reason = glyph.get("reason", "No reason provided.")
        if module:
            print(f"🧬 Running CRISPR mutation for {module}")
            generate_mutation_proposal(module, reason)
        else:
            print("❌ Missing module name for mutation.")

    def _handle_rewrite(self, glyph: Dict):
        coords = glyph.get("target", [0, 0, 0])
        x, y, z = coords if len(coords) == 3 else (0, 0, 0)
        coord_str = f"{x},{y},{z}"
        container = self.state_manager.get_current_container()
        container_path = container.get("path") if container else None

        if container_path:
            success = run_self_rewrite(container_path, coord_str)
            if success:
                print(f"♻️ Self-rewriting glyph at {coord_str}")
            else:
                print(f"⚠️ Rewrite skipped for {coord_str}")
        else:
            print("❌ Container path not found for rewrite.")

    def _handle_log(self, glyph: Dict):
        msg = glyph.get("message", "No message.")
        print(f"📜 Glyph Log: {msg}")

    def _write_cube(self, x: int, y: int, z: int, glyph: str, meta: Dict = None):
        coord = f"{x},{y},{z}"
        container = self.state_manager.get_current_container()
        container_path = container.get("path") if container else None

        if container_path:
            carve_glyph_cube(container_path, coord, glyph, meta)
            print(f"📝 Wrote glyph '{glyph}' to cube ({coord}) with metadata.")
        else:
            print("❌ Container path not found for write.")