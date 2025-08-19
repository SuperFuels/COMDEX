import subprocess
import os
import json
from typing import Tuple, Optional, Union
from pathlib import Path

from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.dna_chain.dc_handler import load_dc_container
from backend.routes.ws.glyphnet_ws import emit_websocket_event

def verify_or_mutate(container) -> bool:
    """
    Attempts Codex rewrite if Lean proof fails.
    """
    from backend.modules.codex.codex_executor import auto_mutate_container  # ✅ Lazy import avoids circular loop
    from backend.modules.lean.lean_proofverifier import validate_lean_container
    from backend.routes.ws.glyphnet_ws import emit_websocket_event

    container_id = container.get("containerId", "unknown")

    emit_websocket_event("logic_verification", {
        "containerId": container_id,
        "status": "❌ Initial proof failed – attempting auto-rewrite..."
    })

    mutated = auto_mutate_container(container)

    if mutated and validate_lean_container(container):
        emit_websocket_event("logic_verification", {
            "containerId": container_id,
            "status": "✅ Proof valid after mutation"
        })
        return True

    emit_websocket_event("logic_verification", {
        "containerId": container_id,
        "status": "❌ Still invalid after mutation"
    })
    return False

def verify_lean_proof(lean_file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Verifies the given Lean proof file.
    Returns (True, None) on success, or (False, error_message) on failure.
    """
    if not os.path.isfile(lean_file_path):
        return False, f"Lean file not found: {lean_file_path}"

    try:
        result = subprocess.run(
            ["lean", lean_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            return True, None
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def extract_lean_path(container: dict) -> Optional[str]:
    """
    Attempts to extract a Lean proof path from container metadata, glyphs, grid, or electrons.
    """
    meta = container.get("metadata", {})
    if "lean_path" in meta:
        return meta["lean_path"]

    for section in ["glyphs", "glyph_grid", "electrons"]:
        for item in container.get(section, []):
            glyphs = item.get("glyphs") if isinstance(item.get("glyphs"), list) else [item]
            for g in glyphs:
                path = g.get("lean_path")
                if path:
                    return path
    return None


def validate_lean_container(container: Union[str, dict], autosave: bool = False) -> bool:
    """
    Validates a symbolic container with Lean content.
    - Accepts a container dict or path to .dc.json
    - Updates container['validation']['lean']
    - Emits WebSocket + CodexMetrics logs
    - Optionally saves container if `autosave` is True
    """
    if isinstance(container, str):
        container_id = Path(container).stem
        container = load_dc_container(container_id)

    lean_path = extract_lean_path(container)
    container_id = container.get("id", Path(lean_path).stem if lean_path else "unknown")

    if not lean_path:
        result = {
            "status": "missing",
            "reason": "No lean_path found"
        }
        container.setdefault("validation", {})["lean"] = result
        print("⚠️ No Lean path found in container.")
        CodexMetrics.record_lean_verification(container_id, None, False, "No lean_path found")
        return False

    success, err = verify_lean_proof(lean_path)

    # Inject result
    container.setdefault("validation", {})["lean"] = {
        "status": "ok" if success else "error",
        "detail": None if success else err,
        "lean_path": lean_path
    }

    # CodexMetrics logging
    CodexMetrics.record_lean_verification(container_id, lean_path, success, err)

    # Emit WebSocket event
    emit_websocket_event("lean_verification_result", {
        "containerId": container_id,
        "status": "ok" if success else "error",
        "detail": None if success else err,
        "leanPath": lean_path
    })

    if autosave and "id" in container:
        out_path = f"containers/{container['id']}.dc.json"
        with open(out_path, "w") as f:
            json.dump(container, f, indent=2)
        print(f"📦 Saved updated container to: {out_path}")

    if success:
        print(f"✅ Lean verification passed for {lean_path}")
    else:
        print(f"❌ Lean verification failed: {err}")

    return success


def is_logically_valid(container: dict, container_id: str = "unknown") -> bool:
    """
    Full smart validation using Lean, with fallback Codex mutation.
    Emits WebSocket updates and returns final validity.
    """
    valid = validate_lean_container(container)

    if valid:
        emit_websocket_event("logic_verification", {
            "containerId": container_id,
            "status": "✅ Proof verified"
        })
        return True
    else:
        emit_websocket_event("logic_verification", {
            "containerId": container_id,
            "status": "❌ Initial proof failed – attempting auto-rewrite..."
        })

        # ⏳ Lazy import to avoid circular dependency
        from backend.modules.codex.codex_executor import auto_mutate_container

        # Attempt Codex rewrite
        mutated = auto_mutate_container(container)
        if mutated:
            if validate_lean_container(container):
                emit_websocket_event("logic_verification", {
                    "containerId": container_id,
                    "status": "✅ Proof valid after mutation"
                })
                return True

        emit_websocket_event("logic_verification", {
            "containerId": container_id,
            "status": "❌ Proof failed after mutation"
        })
        return False


# ─────────────────────────────
# Optional CLI Entry Point
# ─────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python lean_proofverifier.py <path_to_dc.json> [--save]")
        sys.exit(1)

    path = sys.argv[1]
    autosave = "--save" in sys.argv

    try:
        with open(path) as f:
            container = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load container: {e}")
        sys.exit(1)

    success = validate_lean_container(container, autosave=autosave)
    print("✅ VALID" if success else "❌ INVALID")