import os
import json
import shutil
from datetime import datetime
from typing import Any, Dict, Optional

from backend.modules.dna_chain.proposal_manager import load_proposals, save_proposals
from backend.modules.dna_chain.switchboard import get_module_path
from backend.modules.dna_chain.dna_address_lookup import register_backend_path, register_frontend_path
from backend.modules.dna_chain.dna_registry import update_dna_proposal
from backend.modules.dna_chain.dna_writer import save_version_snapshot, get_versions_for_file, restore_version

# ──────────────────────────────────────────────────────────────────────────────
# 🔐 Security / Environment
# ──────────────────────────────────────────────────────────────────────────────
MASTER_KEY = os.getenv("AION_MASTER_KEY")
APP_ENV = os.getenv("APP_ENV", os.getenv("ENV", "development")).lower()
DEV_ALLOW_DNA_NO_KEY = os.getenv("DEV_ALLOW_DNA_NO_KEY", "1")  # "1" enables dev override

# Where we persist feature flags (per container)
_THIS_DIR = os.path.dirname(__file__)
DNA_SWITCH_LOG = os.path.join(_THIS_DIR, "dna_switch_log.json")
DNA_FLAGS_PATH = os.path.join(_THIS_DIR, "dna_flags_store.json")

DEFAULT_FLAGS: Dict[str, Any] = {
    # E1 — Self-Growth switch (gates creative forks, auto-iteration, etc.)
    "self_growth": False,
    # Reserved for future tuning:
    "growth_factor": 1,         # multiplier for fork count / exploration breadth
    "max_concurrent_growth": 2, # guardrail for concurrent self-growth tasks
}

# ──────────────────────────────────────────────────────────────────────────────
# 🧭 Utilities
# ──────────────────────────────────────────────────────────────────────────────
def _utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"

def _read_json(path: str, default: Any) -> Any:
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def _is_prod() -> bool:
    return APP_ENV in ("prod", "production")

def _require_key(provided_key: Optional[str]) -> None:
    """Require master key in production; optionally bypass in dev."""
    if _is_prod():
        if not MASTER_KEY or provided_key != MASTER_KEY:
            raise PermissionError("Invalid master key (production mode).")
    else:
        # dev: allow if env says so; otherwise still require key
        if DEV_ALLOW_DNA_NO_KEY not in ("1", "true", "True"):
            if not MASTER_KEY or provided_key != MASTER_KEY:
                raise PermissionError("Invalid master key (dev mode).")

def _safe_broadcast(tag: str, payload: Dict[str, Any]) -> None:
    try:
        from backend.modules.websocket_manager import broadcast_event
    except Exception:
        return
    try:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(broadcast_event(tag, payload))
        except RuntimeError:
            asyncio.run(broadcast_event(tag, payload))
    except Exception:
        pass

# ──────────────────────────────────────────────────────────────────────────────
# 📦 Feature Flag Store (per container)
# ──────────────────────────────────────────────────────────────────────────────
def _load_flags_store() -> Dict[str, Dict[str, Any]]:
    """
    Returns a dict: { container_id: { flag_name: value, ... }, ... }
    """
    data = _read_json(DNA_FLAGS_PATH, {})
    if not isinstance(data, dict):
        data = {}
    return data

def _save_flags_store(store: Dict[str, Dict[str, Any]]) -> None:
    _write_json(DNA_FLAGS_PATH, store)

def get_flags(container_id: Optional[str]) -> Dict[str, Any]:
    """
    Returns all flags for a container, merged with DEFAULT_FLAGS.
    """
    if not container_id:
        return DEFAULT_FLAGS.copy()
    store = _load_flags_store()
    flags = store.get(container_id, {})
    merged = DEFAULT_FLAGS.copy()
    merged.update(flags if isinstance(flags, dict) else {})
    return merged

def is_enabled(flag: str, container_id: Optional[str]) -> bool:
    return bool(get_flags(container_id).get(flag, False))

