# backend/modules/lean/lean_proofverifier.py
from __future__ import annotations

import os
import json
import subprocess
import time
from pathlib import Path
from typing import Tuple, Optional, Union, Any, Dict

from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.dna_chain.dc_handler import load_dc_container


# ─────────────────────────────
#  Defaults
# ─────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_WORKSPACE_ROOT = _THIS_DIR / "workspace"


def verify_snapshot_params(steps: int, dt_ms: int, spec_version: str = "v1") -> Dict[str, Any]:
    from backend.modules.lean.snapshot_verify import verify_snapshot  # local import to avoid startup costs
    return verify_snapshot(steps=steps, dt_ms=dt_ms, spec_version=spec_version)

def _emit_snapshot_ws(cert: Dict[str, Any]) -> None:
    try:
        from backend.routes.ws.glyphnet_ws import emit_websocket_event  # type: ignore
        emit_websocket_event("lean_snapshot_verify_result", cert)
    except Exception:
        pass
        
# ─────────────────────────────
#  Lean Invocation (Lake-aware)
# ─────────────────────────────
def _find_lean_root(start: str) -> Optional[str]:
    """
    Walk upward from a file/dir looking for a Lean project root.
    We accept any of: lakefile.lean, lakefile.toml, lean-toolchain
    """
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    for parent in [p, *p.parents]:
        if (parent / "lakefile.lean").exists() or (parent / "lakefile.toml").exists() or (parent / "lean-toolchain").exists():
            return str(parent)
    return None


def _lake_env() -> Dict[str, str]:
    """
    Keep Lean/Lake caches off the small overlay FS when possible.
    """
    env = os.environ.copy()
    env.setdefault("ELAN_HOME", "/tmp/.elan")
    env.setdefault("LAKE_HOME", "/tmp/.lake")
    env.setdefault("XDG_CACHE_HOME", "/tmp/.cache")
    env.setdefault("TMPDIR", "/tmp")
    return env


