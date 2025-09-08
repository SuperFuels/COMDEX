# File: backend/modules/dna_chain/container_index_writer.py

import datetime
import hashlib
import importlib
from typing import Dict, Any
from datetime import datetime
import uuid
import os
import json 

from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.websocket_manager import WebSocketManager

_soullaw_checked_ids = set()

def get_current_timestamp() -> str:
    return datetime.utcnow().isoformat()

def generate_uuid() -> str:
    return str(uuid.uuid4())

# ✅ WebSocket for live UI updates
ws_manager = WebSocketManager()

# ---------- CLI/Test fallback ----------
# In-memory UCS stub used when the real state_manager/ucs isn’t available.
_EPHEMERAL_UCS: Dict[str, Any] = {
    "active_container": {
        "id": "ucs_ephemeral",
        "glyph_grid": [],
        "indexes": {},
        "last_updated": None,
    },
    "_ephemeral": True,
}

# Local JSONL sink for CLI/test mirroring
_JSONL_MIRROR = "backend/data/knowledge_index.jsonl"

def _append_jsonl(index_name: str, entry: Dict[str, Any], path: str = _JSONL_MIRROR) -> None:
    """Mirror writes to a JSONL file for offline/CLI inspection."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rec = {
            "ts": datetime.utcnow().isoformat(),
            "index": index_name,
            "entry": entry,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        # Never fail the write because of the mirror
        print(f"⚠️ Index JSONL mirror failed: {e}")

# ✅ Lazy-load UCS to avoid circular import, with robust fallback
def _get_ucs():
    """
    Try several accessors on state_manager to fetch UCS.
    If unavailable (or method missing), return a safe ephemeral UCS stub so
    index writes still work in CLI/test mode.
    """
    try:
        sm = importlib.import_module("backend.modules.consciousness.state_manager")
    except Exception:
        return _EPHEMERAL_UCS

    # Try known accessors (be liberal across branches)
    for accessor in (
        "get_active_universal_container_system",
        "get_universal_container_system",
        "active_universal_container_system",
    ):
        fn = getattr(sm, accessor, None)
        if callable(fn):
            try:
                ucs = fn()
                if isinstance(ucs, dict):
                    # Ensure structure is present
                    ucs.setdefault("active_container", ucs.get("container", {}))
                    ac = ucs.get("active_container")
                    if isinstance(ac, dict):
                        ac.setdefault("indexes", {})
                    return ucs
            except Exception:
                # If calling the accessor fails, fall through to fallback
                break

    # Fallback UCS stub
    return _EPHEMERAL_UCS


def _get_or_create_index(container: Dict[str, Any], index_name: str):
    if "indexes" not in container:
        container["indexes"] = {}
    if index_name not in container["indexes"]:
        container["indexes"][index_name] = []
    return container["indexes"][index_name]


def _create_index_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    glyph_id = entry.get("id", generate_uuid())
    
    # Safely handle content: serialize if dict, leave as-is if str
    glyph_content = entry["content"]
    if isinstance(glyph_content, dict):
        glyph_content = json.dumps(glyph_content, sort_keys=True)

    glyph_hash = entry.get("hash", hashlib.sha256(glyph_content.encode()).hexdigest())
    timestamp = entry.get("timestamp", get_current_timestamp())

    return {
        "id": glyph_id,
        "hash": glyph_hash,
        "type": entry.get("type", "unknown"),
        "timestamp": timestamp,
        "tags": entry.get("metadata", {}).get("tags", []),
        "spatial": entry.get("spatial", None),
        "plugin": entry.get("plugin", None),
    }

def add_to_index(index_name: str, entry: Dict[str, Any]):
    """
    Adds a symbolic glyph entry to a container-level index,
    validates Knowledge Graph integrity, syncs UCS state, and emits updates.
    """
    ucs = _get_ucs()  # ✅ robust lazy fetch
    container = ucs.get("active_container", {})

    # ✅ Create or fetch the target index
    index = _get_or_create_index(container, index_name)
    index_entry = _create_index_entry(entry)
    index.append(index_entry)
    container["last_index_update"] = datetime.utcnow().isoformat()

    # ✅ Mirror to JSONL if running without a real UCS (CLI/test)
    if ucs is _EPHEMERAL_UCS or ucs.get("_ephemeral") is True:
        _append_jsonl(index_name, index_entry)

    # ✅ Knowledge Graph validation (Rubric check)
    try:
        from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
        kgw = kg_writer
        container["rubric_report"] = kgw.validate_knowledge_graph()
    except Exception as e:
        container["rubric_report_error"] = f"Failed to validate rubric: {str(e)}"

    # ✅ SoulLaw enforcement (lazy-import to prevent circular import)
    try:
        if os.getenv("SOUL_LAW_MODE", "full") != "test":  # ✅ Skip in test mode
            from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator
            soul_law = get_soul_law_validator()

            # Use a stable key to dedupe checks
            cid = container.get("id") or container.get("name")
            if cid and cid not in _soullaw_checked_ids:
                if not soul_law.validate_container(container):
                    raise PermissionError(f"SoulLaw: container {cid} failed validation.")
                _soullaw_checked_ids.add(cid)
    except Exception as e:
        container["soul_law_error"] = f"SoulLaw validation failed: {e}"

    # ✅ UCS runtime sync (persist updated state) — skip in ephemeral mode
    try:
        if not (ucs is _EPHEMERAL_UCS or ucs.get("_ephemeral") is True):
            cid = container.get("id") or "unknown_container"
            ucs_runtime.save_container(cid, container)
            print(f"📥 UCS Sync: Saved updated container state for {cid}")
    except Exception as e:
        print(f"⚠️ UCS sync failed: {e}")

    # ✅ GHX visualization log (guard)
    try:
        cid = container.get("id") or "unknown_container"
        if hasattr(ucs_runtime, "visualizer") and getattr(ucs_runtime, "visualizer"):
            ucs_runtime.visualizer.log_event(cid, f"Index updated: {index_name}")
    except Exception as e:
        print(f"⚠️ GHX visualization logging failed: {e}")

    # ✅ WebSocket broadcast for live index updates (guard)
    try:
        if hasattr(ws_manager, "broadcast"):
            import asyncio
            asyncio.create_task(ws_manager.broadcast({
                "type": "index_update",
                "data": {
                    "container_id": container.get("id"),
                    "index_name": index_name,
                    "entry": index_entry,
                    "timestamp": get_current_timestamp()
                }
            }))
    except Exception as e:
        print(f"⚠️ WS broadcast skipped: {e}")

    # ✅ Emit SQI event (index type aware)
    try:
        event_type = f"{index_name}_entry_added"
        from backend.modules.sqi.sqi_event_bus import emit_sqi_event
        emit_sqi_event(event_type, payload={"container_id": container.get("id"), "entry": index_entry})
    except ImportError:
        pass


def add_goal_entry(goal_str: str, source: str = "memory"):
    """
    Adds a symbolic goal entry into the goal index.
    """
    ucs = _get_ucs()
    container = ucs.get("active_container", {})
    goal_id = generate_uuid()

    entry = {
        "id": goal_id,
        "type": "goal",
        "content": goal_str,
        "timestamp": get_current_timestamp(),
        "metadata": {
            "source": source,
            "tags": ["goal"],
        }
    }
    add_to_index("goal_index", entry)
    return goal_id

def get_active_container_ids() -> list:
    """
    Returns a list of currently active container IDs.
    In practice, this often contains just one container.
    """
    ucs = _get_ucs()
    container = ucs.get("active_container", {})
    cid = container.get("id")
    return [cid] if cid else []

def add_dream_entry(dream_str: str, category: str = "vision"):
    """
    Adds a dream entry (used in replay/forecast logic).
    """
    ucs = _get_ucs()
    container = ucs.get("active_container", {})
    dream_id = generate_uuid()

    entry = {
        "id": dream_id,
        "type": "dream",
        "content": dream_str,
        "timestamp": get_current_timestamp(),
        "metadata": {
            "category": category,
            "tags": ["dream"],
        }
    }
    add_to_index("dream_index", entry)
    return dream_id


def add_failure_entry(reason: str, caused_by: str = "unknown"):
    """
    Adds a failure entry for error analysis and mutation.
    """
    ucs = _get_ucs()
    container = ucs.get("active_container", {})
    failure_id = generate_uuid()

    entry = {
        "id": failure_id,
        "type": "failure",
        "content": reason,
        "timestamp": get_current_timestamp(),
        "metadata": {
            "cause": caused_by,
            "tags": ["failure"],
        }
    }
    add_to_index("failure_index", entry)
    return failure_id

def add_innovation_score_entry(wave_id: str, parent_wave_id: str, score: float, glow: float, pulse: float, cause: str):
    """
    Adds an innovation score entry to the container index for replay or HUD rendering.
    """
    entry = {
        "id": generate_uuid(),
        "type": "innovation_score",
        "content": {
            "wave_id": wave_id,
            "parent_wave_id": parent_wave_id,
            "score": score,
            "glow": glow,
            "pulse": pulse,
            "cause": cause,
        },
        "timestamp": get_current_timestamp(),
        "metadata": {
            "tags": ["innovation", "score", "fork"],
            "origin": "creative_core"
        }
    }
    add_to_index("innovation_index", entry)
    return entry["id"]

def add_gwv_trace_entry(trace_str: str, container_id: str = None):
    """
    Injects a symbolic collapse/decoherence replay trace (GWV) into the container as a 'trace' entry.
    This is used to persist symbolic runtime data inside `.dc.json` containers.
    """
    trace_id = generate_uuid()

    entry = {
        "id": trace_id,
        "type": "trace",
        "content": trace_str,
        "timestamp": get_current_timestamp(),
        "metadata": {
            "tags": ["gwv", "replay", "collapse", "decoherence"],
        }
    }
    add_to_index("trace_index", entry)
    return trace_id