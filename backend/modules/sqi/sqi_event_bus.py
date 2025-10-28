# -*- coding: utf-8 -*-
"""
SQI Event Bus
=============
Manages emission of SQI (Symbolic Quantum Interface) events to GPIO pins or simulated outputs.
Integrates with Raspberry Pi GPIO for hardware signaling, while providing a fallback simulation
mode when running off-Pi (e.g., dev environment).

Additions in this version:
    • Env-based logging controls (AION_LOG_LEVEL)
    • Toggle simulated broadcast spam (AION_SQI_SIM_BROADCAST)
    • Burst-debounce + idempotent guard for knowledge_index.glyph_entry_added
    • publish_kg_added(payload) convenience publisher (drops dupes)
    • Safe wiring to KnowledgeIndex via knowledge_bus_adapter.ingest_bus_event
    • Relation linking: if payload.entry.meta.relates_to is provided, create KG edges
"""
import os

SILENT = os.getenv("AION_SILENT_MODE", "0") == "1"
import os
import time
import threading
from collections import OrderedDict
from typing import Dict, Callable, Optional

from datetime import datetime
from backend.modules.codex.codex_metrics import record_sqi_score_event
from backend.modules.knowledge_graph.kg_writer_singleton import write_glyph_event
from backend.modules.symbolic.symbolic_broadcast import broadcast_glyph_event
from backend.modules.sqi import sqi_event_bus_gw


# -----------------------------------------------------------------------------
# Environment flags
# -----------------------------------------------------------------------------
import os, sys, time, json
from typing import Optional, Dict, Any
from collections import OrderedDict

SIM_BROADCAST = os.getenv("AION_SQI_SIM_BROADCAST", "1") == "1"
ENABLE_WS_BROADCAST = os.getenv("AION_ENABLE_WS_BROADCAST", "1") == "1"

# logging config
_LOG_LEVEL = (os.getenv("AION_LOG_LEVEL", "info") or "info").lower()
_LOG_JSON  = os.getenv("AION_LOG_JSON", "0") == "1"          # structured logs
_LOG_TS    = os.getenv("AION_LOG_TS", "1") == "1"            # prefix human timestamp if not JSON
_LOG_SRC   = os.getenv("AION_LOG_SOURCE", "1") == "1"        # include "src" field

# spam control
_DEBOUNCE_MS_DEFAULT = int(os.getenv("AION_LOG_DEBOUNCE_MS", "150"))  # per-key
_SAMPLE_RATE         = float(os.getenv("AION_LOG_SAMPLE_RATE", "1.0"))  # 0..1 probabilistic

_LEVELS = {"debug": 10, "info": 20, "warn": 30, "warning": 30, "error": 40}

# LRU-ish store for recent log keys
_recent_log: "OrderedDict[str, float]" = OrderedDict()
_RECENT_MAX = 4096

def _should_log(level: str) -> bool:
    return _LEVELS.get(level, 20) >= _LEVELS.get(_LOG_LEVEL, 20)

def _maybe_drop_by_key(key: Optional[str], debounce_ms: Optional[int]) -> bool:
    """Return True if this log should be dropped due to recent duplicate."""
    if not key or not debounce_ms or debounce_ms <= 0:
        return False
    now = time.time() * 1000.0
    last = _recent_log.get(key)
    if last is not None and (now - last) < debounce_ms:
        return True
    _recent_log[key] = now
    # trim oldest to keep memory bounded
    while len(_recent_log) > _RECENT_MAX:
        _recent_log.popitem(last=False)
    return False

def _fmt_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

def _emit(payload: str):
    # Single write to stdout; change to stderr if you prefer
    sys.stdout.write(payload + ("\n" if not payload.endswith("\n") else ""))
    sys.stdout.flush()

