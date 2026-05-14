# File: backend/modules/knowledge_graph/knowledge_bus_adapter.py

from __future__ import annotations
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import os
import textwrap

from backend.modules.knowledge_graph.indexes.knowledge_index import knowledge_index

# ---- Config -----------------------------------------------------------------

DEFAULT_GLYPH_PATH = os.getenv(
    "KNOWLEDGE_GLYPH_PATH",
    # runtime-safe mirror; adjust if you want it next to the static doc
    "backend/modules/knowledge_graph/knowledge_index_runtime.glyph",
)

# ---- Public API --------------------------------------------------------------

def ingest_bus_event(
    payload: Dict[str, Any],
    *,
    persist_glyph: bool = True,
    glyph_path: Optional[str] = None,
    ghx_logger: Optional[object] = None,
) -> bool:
    """
    Normalize an incoming SQI/GlyphNet event into KnowledgeIndex and (optionally) append to a .glyph file.

    Expected payload (based on your logs):
      {
        "container_id": "ucs_ephemeral",
        "entry": {
          "id": "...",
          "hash": "9b12...d33e",
          "type": "approval" | "drift_report" | ...,
          "timestamp": "2025-08-07T23:29:38.66...",
          "tags": ["📜","🧠","✅"],
          "plugin": null | "some_plugin",
          "source": "glyph_executor" | "MemoryEngine" | ...
        },
        "origin": "sqi_bus" | "glyphnet_ws" | ...
      }

    Returns True if a new entry was added (not a duplicate), False otherwise.
    """

    cid = payload.get("container_id") or "unknown"
    entry: Dict[str, Any] = payload.get("entry", {}) or {}

    # --- map bus payload to KnowledgeIndex kwargs (your requested block) -----
    glyph        = entry.get("glyph", "")          # or whatever your upstream provides
    meaning      = entry.get("meaning", "")        # "
    tags         = entry.get("tags", []) or []
    source       = entry.get("type", "bus")        # use bus event type as source
    container_id = cid
    confidence   = float(entry.get("confidence", 1.0))
    plugin       = entry.get("plugin")
    anchor       = entry.get("anchor")

    kwargs = {
        "glyph": glyph,
        "meaning": meaning,
        "tags": tags,
        "source": source,
        "container_id": container_id,
        "confidence": confidence,
        "plugin": plugin,
        "anchor": anchor,
        # ↓ important for idempotency + relation linking
        "external_hash": entry.get("hash"),
        "timestamp": entry.get("timestamp") or _utc_now_iso(),
    }

    # Try to insert idempotently. If KnowledgeIndex supports external_hash+timestamp,
    # use it; otherwise gracefully fall back to legacy signature.
    added = _safe_add_to_index(**kwargs)

    # If event includes relations, link them (safe no-op if missing)
    _maybe_link_relations(entry, external_hash=kwargs.get("external_hash"))

    # Soft GHX log (avoid the AttributeError spam)
    if ghx_logger is not None:
        _safe_ghx_log(ghx_logger, {
            "t": "knowledge_index.ingest",
            "container_id": cid,
            "hash": kwargs.get("external_hash"),
            "type": source,
            "added": added,
            "timestamp": kwargs["timestamp"],
            "tags": tags,
            "source": source,
        })

    # Optional .glyph persistence (append-only, human-readable)
    if added and persist_glyph:
        _append_glyph_file(
            glyph_path or DEFAULT_GLYPH_PATH,
            glyph=glyph or source,              # if no glyph string, keep it readable
            meaning=meaning or f"KG event: {source}",
            tags=tags,
            confidence=confidence,
            source=source,
            container_id=cid,
            timestamp=kwargs["timestamp"],
        )

    return added


# ---- Internals ---------------------------------------------------------------

def _safe_add_to_index(**kwargs) -> bool:
    """
    Calls knowledge_index.add_entry with the new signature; if that TypeErrors (older class),
    falls back to the legacy call (no external_hash/timestamp).
    Returns True if inserted, False if deduped.
    """
    try:
        # New/extended signature (adds external_hash, timestamp)
        return bool(knowledge_index.add_entry(**kwargs))
    except TypeError:
        # Legacy KnowledgeIndex: drop unsupported fields and rely on old dedupe.
        legacy_fields = {
            k: kwargs[k]
            for k in ("glyph","meaning","tags","source","container_id","confidence","plugin","anchor")
            if k in kwargs
        }
        return bool(knowledge_index.add_entry(**legacy_fields))


def _maybe_link_relations(entry: dict, external_hash: Optional[str]) -> None:
    """
    If the bus payload carried relation info, create a link from this entry's hash
    to the provided related hashes. Silent on failure.
    """
    try:
        from backend.modules.knowledge_graph.indexes.knowledge_index import knowledge_index as _ki
    except Exception:
        return

    meta = (entry or {}).get("meta") or {}
    relates = meta.get("relates_to") or []
    my_hash = external_hash or entry.get("hash")
    if not my_hash or not relates:
        return

    relation = meta.get("relation", "relates_to")
    for other_hash in relates:
        try:
            if hasattr(_ki, "add_link"):
                _ki.add_link(my_hash, other_hash, relation=relation)
        except Exception:
            # never let relations break ingest
            pass


def _infer_source_from_container(container_id: str) -> Optional[str]:
    cid = (container_id or "").lower()
    if not cid:
        return None
    if "replay" in cid or "codex" in cid:
        return "CodexCore"
    if "seed" in cid or "glyph" in cid:
        return "glyph_executor"
    if "memory" in cid:
        return "MemoryEngine"
    return None


def _infer_confidence(evt_type: str, tags: list) -> float:
    t = (evt_type or "").lower()
    # Simple sane defaults; tune as needed
    if t == "approval":
        base = 0.90
    elif t in {"proof", "assertion"}:
        base = 0.88
    elif t in {"drift_report", "warning"}:
        base = 0.65
    else:
        base = 0.80

    if "✅" in tags:
        base += 0.05
    if "⚠️" in tags:
        base -= 0.10
    return max(0.0, min(1.0, base))


def _safe_ghx_log(ghx_logger: object, event: dict) -> None:
    """
    Attempt a best-effort GHX HUD/event trace without blowing up if the
    visualizer lacks a method.
    """
    try:
        if hasattr(ghx_logger, "log_event") and callable(getattr(ghx_logger, "log_event")):
            ghx_logger.log_event(event)
        elif hasattr(ghx_logger, "append") and callable(getattr(ghx_logger, "append")):
            ghx_logger.append(event)
        elif hasattr(ghx_logger, "publish") and callable(getattr(ghx_logger, "publish")):
            ghx_logger.publish(event)
        else:
            pass
    except Exception:
        # Never let GHX logging break ingestion
        pass


def _append_glyph_file(path: str, **fields) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    block = _format_glyph_block(**fields)
    with open(path, "a", encoding="utf-8") as f:
        f.write(block)


def _format_glyph_block(
    *,
    glyph: str,
    meaning: str,
    tags: list,
    confidence: float,
    source: str,
    container_id: str,
    timestamp: str,
) -> str:
    # Keep it aligned with your .glyph file style
    tag_list = ", ".join(tags) if tags else ""
    return textwrap.dedent(f"""
    - ⟦ Glyph ⟧: {glyph}
      ⟦ Meaning ⟧: {meaning}
      ⟦ Tags ⟧: [{tag_list}]
      ⟦ Confidence ⟧: {confidence:.2f}
      ⟦ Source ⟧: {source}
      ⟦ Container ⟧: {container_id}
      ⟦ Timestamp ⟧: ⌛ {timestamp}
    """).lstrip()


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"