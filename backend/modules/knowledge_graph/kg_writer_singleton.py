# /workspaces/COMDEX/backend/modules/knowledge_graph/kg_writer_singleton.py
from __future__ import annotations

import importlib
import json
import os
import traceback
import logging
from typing import Any, Callable, Optional, Dict

log = logging.getLogger("kg_writer_singleton")

# 🧠 Singleton holder for the KnowledgeGraphWriter instance
_kg_writer_instance: Optional[Any] = None
_KG_WRITER_CLASS: Optional[Callable[[], Any]] = None  # Lazy-loaded class reference
_build_tree_from_container = None  # Lazy-imported symbolic tree builder
_export_tree_to_kg = None  # Lazy-imported KG writer method

# ✅ Direct reference to the real GlyphVault Manager (not container_runtime)
try:
    from backend.modules.glyphvault.vault_manager import VAULT
    log.info("🔗 [kg_writer_singleton] VAULT bound to glyphvault.vault_manager.VAULT")
except Exception as e:
    VAULT = None
    log.warning("[kg_writer_singleton] ⚠️ Could not import VAULT from glyphvault.vault_manager: %s", e)

# --------------------------------------------------------------------
# Compat wrapper
# --------------------------------------------------------------------
_KG_COMPAT_ENABLED = os.getenv("AION_KG_COMPAT", "1") not in {"0", "false", "no", "off"}


def _attach_compat(writer: Any) -> Any:
    """
    Attach back-compat methods to the KG writer instance so older modules
    calling `log_event()` / `append_entry()` don't spam prints or break.

    These map to `inject_glyph()` when available.
    """
    if not _KG_COMPAT_ENABLED or writer is None:
        return writer

    def _has(name: str) -> bool:
        return hasattr(writer, name) and callable(getattr(writer, name))

    # Prefer inject_glyph as the canonical new API
    has_inject = _has("inject_glyph")

    if not _has("log_event"):
        def log_event(event_type: str = "event", payload: Optional[Dict[str, Any]] = None, **kwargs) -> bool:
            if not has_inject:
                return False
            try:
                meta = {"event_type": event_type}
                if payload and isinstance(payload, dict):
                    meta.update(payload)
                meta.update(kwargs)

                writer.inject_glyph(
                    content=json.dumps(payload or kwargs, default=str),
                    glyph_type="kg_event",
                    metadata=meta,
                    plugin="KGCompat",
                )
                return True
            except Exception as e:
                log.debug("[KGCompat] log_event failed: %s", e)
                return False

        writer.log_event = log_event  # type: ignore[attr-defined]

    if not _has("append_entry"):
        def append_entry(entry: Dict[str, Any], **kwargs) -> bool:
            if not has_inject:
                return False
            if not isinstance(entry, dict):
                return False
            try:
                meta = dict(entry)
                meta.update(kwargs)
                writer.inject_glyph(
                    content=json.dumps(entry, default=str),
                    glyph_type=str(entry.get("type", "kg_entry")),
                    metadata=meta,
                    plugin="KGCompat",
                )
                return True
            except Exception as e:
                log.debug("[KGCompat] append_entry failed: %s", e)
                return False

        writer.append_entry = append_entry  # type: ignore[attr-defined]

    return writer


# ────────────────────────────────────────────────────────────────
def get_kg_writer() -> Any:
    """
    Lazily initializes and returns the singleton KnowledgeGraphWriter instance.
    This avoids circular import issues by delaying class resolution until needed.

    Also attaches compat methods (log_event/append_entry) to prevent spam
    and keep legacy callers working.
    """
    global _kg_writer_instance, _KG_WRITER_CLASS

    if _kg_writer_instance is not None:
        return _kg_writer_instance

    try:
        if _KG_WRITER_CLASS is None:
            module = importlib.import_module("backend.modules.knowledge_graph.knowledge_graph_writer")
            if not hasattr(module, "KnowledgeGraphWriter"):
                raise ImportError("[kg_writer_singleton] ❌ 'KnowledgeGraphWriter' class not found in module.")
            _KG_WRITER_CLASS = getattr(module, "KnowledgeGraphWriter")

        _kg_writer_instance = _KG_WRITER_CLASS()
        _kg_writer_instance = _attach_compat(_kg_writer_instance)
        return _kg_writer_instance

    except Exception as e:
        trace = "".join(traceback.format_stack(limit=10))
        raise RuntimeError(
            f"[kg_writer_singleton] ❌ Failed to initialize KnowledgeGraphWriter: {e}\n"
            f"[kg_writer_singleton] 📍 Stack Trace:\n{trace}"
        )


# ────────────────────────────────────────────────────────────────
def get_strategy_planner_kg_writer() -> Any:
    """🔁 Alias for get_kg_writer(), used in StrategyPlanner and other contexts."""
    return get_kg_writer()