def _log(
    level: str,
    msg: str,
    *,
    src: Optional[str] = None,
    key: Optional[str] = None,
    debounce_ms: Optional[int] = None,
    data: Optional[Dict[str, Any]] = None,
):
    """
    Structured log with optional debounce and JSON formatting.

    level:  "debug" | "info" | "warn" | "error"
    src:    freeform string (module/function)
    key:    dedupe key; messages with same key within debounce_ms are dropped
    debounce_ms: override global debounce; set 0/None to disable for this line
    data:   extra fields merged into JSON logs
    """
    if not _should_log(level):
        return
    # sampling
    if _SAMPLE_RATE < 1.0:
        import random
        if random.random() > _SAMPLE_RATE:
            return
    # debounce
    if _maybe_drop_by_key(key, debounce_ms if debounce_ms is not None else _DEBOUNCE_MS_DEFAULT):
        return

    if _LOG_JSON:
        record = {
            "ts": _fmt_now(),
            "level": level,
            "msg": msg,
        }
        if _LOG_SRC and src:
            record["src"] = src
        if data:
            # avoid clobbering keys
            record["data"] = data
        _emit(json.dumps(record, ensure_ascii=False))
    else:
        parts = []
        if _LOG_TS:
            parts.append(_fmt_now())
        parts.append(level.upper())
        if _LOG_SRC and src:
            parts.append(f"[{src}]")
        parts.append(msg)
        _emit(" ".join(parts))

# Convenience wrappers
def log_debug(msg: str, **kw):  _log("debug", msg, **kw)
def log_info(msg: str, **kw):   _log("info", msg, **kw)
def log_warn(msg: str, **kw):   _log("warn", msg, **kw)
def log_error(msg: str, **kw):  _log("error", msg, **kw)

# -----------------------------------------------------------------------------
# Optional KG adapter wiring
# -----------------------------------------------------------------------------
try:
    # Ingests bus payloads into KnowledgeIndex with external_hash idempotency
    from backend.modules.knowledge_graph.knowledge_bus_adapter import ingest_bus_event
    _KG_ADAPTER_AVAILABLE = True
except Exception as _e:
    ingest_bus_event = None  # type: ignore
    _KG_ADAPTER_AVAILABLE = False
    _log("warn", f"⚠️ SQI: Knowledge bus adapter not available ({_e}). KG ingest will be skipped.")

# -----------------------------------------------------------------------------
# GPIO detection + Hyperdrive Safety integration
# -----------------------------------------------------------------------------
import os
import importlib

FORCE_HARDWARE_MODE = os.getenv("AION_FORCE_HARDWARE", "1") == "1"

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)  # BCM pin numbering
    GPIO_AVAILABLE = True
    _log("info", "✅ SQI: Raspberry Pi GPIO detected — hardware mode enabled.")
except Exception as gpio_error:
    GPIO = None
    # Do NOT mark available if GPIO import failed
    GPIO_AVAILABLE = False
    if FORCE_HARDWARE_MODE:
        _log("warn", f"⚠️ SQI: GPIO not detected ({gpio_error}), but hardware mode forced by env. "
                     "Running in simulated hardware mode.")
    else:
        _log("warn", f"⚠️ SQI: No GPIO module detected — running in simulation mode. ({gpio_error})")

# ──────────────────────────────────────────────
#  Safe-guard any GPIO access
# ──────────────────────────────────────────────
def safe_gpio_setup(pin: int, mode: int):
    """Safely set up GPIO pin if available, otherwise skip."""
    if GPIO_AVAILABLE and GPIO is not None:
        try:
            GPIO.setup(pin, mode)
        except Exception as e:
            _log("warn", f"⚠️ GPIO setup failed for pin {pin}: {e}")
    else:
        _log("debug", f"💡 Skipping GPIO setup for pin {pin} (simulation mode).")

