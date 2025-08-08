# File: backend/modules/sqi/sqi_event_bus.py
"""
SQI Event Bus
=============
Manages emission of SQI (Symbolic Quantum Interface) events to GPIO pins or simulated outputs.
Integrates with Raspberry Pi GPIO for hardware signaling, while providing a fallback simulation
mode when running off-Pi (e.g., dev environment).

Additions in this version:
    • Burst-debounce + idempotent guard for knowledge_index.glyph_entry_added
    • publish_kg_added(payload) convenience publisher (drops dupes)
    • Safe wiring to KnowledgeIndex via knowledge_bus_adapter.ingest_bus_event
    • Relation linking: if payload.entry.meta.relates_to is provided, create KG edges
"""

import os
import time
import threading
from collections import OrderedDict
from typing import Dict, Callable, Optional

# ---- Optional KG adapter wiring --------------------------------------------
try:
    # Ingests bus payloads into KnowledgeIndex with external_hash idempotency
    from backend.modules.knowledge_graph.knowledge_bus_adapter import ingest_bus_event
    _KG_ADAPTER_AVAILABLE = True
except Exception as _e:
    ingest_bus_event = None  # type: ignore
    _KG_ADAPTER_AVAILABLE = False
    print(f"⚠️ SQI: Knowledge bus adapter not available ({_e}). KG ingest will be skipped.")

# ---- GPIO detection ---------------------------------------------------------
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)  # BCM pin numbering
    GPIO_AVAILABLE = True
    print("✅ SQI: Raspberry Pi GPIO detected, hardware mode enabled.")
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️ SQI: No GPIO detected, running in simulation mode.")

# ---- Defaults ---------------------------------------------------------------
DEFAULT_PINS = {
    "container_growth": 17,
    "glyph_injection": 27,
    "entropy_pulse": 22,
    "heartbeat": 5,
}

# Event listeners registry (str -> list[callable])
event_listeners: Dict[str, list[Callable[[dict], None]]] = {}

# ---- Debounce / Idempotency for KG events ----------------------------------
_DEDUPE = OrderedDict()     # (container_id, external_hash) -> last_ms
_DEBOUNCE_MS = 150          # collapse storms within this window
_MAX_CACHE = 4096           # LRU-ish cap

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

# ---- Listener registration --------------------------------------------------
def register_event_listener(event_type: str, callback: Callable[[dict], None]) -> None:
    """Register a listener function for a given SQI event."""
    if event_type not in event_listeners:
        event_listeners[event_type] = []
    event_listeners[event_type].append(callback)
    print(f"🔗 SQI listener registered for event: {event_type}")

# ---- Low-level GPIO pulse ---------------------------------------------------
def _pulse_pin(pin: int, duration: float = 0.1) -> None:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(pin, GPIO.LOW)

# ---- Core emitter -----------------------------------------------------------
def emit_sqi_event(event_type: str, payload: Optional[dict] = None) -> None:
    """
    Emit an SQI event, pulsing GPIO (if available) and notifying listeners.
    """
    payload = payload or {}
    print(f"[SQI Event] {event_type} | Payload: {payload}")

    # Hardware pulse or simulated notice
    if GPIO_AVAILABLE and event_type in DEFAULT_PINS:
        pin = DEFAULT_PINS[event_type]
        threading.Thread(target=_pulse_pin, args=(pin,), daemon=True).start()
    elif not GPIO_AVAILABLE:
        print(f"⚠️ SQI simulated pulse → Event: {event_type}")

    # Notify listeners
    if event_type in event_listeners:
        for callback in list(event_listeners[event_type]):
            try:
                callback(payload)
            except Exception as e:
                print(f"⚠️ SQI listener error for {event_type}: {e}")

# ---- High-level publishers --------------------------------------------------
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

# ---- Optional: auto-wire KG ingest as a listener ---------------------------
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
        print(f"⚠️ KG ingest failed: {e}")

# Register the listener once at import time
register_event_listener("knowledge_index.glyph_entry_added", _kg_ingest_listener)

# ---- Heartbeat --------------------------------------------------------------
def emit_heartbeat(interval: float = 5.0) -> None:
    """Emit periodic heartbeat pulses over SQI to confirm system is alive."""
    def _heartbeat_loop():
        while True:
            emit_sqi_event("heartbeat", {"timestamp": time.time()})
            time.sleep(interval)

    threading.Thread(target=_heartbeat_loop, daemon=True).start()
    print(f"💓 SQI heartbeat started (interval: {interval}s)")

# ---- Cleanup ----------------------------------------------------------------
def cleanup_sqi() -> None:
    """Clean up GPIO pins on shutdown."""
    if GPIO_AVAILABLE:
        GPIO.cleanup()
        print("🧹 SQI GPIO cleaned up.")

# ---- Auto-start heartbeat if enabled ---------------------------------------
if os.getenv("SQI_HEARTBEAT", "true").lower() == "true":
    emit_heartbeat()

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