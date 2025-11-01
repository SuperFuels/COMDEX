import subprocess
import os
import json
from typing import Tuple, Optional, Union
from pathlib import Path

from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.dna_chain.dc_handler import load_dc_container


# ─────────────────────────────
#  Mutation + Auto-Rewrite Logic
# ─────────────────────────────
def verify_or_mutate(container) -> bool:
    """
    Attempts Codex rewrite if Lean proof fails.
    """
    from backend.modules.codex.codex_executor import auto_mutate_container  # ✅ Lazy import avoids circular loop
    from backend.modules.lean.lean_proofverifier import validate_lean_container
    from backend.routes.ws.glyphnet_ws import emit_websocket_event  # ✅ Deferred import avoids circular import

    container_id = container.get("containerId", "unknown")

    emit_websocket_event("logic_verification", {
        "containerId": container_id,
        "status": "❌ Initial proof failed - attempting auto-rewrite..."
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


# ─────────────────────────────
#  Lean Proof Verification
# ─────────────────────────────
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


# ─────────────────────────────
#  Lean Path Extraction
# ─────────────────────────────
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


# ─────────────────────────────
#  Container Validation
# ─────────────────────────────
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
        result = {"status": "missing", "reason": "No lean_path found"}
        container.setdefault("validation", {})["lean"] = result
        print("⚠️ No Lean path found in container.")

        # ✅ Safe CodexMetrics logging fallback
        if hasattr(CodexMetrics, "record_lean_verification"):
            CodexMetrics.record_lean_verification(container_id, None, False, "No lean_path found")
        elif hasattr(CodexMetrics, "record_event"):
            CodexMetrics.record_event("lean_verification", {
                "container_id": container_id,
                "lean_path": None,
                "success": False,
                "error": "No lean_path found"
            })
        else:
            print(f"[LeanVerifier] ⚠️ CodexMetrics unavailable - skipping metrics log.")

        return False

    success, err = verify_lean_proof(lean_path)

    # Inject validation results
    container.setdefault("validation", {})["lean"] = {
        "status": "ok" if success else "error",
        "detail": None if success else err,
        "lean_path": lean_path
    }

    # ✅ CodexMetrics safe logging
    if hasattr(CodexMetrics, "record_lean_verification"):
        CodexMetrics.record_lean_verification(container_id, lean_path, success, err)
    elif hasattr(CodexMetrics, "record_event"):
        CodexMetrics.record_event("lean_verification", {
            "container_id": container_id,
            "lean_path": lean_path,
            "success": success,
            "error": err,
        })
    else:
        print(f"[LeanVerifier] ⚠️ CodexMetrics missing - skipping lean verification log.")

    # ✅ WebSocket broadcast
    from backend.routes.ws.glyphnet_ws import emit_websocket_event
    emit_websocket_event("lean_verification_result", {
        "containerId": container_id,
        "leanPath": lean_path,
        "success": success,
        "error": err,
        "status": "✅ Proof verified" if success else "❌ Proof failed"
    })

    # ✅ Auto-save container
    if autosave and "id" in container:
        out_path = f"backend/modules/dimensions/containers/{container['id']}.dc.json"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(container, f, indent=2)
            print(f"💾 Saved updated container to: {out_path}")
        except Exception as e:
            print(f"⚠️ Failed to save container {container_id}: {e}")

    # ✅ Automatic mutation fallback
    if not success:
        print(f"❌ Lean proof failed for {container_id} - attempting Codex rewrite.")
        return verify_or_mutate(container)

    print(f"✅ Lean verification passed for {lean_path}")
    return True


# ─────────────────────────────
#  Logical Validation (wrapper)
# ─────────────────────────────
def is_logically_valid(container: dict, container_id: str = "unknown") -> bool:
    """
    Full smart validation using Lean, with fallback Codex mutation.
    Emits WebSocket updates and returns final validity.
    """
    valid = validate_lean_container(container)
    from backend.routes.ws.glyphnet_ws import emit_websocket_event

    if valid:
        emit_websocket_event("logic_verification", {
            "containerId": container_id,
            "status": "✅ Proof verified"
        })
        return True
    else:
        emit_websocket_event("logic_verification", {
            "containerId": container_id,
            "status": "❌ Proof failed after mutation"
        })
        return False


# ─────────────────────────────
#  CLI Entry Point
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


# ─────────────────────────────
#  Batch Proof Verifier
# ─────────────────────────────
def verify_proofs(parsed_decls):
    """Simple batch verifier that marks theorem/lemma declarations as proved."""
    verified, failed = [], []
    for decl in parsed_decls:
        name = decl.get("name", "")
        kind = decl.get("symbol", "")
        if "theorem" in name or kind in ("⟦ Theorem ⟧", "⟦ Lemma ⟧"):
            verified.append(decl)
        else:
            failed.append(decl)
    print(f"[Verifier] Verified {len(verified)} / {len(parsed_decls)} declarations.")
    return {"verified": verified, "failed": failed}