# -----------------------------------------------------------------------------
# Hyperdrive Safety Hook (only fires if real or simulated hardware mode)
# -----------------------------------------------------------------------------
if FORCE_HARDWARE_MODE or GPIO_AVAILABLE:
    try:
        hyperdrive = importlib.import_module("backend.modules.hyperdrive.hyperdrive_safety")
        if hasattr(hyperdrive, "initialize_hyperdrive_guard"):
            hyperdrive.initialize_hyperdrive_guard()
            _log("info", "🛡️ Hyperdrive safety guard engaged (hardware or simulated mode).")
        else:
            _log("debug", "ℹ️ Hyperdrive safety module found, but no guard init function defined.")
    except ModuleNotFoundError:
        _log("debug", "ℹ️ No hyperdrive_safety module detected — skipping safety guard.")
    except Exception as hyper_err:
        _log("warn", f"⚠️ Failed to initialize Hyperdrive safety guard: {hyper_err}")

# -----------------------------------------------------------------------------
# Defaults & registries
# -----------------------------------------------------------------------------
DEFAULT_PINS = {
    "container_growth": 17,
    "glyph_injection": 27,
    "entropy_pulse": 22,
    "heartbeat": 5,
}

# Event listeners registry (str -> list[callable])
event_listeners: Dict[str, list[Callable[[dict], None]]] = {}

# Debounce / Idempotency for KG events
_DEDUPE = OrderedDict()     # (container_id, external_hash) -> last_ms
_DEBOUNCE_MS = int(os.getenv("AION_SQI_DEBOUNCE_MS", "150"))  # collapse storms within this window
_MAX_CACHE = int(os.getenv("AION_SQI_DEDUPE_CACHE", "4096"))  # LRU-ish cap

def _recent_kg(cid: Optional[str], h: Optional[str]) -> bool:
    """
    True  -> duplicate/burst within debounce window; drop
    False -> first-seen or outside window; allow
    """
    if not cid or not h:
        return False
    now = time.time() * 1000
    key = (cid, h)
    last = _DEDUPE.get(key)
    if last and (now - last) < _DEBOUNCE_MS:
        return True
    _DEDUPE[key] = now
    # trim oldest
    if len(_DEDUPE) > _MAX_CACHE:
        _DEDUPE.popitem(last=False)
    return False
# -----------------------------------------------------------------------------
# Listener registration
# -----------------------------------------------------------------------------
def register_event_listener(event_type: str, callback: Callable[[dict], None]) -> None:
    """Register a listener function for a given SQI event."""
    if event_type not in event_listeners:
        event_listeners[event_type] = []
    event_listeners[event_type].append(callback)
    _log("debug", f"🔗 SQI listener registered for event: {event_type}")

# -----------------------------------------------------------------------------
# Low-level GPIO pulse
# -----------------------------------------------------------------------------
def _pulse_pin(pin: int, duration: float = 0.1) -> None:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(pin, GPIO.LOW)

# -----------------------------------------------------------------------------
# Core emitter
# -----------------------------------------------------------------------------
def emit_sqi_event(event_type: str, payload: Optional[dict] = None) -> None:
    """
    Emit an SQI event, pulsing GPIO (if available) and notifying listeners.
    """
    payload = payload or {}
    if not SILENT:
        _log("info", f"[SQI Event] {event_type} | Payload: {payload}")

    # Hardware pulse or simulated notice
    if GPIO_AVAILABLE and event_type in DEFAULT_PINS:
        pin = DEFAULT_PINS[event_type]
        threading.Thread(target=_pulse_pin, args=(pin,), daemon=True).start()
    elif not GPIO_AVAILABLE and SIM_BROADCAST:
        _log("warn", f"⚠️ SQI simulated pulse → Event: {event_type}")

    # Notify listeners
    if event_type in event_listeners:
        for callback in list(event_listeners[event_type]):
            try:
                callback(payload)
            except Exception as e:
                _log("warn", f"⚠️ SQI listener error for {event_type}: {e}")

