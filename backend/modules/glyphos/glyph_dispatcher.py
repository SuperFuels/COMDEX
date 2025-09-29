# -*- coding: utf-8 -*-
# File: backend/modules/glyphos/glyph_dispatcher.py
"""
Glyph Dispatcher
─────────────────────────────────────────────
Routes parsed glyph actions to runtime handlers.

Phase 8 (I1 Alignment):
- Delegates through registry_bridge.resolve_and_execute()
- Namespaces all actions as glyph:*
- Falls back to legacy _handle_* methods if no registry handler exists
"""

from datetime import datetime
from typing import Dict

from backend.modules.consciousness.state_manager import StateManager
from backend.modules.dna_chain.crispr_ai import generate_mutation_proposal
from backend.modules.dna_chain.dc_handler import carve_glyph_cube
from backend.modules.glyphos.glyph_mutator import run_self_rewrite
from backend.core.registry_bridge import registry_bridge
from backend.core.log_utils import make_log_event, log_event

class GlyphDispatcher:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def dispatch(self, parsed_glyph: Dict):
        action = parsed_glyph.get("action", "unknown")
        namespaced = f"glyph:{action}"
        print(f"🔁 Dispatching glyph action: {action}")

        # ✅ Step 1: Try registry bridge first
        if registry_bridge.has_handler(namespaced):
            try:
                result = registry_bridge.resolve_and_execute(
                    namespaced, **parsed_glyph, ctx=self.state_manager
                )
                payload = make_log_event(
                    event="registry_execute",
                    op=action,
                    canonical=namespaced,
                    args=[],
                    kwargs=parsed_glyph,
                    status="ok",
                    result=result,
                )
                log_event(payload)
                return result
            except Exception as e:
                payload = make_log_event(
                    event="registry_execute",
                    op=action,
                    canonical=namespaced,
                    args=[],
                    kwargs=parsed_glyph,
                    status="error",
                    result=None,
                    error=str(e),
                )
                log_event(payload)
                print(f"⚠️ Registry execution failed for {namespaced}: {e}")
                return {"status": "error", "error": str(e)}

        # ❌ Step 2: Fallback to legacy handlers
        match action:
            case "teleport":
                result = self._handle_teleport(parsed_glyph)
            case "write_cube":
                result = self._handle_write_cube(parsed_glyph)
            case "run_mutation":
                result = self._handle_mutation(parsed_glyph)
            case "rewrite":
                result = self._handle_rewrite(parsed_glyph)
            case "log":
                result = self._handle_log(parsed_glyph)
            case _:
                result = {"status": "unknown", "action": action}

        # ✅ Always emit structured log for fallback
        status = result.get("status", "ok")
        payload = make_log_event(
            event="registry_execute",
            op=action,
            canonical=namespaced,
            args=[],
            kwargs=parsed_glyph,
            status=status if status in ("ok", "error") else "stub",
            result=result if status == "ok" else None,
            error=result.get("error") if status not in ("ok",) else None,
        )
        log_event(payload)

        return result
    # ------------------------
    # Legacy Handlers
    # ------------------------
    def _handle_teleport(self, glyph: Dict):
        destination = glyph.get("target")
        if destination:
            print(f"🌀 Teleporting to: {destination}")
            self.state_manager.teleport(destination)
            return {"status": "ok", "teleported_to": destination}
        else:
            print("❌ No destination provided.")
            return {"status": "error", "error": "No destination"}

    def _handle_write_cube(self, glyph: Dict):
        coords = glyph.get("target", [0, 0, 0])
        x, y, z = coords if len(coords) == 3 else (0, 0, 0)
        value = glyph.get("value", "⛓️")

        meta = glyph.get("meta") or {
            "source": "glyph_dispatcher",
            "label": "auto_write",
            "action": "write_cube",
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._write_cube(x, y, z, value, meta)
        return {"status": "ok", "coords": (x, y, z), "value": value}

    def _handle_mutation(self, glyph: Dict):
        module = glyph.get("module")
        reason = glyph.get("reason", "No reason provided.")
        if module:
            print(f"🧬 Running CRISPR mutation for {module}")
            generate_mutation_proposal(module, reason)
            return {"status": "ok", "mutation_module": module}
        else:
            print("❌ Missing module name for mutation.")
            return {"status": "error", "error": "Missing module name"}

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
                return {"status": "ok", "rewritten": coord_str}
            else:
                print(f"⚠️ Rewrite skipped for {coord_str}")
                return {"status": "skipped", "coord": coord_str}
        else:
            print("❌ Container path not found for rewrite.")
            return {"status": "error", "error": "No container path"}

    def _handle_log(self, glyph: Dict):
        msg = glyph.get("message", "No message.")
        print(f"📜 Glyph Log: {msg}")
        return {"status": "ok", "log": msg}

    def _write_cube(self, x: int, y: int, z: int, glyph: str, meta: Dict = None):
        coord = f"{x},{y},{z}"
        container = self.state_manager.get_current_container()
        container_path = container.get("path") if container else None

        if container_path:
            carve_glyph_cube(container_path, coord, glyph, meta)
            print(f"📝 Wrote glyph '{glyph}' to cube ({coord}) with metadata.")
        else:
            print("❌ Container path not found for write.")