def set_flag(
    container_id: str,
    flag: str,
    value: Any,
    *,
    actor: str = "system",
    reason: Optional[str] = None,
    provided_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Toggle/set a feature flag for a container (with audit + optional WS emit).
    - Requires MASTER_KEY in prod. In dev, can be allowed without key.
    """
    _require_key(provided_key)

    store = _load_flags_store()
    flags = store.get(container_id, {})
    if not isinstance(flags, dict):
        flags = {}

    # Coerce boolean for known boolean flags
    if flag in ("self_growth",):
        value = bool(value)

    flags[flag] = value
    store[container_id] = flags
    _save_flags_store(store)

    entry = {
        "action": "set_flag",
        "container_id": container_id,
        "flag": flag,
        "value": value,
        "actor": actor,
        "reason": reason,
        "timestamp": _utc_now(),
        "env": APP_ENV,
    }
    log_dna_switch(entry)
    _safe_broadcast("dna.switch", {"type": "dna_flag_update", **entry})
    return entry

# High-level helpers for E1 — Self-Growth
def is_self_growth_enabled(container_id: Optional[str]) -> bool:
    return is_enabled("self_growth", container_id)

def enable_self_growth(
    container_id: str,
    *,
    actor: str = "runtime",
    reason: Optional[str] = "enable self_growth",
    provided_key: Optional[str] = None,
) -> Dict[str, Any]:
    return set_flag(container_id, "self_growth", True, actor=actor, reason=reason, provided_key=provided_key)

def disable_self_growth(
    container_id: str,
    *,
    actor: str = "runtime",
    reason: Optional[str] = "disable self_growth",
    provided_key: Optional[str] = None,
) -> Dict[str, Any]:
    return set_flag(container_id, "self_growth", False, actor=actor, reason=reason, provided_key=provided_key)

# Optional helpers for growth tuning
def get_growth_factor(container_id: Optional[str]) -> int:
    try:
        gf = int(get_flags(container_id).get("growth_factor", 1))
        return max(1, min(gf, 12))
    except Exception:
        return 1

def set_growth_factor(
    container_id: str,
    value: int,
    *,
    actor: str = "runtime",
    reason: Optional[str] = "set growth_factor",
    provided_key: Optional[str] = None,
) -> Dict[str, Any]:
    value = max(1, min(int(value), 12))
    return set_flag(container_id, "growth_factor", value, actor=actor, reason=reason, provided_key=provided_key)

# ──────────────────────────────────────────────────────────────────────────────
# 🧩 Existing DNA Module Switch & Proposal Flow (kept, with minor refactors)
# ──────────────────────────────────────────────────────────────────────────────
class DNAModuleSwitch:
    def __init__(self):
        self.tracked_files: Dict[str, Dict[str, Any]] = {}

    def register(self, path: str, file_type: str = "backend") -> None:
        abs_path = os.path.abspath(path)
        if abs_path not in self.tracked_files:
            self.tracked_files[abs_path] = {
                "type": file_type,
                "registered_at": _utc_now(),
            }
            filename = os.path.basename(abs_path)
            if file_type == "backend":
                register_backend_path(name=filename, path=abs_path)
            elif file_type == "frontend":
                register_frontend_path(name=filename, path=abs_path)

    def list(self) -> Dict[str, Dict[str, Any]]:
        return self.tracked_files

    def list_versions(self, file: str):
        """List all saved versions for a given file."""
        return get_versions_for_file(file)

    def rollback_to_version(self, file: str, version_filename: str, provided_key: str):
        """
        Restore a given version snapshot into the target file.
        Only allowed if provided_key == MASTER_KEY (with env policy).
        """
        _require_key(provided_key)
        restore_version(file, version_filename)
        log_dna_switch({
            "action": "rollback",
            "file": file,
            "version_restored": version_filename,
            "timestamp": _utc_now()
        })

# ✅ Use proposal manager for secure mutation approval + replacement
def approve_proposal(proposal_id, provided_key):
    _require_key(provided_key)

    proposals = load_proposals()
    matched = None
    for proposal in proposals:
        if proposal["proposal_id"] == proposal_id:
            matched = proposal
            break

    if not matched:
        raise ValueError("Proposal not found.")

    # Mark as approved
    matched["approved"] = True
    save_proposals(proposals)

    # Apply the change
    file_path = get_module_path(matched["file"])

    # --- Save version snapshot BEFORE applying ---
    with open(file_path, "r", encoding="utf-8") as f:
        current_contents = f.read()
    save_version_snapshot(matched["file"], current_contents)

    # Read original contents for replacement
    contents = current_contents
    if matched["replaced_code"] not in contents:
        raise ValueError("Original code block not found in file.")

    updated = contents.replace(matched["replaced_code"], matched["new_code"])

    # Write modified version
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated)

    # Log and update
    log_dna_switch({
        "proposal_id": proposal_id,
        "file": file_path,
        "timestamp": _utc_now(),
        "status": "applied"
    })

    update_dna_proposal(proposal_id, {
        "approved": True,
        "applied_at": _utc_now(),
        "applied_successfully": True
    })

    return {"status": "applied", "file": matched["file"]}

# ✅ Manual DNA trigger for runtime executors (glyphs, dreams, etc.)
def register_dna_switch(proposal_id: str, new_code: str, file_path: str):
    success = apply_dna_switch(file_path, new_code)
    update_dna_proposal(proposal_id, {
        "approved": True,
        "applied_at": _utc_now(),
        "applied_successfully": success
    })

# ✅ Apply code directly and log it
def apply_dna_switch(file_path: str, new_code: str) -> bool:
    try:
        # Optional: backup before applying using dna_writer version snapshot
        with open(file_path, "r", encoding="utf-8") as f:
            current_contents = f.read()
        save_version_snapshot(file_path, current_contents)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_code)

        log_dna_switch({
            "file": file_path,
            "timestamp": _utc_now(),
            "status": "applied"
        })
        return True
    except Exception as e:
        print(f"❌ DNA switch failed for {file_path}: {e}")
        return False

def add_dna_mutation(from_glyph: dict, to_glyph: dict, reason: str = "pattern_recombination") -> bool:
    """
    Record a DNA mutation from one glyph to another with reason.
    Saves to dna_switch_log.json for audit, and creates a proposal.
    """
    mutation_entry = {
        "from": from_glyph,
        "to": to_glyph,
        "reason": reason,
        "timestamp": _utc_now()
    }

    # Save to switch log
    log_dna_switch({
        "action": "mutation",
        "mutation": mutation_entry
    })

    # Also propose as formal DNA mutation
    try:
        from backend.modules.dna_chain.dna_writer import propose_dna_mutation
        propose_dna_mutation(from_glyph, to_glyph, reason)
    except Exception as e:
        print(f"⚠️ Failed to propose DNA mutation: {e}")

    return True

# 🧠 Switch log for audit
def log_dna_switch(entry: dict):
    data = _read_json(DNA_SWITCH_LOG, {"log": []})
    if "log" not in data or not isinstance(data["log"], list):
        data["log"] = []
    data["log"].append(entry)
    _write_json(DNA_SWITCH_LOG, data)

# 🧠 Track Frontend Files (Optional)
def register_frontend(filepath: str):
    DNA_SWITCH.register(filepath, file_type="frontend")

def get_frontend_status():
    return {
        path: meta
        for path, meta in DNA_SWITCH.tracked_files.items()
        if meta.get("type") == "frontend"
    }

# ✅ DNA Switch Singleton
DNA_SWITCH = DNAModuleSwitch()

# ✅ Re-export symbolic mutation proposal function from dna_writer
from backend.modules.dna_chain.dna_writer import propose_dna_mutation
__all__ = [
    "DNAModuleSwitch",
    "approve_proposal",
    "register_dna_switch",
    "apply_dna_switch",
    "add_dna_mutation",
    "log_dna_switch",
    "register_frontend",
    "get_frontend_status",
    "DNA_SWITCH",
    "propose_dna_mutation",
    # Feature-flag (E1)
    "get_flags",
    "is_enabled",
    "set_flag",
    "is_self_growth_enabled",
    "enable_self_growth",
    "disable_self_growth",
    "get_growth_factor",
    "set_growth_factor",
]