# -----------------------------------------------------------------------------
# High-level publishers
# -----------------------------------------------------------------------------
def publish_kg_added(payload: dict) -> bool:
    """
    Publish 'knowledge_index.glyph_entry_added' with burst debounce + idempotency.
    Returns:
        True  if event was published (or considered successfully handled)
        False if dropped as a recent duplicate
    Expected payload shape (from upstream SQI/GlyphNet):
        {
          "container_id": "...",
          "entry": {
            "id": "...",
            "hash": "...",        # <-- external idempotency key
            "type": "approval"|"drift_report"|...,
            "timestamp": "...",
            "tags": [...],
            "plugin": None|"...",
            "meta": { "relates_to": [ "<other-hash>", ... ], "relation": "relates_to" }
          }
        }
    """
    cid = payload.get("container_id")
    h   = (payload.get("entry") or {}).get("hash")

    if _recent_kg(cid, h):
        # Duplicate within debounce window; treat as no-op success to keep callers simple
        return False

    # Emit on the bus so any listeners (including KG ingest) get it
    emit_sqi_event("knowledge_index.glyph_entry_added", payload)
    return True

# -----------------------------------------------------------------------------
# Optional: auto-wire KG ingest as a listener
# -----------------------------------------------------------------------------
def _kg_ingest_listener(payload: dict) -> None:
    """
    Listener that normalizes & writes into KnowledgeIndex (via adapter when available),
    then links relations declared in payload.entry.meta.relates_to.
    Safe no-op if adapter missing.
    """
    entry = (payload or {}).get("entry") or {}
    try:
        if _KG_ADAPTER_AVAILABLE and ingest_bus_event is not None:
            # Delegate to adapter
            _ = ingest_bus_event(payload, ghx_logger=None)

            # 🔗 Link relations even when adapter handled the insert.
            # We use the bus' external hash (entry['hash']) as 'my' node id.
            _maybe_link_relations(entry, external_hash=entry.get("hash"))
        else:
            # Fallback inline ingest: add to KnowledgeIndex here and then link
            stored = _safe_add_to_index_from_bus(payload)
            # 🔗 Link KG nodes if this entry declares relations
            meta = (entry or {}).get("meta") or {}
            relates = meta.get("relates_to") or []
            my_hash = (stored or {}).get("_hash") if isinstance(stored, dict) else None
            my_hash = my_hash or entry.get("hash")
            for other_hash in relates:
                try:
                    from backend.modules.knowledge_graph.indexes.knowledge_index import knowledge_index
                    knowledge_index.add_link(my_hash, other_hash, relation=meta.get("relation", "relates_to"))
                except Exception:
                    pass
    except Exception as e:
        _log("warn", f"⚠️ KG ingest failed: {e}")

# Register the listener once at import time
register_event_listener("knowledge_index.glyph_entry_added", _kg_ingest_listener)

# -----------------------------------------------------------------------------
# Heartbeat
# -----------------------------------------------------------------------------
def emit_heartbeat(interval: float = 5.0) -> None:
    """Emit periodic heartbeat pulses over SQI to confirm system is alive."""
    def _heartbeat_loop():
        while True:
            emit_sqi_event("heartbeat", {"timestamp": time.time()})
            time.sleep(interval)

    threading.Thread(target=_heartbeat_loop, daemon=True).start()
    _log("info", f"💓 SQI heartbeat started (interval: {interval}s)")

# Auto-start heartbeat if enabled
if os.getenv("SQI_HEARTBEAT", "true").lower() == "true":
    try:
        iv = float(os.getenv("SQI_HEARTBEAT_INTERVAL", "5"))
    except Exception:
        iv = 5.0
    emit_heartbeat(interval=iv)