def verify_lean_proof(lean_file_path: str, *, cwd: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Verifies the given Lean proof file.

    IMPORTANT:
      - Default cwd is backend/modules/lean/workspace (your Lake project root)
      - Uses `lake env lean` so module imports resolve
    """
    if not os.path.isfile(lean_file_path):
        return False, f"Lean file not found: {lean_file_path}"

    try:
        abs_path = Path(lean_file_path).resolve()

        # Prefer explicit cwd, else your workspace root, else best-effort autodetect, else file dir.
        root_path: Path
        if cwd:
            root_path = Path(cwd).resolve()
        elif DEFAULT_WORKSPACE_ROOT.exists() and (DEFAULT_WORKSPACE_ROOT / "lakefile.lean").exists():
            root_path = DEFAULT_WORKSPACE_ROOT
        else:
            detected = _find_lean_root(str(abs_path))
            root_path = Path(detected).resolve() if detected else abs_path.parent

        # Prefer relative paths to the workspace root (cleaner + avoids weird import roots)
        try:
            rel = abs_path.relative_to(root_path)
            lean_arg = str(rel)
        except Exception:
            lean_arg = str(abs_path)

        cmd = ["lake", "env", "lean", lean_arg]

        result = subprocess.run(
            cmd,
            cwd=str(root_path),
            env=_lake_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode == 0:
            return True, None

        err = (result.stderr or "").strip()
        out = (result.stdout or "").strip()
        msg = err if err else out
        return False, msg or f"Lean failed with code {result.returncode}"

    except Exception as e:
        return False, str(e)


# ─────────────────────────────
#  Lean Path Extraction (safe)
# ─────────────────────────────
def extract_lean_path(container: dict) -> Optional[str]:
    """
    Attempts to extract a Lean proof path from container metadata, glyphs, grid, or electrons.
    Safe with string glyph arrays.
    """
    meta = container.get("metadata", {}) or {}

    # canonical place
    lp = meta.get("lean_path")
    if isinstance(lp, str) and lp.strip():
        return lp.strip()

    for section in ("glyphs", "glyph_grid", "electrons"):
        items = container.get(section, [])
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            p = item.get("lean_path")
            if isinstance(p, str) and p.strip():
                return p.strip()

            gs = item.get("glyphs")
            if isinstance(gs, list):
                for g in gs:
                    if isinstance(g, dict):
                        p2 = g.get("lean_path")
                        if isinstance(p2, str) and p2.strip():
                            return p2.strip()

    return None


# ─────────────────────────────
#  Mutation + Auto-Rewrite Logic
# ─────────────────────────────
def verify_or_mutate(container: Dict[str, Any]) -> bool:
    """
    Attempts Codex rewrite once if Lean proof fails.
    """
    from backend.modules.codex.codex_executor import auto_mutate_container  # type: ignore

    container_id = container.get("id") or container.get("containerId") or "unknown"

    try:
        from backend.routes.ws.glyphnet_ws import emit_websocket_event  # type: ignore
        emit_websocket_event("logic_verification", {
            "containerId": container_id,
            "status": "❌ Initial proof failed - attempting auto-rewrite..."
        })
    except Exception:
        pass

    mutated = auto_mutate_container(container)
    candidate = mutated if isinstance(mutated, dict) else container

    ok = False
    if isinstance(candidate, dict):
        ok = validate_lean_container(candidate, autosave=False, allow_mutation=False)

    try:
        from backend.routes.ws.glyphnet_ws import emit_websocket_event  # type: ignore
        emit_websocket_event("logic_verification", {
            "containerId": container_id,
            "status": "✅ Proof valid after mutation" if ok else "❌ Still invalid after mutation"
        })
    except Exception:
        pass

    return ok


# ─────────────────────────────
#  Container Validation
# ─────────────────────────────
def validate_lean_container(
    container: Union[str, dict],
    autosave: bool = False,
    *,
    allow_mutation: bool = True,
) -> bool:
    """
    Validates a symbolic container with Lean content.
    """
    if isinstance(container, str):
        p = container
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    container = json.load(f)
            except Exception:
                container_id = Path(p).stem
                container = load_dc_container(container_id)
        else:
            container = load_dc_container(p)

    assert isinstance(container, dict)

    meta = container.get("metadata", {}) or {}

    # Default to your workspace root unless caller overrides.
    lean_cwd = meta.get("lean_cwd") or meta.get("lean_project_root")
    if not lean_cwd and DEFAULT_WORKSPACE_ROOT.exists():
        lean_cwd = str(DEFAULT_WORKSPACE_ROOT)

    lean_path = extract_lean_path(container)
    container_id = container.get("id") or (Path(lean_path).stem if lean_path else "unknown")

    if not lean_path:
        result = {"status": "missing", "reason": "No lean_path found"}
        container.setdefault("validation", {})["lean"] = result
        print("⚠️ No Lean path found in container.")

        if hasattr(CodexMetrics, "record_lean_verification"):
            CodexMetrics.record_lean_verification(container_id, None, False, "No lean_path found")
        elif hasattr(CodexMetrics, "record_event"):
            CodexMetrics.record_event("lean_verification", {
                "container_id": container_id,
                "lean_path": None,
                "success": False,
                "error": "No lean_path found"
            })

        return False

    success, err = verify_lean_proof(lean_path, cwd=lean_cwd)

    container.setdefault("validation", {})["lean"] = {
        "status": "ok" if success else "error",
        "detail": None if success else err,
        "lean_path": lean_path,
        "lean_cwd": lean_cwd,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if hasattr(CodexMetrics, "record_lean_verification"):
        CodexMetrics.record_lean_verification(container_id, lean_path, success, err)
    elif hasattr(CodexMetrics, "record_event"):
        CodexMetrics.record_event("lean_verification", {
            "container_id": container_id,
            "lean_path": lean_path,
            "lean_cwd": lean_cwd,
            "success": success,
            "error": err,
        })

    try:
        from backend.routes.ws.glyphnet_ws import emit_websocket_event  # type: ignore
        emit_websocket_event("lean_verification_result", {
            "containerId": container_id,
            "leanPath": lean_path,
            "leanCwd": lean_cwd,
            "success": success,
            "error": err,
            "status": "✅ Proof verified" if success else "❌ Proof failed"
        })
    except Exception:
        pass

    if autosave and container.get("id"):
        out_path = f"backend/modules/dimensions/containers/{container['id']}.dc.json"
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(container, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved updated container to: {out_path}")
        except Exception as e:
            print(f"⚠️ Failed to save container {container_id}: {e}")

    if not success:
        print(f"❌ Lean proof failed for {container_id}")
        if allow_mutation:
            print("↪ attempting Codex rewrite...")
            return verify_or_mutate(container)
        return False

    print(f"✅ Lean verification passed for {lean_path}")
    return True


def is_logically_valid(container: dict, container_id: str = "unknown") -> bool:
    valid = validate_lean_container(container)
    try:
        from backend.routes.ws.glyphnet_ws import emit_websocket_event  # type: ignore
        emit_websocket_event("logic_verification", {
            "containerId": container_id,
            "status": "✅ Proof verified" if valid else "❌ Proof failed after mutation"
        })
    except Exception:
        pass
    return valid


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m backend.modules.lean.lean_proofverifier <path_to_dc.json> [--save]")
        raise SystemExit(1)

    path = sys.argv[1]
    autosave = "--save" in sys.argv

    try:
        with open(path, "r", encoding="utf-8") as f:
            container = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load container: {e}")
        raise SystemExit(1)

    success = validate_lean_container(container, autosave=autosave)
    print("✅ VALID" if success else "❌ INVALID")