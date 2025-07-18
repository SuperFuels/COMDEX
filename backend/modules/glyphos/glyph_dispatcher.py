# backend/modules/glyphos/glyph_dispatcher.py

from backend.modules.consciousness.state_manager import StateManager
from backend.modules.dna_chain.crispr_ai import generate_mutation_proposal
from backend.modules.dna_chain.dc_handler import carve_glyph_cube
from backend.modules.glyphos.glyph_mutator import run_self_rewrite
from datetime import datetime

class GlyphDispatcher:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def dispatch(self, parsed_glyph: dict):
        action = parsed_glyph.get("action")
        print(f"🔁 Dispatching glyph action: {action}")

        if action == "teleport":
            destination = parsed_glyph.get("target")
            if destination:
                print(f"🌀 Teleporting to: {destination}")
                self.state_manager.teleport(destination)
            else:
                print("❌ No destination provided.")

        elif action == "write_cube":
            x, y, z = parsed_glyph.get("target", [0, 0, 0])
            glyph = parsed_glyph.get("value", "⛓️")
            meta = parsed_glyph.get("meta", {
                "source": "glyph_dispatcher",
                "label": "auto_write",
                "action": "write_cube",
                "timestamp": datetime.utcnow().isoformat()
            })
            self._write_cube(x, y, z, glyph, meta)

        elif action == "run_mutation":
            module = parsed_glyph.get("module")
            reason = parsed_glyph.get("reason", "No reason provided.")
            if module:
                print(f"🧬 Running CRISPR mutation for {module}")
                generate_mutation_proposal(module, reason)
            else:
                print("❌ Missing module name for mutation.")

        elif action == "rewrite":
            x, y, z = parsed_glyph.get("target", [0, 0, 0])
            coord = f"{x},{y},{z}"
            container = self.state_manager.get_current_container()
            container_path = container.get("path")
            if container_path:
                rewritten = run_self_rewrite(container_path, coord)
                if rewritten:
                    print(f"♻️ Self-rewriting glyph at {coord}")
                else:
                    print(f"⚠️ Rewrite skipped for {coord}")
            else:
                print("❌ Container path not found for rewrite.")

        elif action == "log":
            msg = parsed_glyph.get("message", "No message.")
            print(f"📜 Glyph Log: {msg}")

        else:
            print(f"❓ Unknown glyph action: {action}")

    def _write_cube(self, x, y, z, glyph, meta=None):
        coord = f"{x},{y},{z}"
        container = self.state_manager.get_current_container()
        container_path = container.get("path")
        if container_path:
            carve_glyph_cube(container_path, coord, glyph, meta)
            print(f"📝 Wrote glyph '{glyph}' to cube ({coord}) with metadata.")
        else:
            print("❌ Container path not found for write.")