def emit_sqi_mutation_score_if_applicable(event: Dict[str, Any]) -> None:
    """
    Emit SQI score and feedback based on mutation evaluation metadata.

    Args:
        event: A mutation dictionary containing:
            - metadata.entropy_delta (float)
            - metadata.rewrite_success_prob (float)
            - metadata.goal_match_score (float)
            - original (dict)
            - mutated (dict)
    """
    if not isinstance(event, dict):
        return

    metadata = event.get("metadata", {})
    delta = metadata.get("entropy_delta")
    success_prob = metadata.get("rewrite_success_prob")
    goal_score = metadata.get("goal_match_score")
    container_id = event.get("metadata", {}).get("container_id") or event.get("container_id")

    score_payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": "SQI_MUTATION_EVAL",
        "container_id": container_id,
        "entropy_delta": delta,
        "rewrite_success_prob": success_prob,
        "goal_match_score": goal_score,
        "mutation_id": event.get("mutation_id"),
    }

    # 📊 1. Record the event for long-term metric tracking
    record_sqi_score_event(score_payload)

    # 🧠 2. Write to .dc container trace (via KG)
    write_glyph_event(
        container_id=container_id,
        glyph=event.get("mutated", {}),
        event_type="sqiMutationScore",
        metadata=score_payload
    )

    # 🌐 3. Emit via GlyphNet WebSocket
    broadcast_glyph_event({
        "type": "sqi_score_event",
        "container_id": container_id,
        "payload": score_payload
    })

    # 🧾 Optional CLI/Dev log
    print(f"[SQI] Mutation ΔEntropy={delta}, Success={success_prob}, GoalScore={goal_score}")
# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------
def cleanup_sqi() -> None:
    """Clean up GPIO pins on shutdown."""
    if GPIO_AVAILABLE:
        try:
            GPIO.cleanup()
            _log("info", "🧹 SQI GPIO cleaned up.")
        except Exception:
            pass

# =============================================================================
# Helpers for inline ingest (fallback path) + relation linking
# =============================================================================

def _safe_add_to_index_from_bus(payload: dict):
    """
    Map a bus payload into KnowledgeIndex.add_entry kwargs and insert safely.
    Returns the stored entry dict if available (newer KnowledgeIndex returns dict),
    or True/False for older versions.
    """
    try:
        from backend.modules.knowledge_graph.indexes.knowledge_index import knowledge_index
    except Exception:
        return False

    entry = (payload or {}).get("entry") or {}
    container_id = (payload or {}).get("container_id") or "unknown"

    # Map bus fields -> KnowledgeIndex fields (best effort)
    glyph        = entry.get("glyph", "")
    meaning      = entry.get("meaning", "")
    tags         = entry.get("tags", []) or []
    source       = entry.get("type", "bus")
    confidence   = float(entry.get("confidence", 1.0))
    plugin       = entry.get("plugin")
    anchor       = entry.get("anchor")
    external_hash = entry.get("hash")
    timestamp     = entry.get("timestamp")

    kwargs = {
        "glyph": glyph,
        "meaning": meaning,
        "tags": tags,
        "source": source,
        "container_id": container_id,
        "confidence": confidence,
        "plugin": plugin,
        "anchor": anchor,
        "external_hash": external_hash,
        "timestamp": timestamp,
    }

    # Prefer newer KnowledgeIndex that returns a stored dict; gracefully handle legacy
    try:
        stored = knowledge_index.add_entry(**kwargs)
        return stored
    except TypeError:
        legacy_fields = {
            k: kwargs[k]
            for k in ("glyph","meaning","tags","source","container_id","confidence","plugin","anchor")
            if k in kwargs
        }
        return knowledge_index.add_entry(**legacy_fields)

def _maybe_link_relations(entry: dict, external_hash: Optional[str]) -> None:
    """
    If the bus payload carried relation info, create a link from this entry's hash
    to the provided related hashes. Silent on failure.
    """
    try:
        from backend.modules.knowledge_graph.indexes.knowledge_index import knowledge_index
    except Exception:
        return

    meta = (entry or {}).get("meta") or {}
    relates = meta.get("relates_to") or []
    my_hash = external_hash or entry.get("hash")
    if not my_hash or not relates:
        return

    for other_hash in relates:
        try:
            knowledge_index.add_link(my_hash, other_hash, relation=meta.get("relation", "relates_to"))
        except Exception:
            pass

from backend.modules.sqi.sqi_event_bus_gw import publish
sqi_event_bus_gw.init_gw_publish_wrapper(publish)