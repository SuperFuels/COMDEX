# glyph_dispatcher.py
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.dna_chain.crispr_ai import generate_mutation_proposal

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
            self._write_cube(x, y, z, glyph)

        elif action == "run_mutation":
            module = parsed_glyph.get("module")
            reason = parsed_glyph.get("reason", "No reason provided.")
            if module:
                print(f"🧬 Running CRISPR mutation for {module}")
                generate_mutation_proposal(module, reason)
            else:
                print("❌ Missing module name for mutation.")

        elif action == "log":
            msg = parsed_glyph.get("message", "No message.")
            print(f"📜 Glyph Log: {msg}")

        else:
            print(f"❓ Unknown glyph action: {action}")

    def _write_cube(self, x, y, z, glyph):
        coord = f"{x},{y},{z}"
        container = self.state_manager.get_current_container()
        if "cubes" not in container:
            container["cubes"] = {}
        container["cubes"][coord] = {"glyph": glyph}
        print(f"📝 Wrote glyph '{glyph}' to cube ({coord})")