# ────────────────────────────────────────────────────────────────
def write_glyph_event(*args, **kwargs) -> None:
    """
    Back/forward compatible proxy to knowledge_graph_writer.write_glyph_event.

    Supports BOTH call styles:

    A) Legacy:
        write_glyph_event(event_type: str, event: dict, container_id: Optional[str]=None)

    B) Newer:
        write_glyph_event(container_id=..., glyph=..., event_type=..., metadata=...)

    It will adapt to whichever signature the underlying knowledge_graph_writer exposes.
    """
    # --- normalize inputs from multiple calling conventions -----------------
    event_type = kwargs.pop("event_type", None)
    container_id = kwargs.pop("container_id", None)

    event = kwargs.pop("event", None)
    glyph = kwargs.pop("glyph", None)
    metadata = kwargs.pop("metadata", None)
    meta = kwargs.pop("meta", None)

    # positional support:
    #   (event_type, event, container_id=None)
    if event_type is None and len(args) >= 1:
        event_type = args[0]
    if event is None and len(args) >= 2 and isinstance(args[1], dict):
        event = args[1]
    if container_id is None and len(args) >= 3:
        container_id = args[2]

    # build event from glyph/metadata if needed
    if event is None and glyph is not None:
        event = {
            "glyph": glyph,
            "metadata": metadata if metadata is not None else (meta if meta is not None else {}),
        }
        if kwargs:
            event.update(kwargs)
        kwargs = {}

    if not isinstance(event_type, str) or not event_type.strip():
        raise ValueError("[kg_writer_singleton] write_glyph_event: missing/invalid event_type")
    if event is None or not isinstance(event, dict):
        raise ValueError("[kg_writer_singleton] write_glyph_event: missing/invalid event payload (dict)")

    # --- dispatch to underlying writer --------------------------------------
    try:
        module = importlib.import_module("backend.modules.knowledge_graph.knowledge_graph_writer")
        real_writer = getattr(module, "write_glyph_event", None)
        if real_writer is None:
            raise ImportError("write_glyph_event function not found in knowledge_graph_writer module.")

        varnames = getattr(getattr(real_writer, "__code__", None), "co_varnames", ())

        # Case 1: underlying wants (event_type, event, container_id[, vault])
        if "event" in varnames and "event_type" in varnames:
            call = {"event_type": event_type, "event": event, "container_id": container_id}
            if "vault" in varnames:
                call["vault"] = VAULT
            return real_writer(**call)

        # Case 2: underlying wants (container_id, glyph, event_type, metadata[, vault])
        if "glyph" in varnames and "metadata" in varnames:
            call = {
                "container_id": container_id,
                "glyph": event.get("glyph"),
                "event_type": event_type,
                "metadata": event.get("metadata", {}),
            }
            if "vault" in varnames:
                call["vault"] = VAULT
            return real_writer(**call)

        # Last resort: try old-style call first, then fallback to new-style call
        try:
            if "vault" in varnames:
                return real_writer(event_type=event_type, event=event, container_id=container_id, vault=VAULT)
            return real_writer(event_type=event_type, event=event, container_id=container_id)
        except TypeError:
            if "vault" in varnames:
                return real_writer(
                    container_id=container_id,
                    glyph=event.get("glyph"),
                    event_type=event_type,
                    metadata=event.get("metadata", {}),
                    vault=VAULT,
                )
            return real_writer(
                container_id=container_id,
                glyph=event.get("glyph"),
                event_type=event_type,
                metadata=event.get("metadata", {}),
            )

    except Exception as e:
        trace = "".join(traceback.format_stack(limit=10))
        log.error(
            "[kg_writer_singleton] ❌ Failed to call write_glyph_event: %s\n[kg_writer_singleton] 📍 Stack Trace:\n%s",
            e,
            trace,
        )
        raise


# ────────────────────────────────────────────────────────────────
def get_glyph_trace_for_container(container_id: str) -> dict:
    """
    Proxy passthrough to get_glyph_trace_for_container() in knowledge_graph_writer module.
    Used by HolographicSymbolTree and related systems.
    """
    try:
        module = importlib.import_module("backend.modules.knowledge_graph.knowledge_graph_writer")
        real_func = getattr(module, "get_glyph_trace_for_container", None)
        if real_func is None:
            raise ImportError("get_glyph_trace_for_container not found in knowledge_graph_writer module.")
        return real_func(container_id)
    except Exception as e:
        trace = "".join(traceback.format_stack(limit=10))
        raise RuntimeError(
            f"[kg_writer_singleton] ❌ Failed to call get_glyph_trace_for_container: {e}\n"
            f"[kg_writer_singleton] 📍 Stack Trace:\n{trace}"
        )


# ────────────────────────────────────────────────────────────────
def export_symbol_tree_if_enabled(container_id: str) -> None:
    """
    🌳 Lazy-proxy to build and export the symbolic meaning tree.
    This avoids import loops by loading build_tree_from_container only when called.
    """
    global _build_tree_from_container, _export_tree_to_kg
    try:
        if _build_tree_from_container is None:
            from backend.modules.symbolic.symbol_tree_generator import build_tree_from_container
            _build_tree_from_container = build_tree_from_container

        if _export_tree_to_kg is None:
            from backend.modules.knowledge_graph.knowledge_graph_writer import export_tree_to_kg
            _export_tree_to_kg = export_tree_to_kg

        tree = _build_tree_from_container(container_id)
        _export_tree_to_kg(tree)

        log.info("[🌳] Symbolic Tree auto-exported for container: %s", container_id)

    except Exception as e:
        log.warning("[kg_writer_singleton] ⚠️ Failed to export symbolic tree for %s: %s", container_id, e)


# ────────────────────────────────────────────────────────────────
def get_crdt_registry() -> Optional[Any]:
    """Returns the CRDT registry from the KnowledgeGraphWriter instance."""
    try:
        writer = get_kg_writer()
        return getattr(writer, "crdt_registry", None)
    except Exception as e:
        log.warning("[kg_writer_singleton] ⚠️ Could not access crdt_registry: %s", e)
        return None


# ────────────────────────────────────────────────────────────────
__all__ = [
    "get_kg_writer",
    "get_strategy_planner_kg_writer",
    "write_glyph_event",
    "get_glyph_trace_for_container",
    "get_crdt_registry",
    "export_symbol_tree_if_enabled",
]