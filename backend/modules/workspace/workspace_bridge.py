# File: backend/modules/workspace/workspace_bridge.py
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Callable, Awaitable

# --- Safe imports with graceful fallbacks ------------------------------------

# SQI drift logger (canonical deep path first)
try:
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import (  # noqa: E501
        log_sqi_drift,
    )
except Exception:
    try:
        from backend.modules.sqi.sqi_reasoning_module import log_sqi_drift  # legacy path
    except Exception:
        try:
            from backend.modules.sqi.sqi_scorer import log_sqi_drift  # scorer fallback
        except Exception:

            def log_sqi_drift(container_id: str, wave_id: str, glow: float, pulse: float) -> None:  # type: ignore
                print(f"[SQI] (stub) Drift beam {wave_id} in {container_id} -> glow={glow:.2f}, pulse={pulse:.2f}Hz")


# Collapse/codex metric
try:
    from backend.modules.codex.codex_metrics import log_collapse_metric  # ✅ canonical
except Exception:
    def log_collapse_metric(container_id, wave_id, score, state):  # type: ignore
        print(f"[CodexMetric] Beam {wave_id} in {container_id} -> SQI={score:.3f}, state={state}")


# Carrier type (enum) - optional
try:
    from backend.modules.glyphwave.carrier.carrier_types import CarrierType as _CarrierType  # type: ignore
    CarrierType = _CarrierType
    DEFAULT_CARRIER = getattr(CarrierType, "SIMULATED", "simulated")
except Exception:
    class CarrierType:  # type: ignore
        SIMULATED = "simulated"

    DEFAULT_CARRIER = "simulated"


# Core wave state
from backend.modules.glyphwave.core.wave_state import WaveState

# Creative / research utilities (with fallbacks)
try:
    from backend.modules.creative.innovation_scorer import compute_innovation_score
except Exception:

    def compute_innovation_score(tree: Dict[str, Any], mutated: bool = False) -> float:  # type: ignore
        # Simple heuristic fallback
        size = 1
        if isinstance(tree, dict):
            size += len(tree.keys())
        if isinstance(tree.get("children"), list):  # type: ignore
            size += len(tree["children"])  # type: ignore
        base = min(1.0, 0.1 + size * 0.05)
        return max(0.0, min(1.0, base if mutated else base * 0.9))


try:
    from backend.modules.creative.symbolic_mutation_engine import mutate_symbolic_logic
except Exception:

    def mutate_symbolic_logic(tree: Dict[str, Any], max_variants: int = 1) -> List[Dict[str, Any]]:  # type: ignore
        # Minimal mutation: duplicate and tag
        mutated = []
        for i in range(max_variants):
            copy = {"label": tree.get("label", "root"), "children": list(tree.get("children", []))}
            copy["mutated"] = True
            copy["variant"] = i
            mutated.append(copy)
        return mutated


# QWave & WS, QFC visualization
try:
    from backend.modules.glyphwave.qwave.qwave_emitter import emit_qwave_beam  # async
except Exception:
    async def emit_qwave_beam(*, wave: WaveState, container_id: str, source: str, metadata: Dict[str, Any]):  # type: ignore
        print(f"[QWaveEmitter] ⚡ Emitting beam from source: {source} -> {getattr(wave, 'wave_id', None)}")
        # pretend to do I/O
        await asyncio.sleep(0)

try:
    from backend.modules.websocket_manager import broadcast_event  # async
except Exception:
    async def broadcast_event(tag: str, payload: Dict[str, Any]):  # type: ignore
        print(f"[📣] Broadcasting to 0 clients on tag: {tag}")
        await asyncio.sleep(0)

# These are OPTIONAL helpers; we'll use them if available, but never rely on them.
try:
    from backend.modules.visualization.glyph_to_qfc import to_qfc_payload  # type: ignore
except Exception:
    to_qfc_payload = None  # type: ignore

try:
    from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update  # type: ignore
except Exception:
    def broadcast_qfc_update(container_id: str, payload: Dict[str, Any]):  # type: ignore
        nodes_ct = len((payload or {}).get("nodes", []) or [])
        print(f"📡 QFC broadcast sent for: {container_id} | Nodes: {nodes_ct}")

# Container index writer (innovation entries)
from backend.modules.dna_chain.container_index_writer import add_innovation_score_entry

BRIDGE_SOURCE = "workspace_bridge"


# --- Async spawn helper (no warnings in CLI/tests) -----------------------------------
def _spawn_async(factory: Callable[[], Awaitable[Any]], label: str) -> None:
    """
    Schedule a coroutine if a loop is running; otherwise, skip gracefully.
    IMPORTANT: pass a *factory* (lambda) that creates the coroutine, so we don't
    instantiate coroutines unless we can actually schedule them (prevents
    'coroutine was never awaited' RuntimeWarnings in CLI/pytest).
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(factory())
    except RuntimeError:
        # No running loop (common in pytest/CLI)
        print(f"⚠️ {label} skipped: no running event loop")


# --- Small helpers ------------------------------------------------------------

def _new_wave_id() -> str:
    return str(uuid.uuid4())


def _symbolic_tree_to_nodes(tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Very small adapter to a QFC 'nodes' list from a symbolic tree.
    The real system likely has richer conversion; this is safe/minimal.
    """
    nodes: List[Dict[str, Any]] = []

    def walk(n: Dict[str, Any], depth: int = 0):
        label = n.get("label", f"node_{depth}")
        nodes.append({"id": f"{label}-{depth}-{len(nodes)}", "label": label})
        for child in n.get("children", []) or []:
            if isinstance(child, dict):
                walk(child, depth + 1)

    if isinstance(tree, dict):
        walk(tree, 0)
    return nodes


def _emit_qwave(container_id: str, wave: WaveState, metadata: Dict[str, Any]) -> None:
    """
    Fire a QWave emitter event (async-safe, no warnings when no loop is present).
    """
    try:
        _spawn_async(
            lambda: emit_qwave_beam(
                wave=wave,
                container_id=container_id,
                source=BRIDGE_SOURCE,
                metadata=metadata,
            ),
            label="QWave emit",
        )
    except Exception as e:
        print(f"[WorkspaceBridge] ⚠️ QWave emitter failed: {e}")


def _broadcast_fork(
    container_id: str,
    wave: WaveState,
    packet: Optional[Dict[str, Any]],
    scores: Dict[str, float],
    reason: Optional[str],
) -> None:
    """
    Broadcast a glyphwave-compatible fork beam message for live UIs (async-safe).
    """
    try:
        payload = {
            "type": "workspace_result_beam",
            "wave_id": getattr(wave, "wave_id", None),
            "parent_wave_id": None,  # no parent for workspace requests
            "carrier_packet": packet,
            "scores": scores,
            "mutation_cause": reason or "workspace_query",
            "timestamp": getattr(wave, "timestamp", None),
        }
        _spawn_async(lambda: broadcast_event("glyphwave.fork_beam", payload), label="WS broadcast")
    except Exception as e:
        print(f"[WorkspaceBridge] ⚠️ WS broadcast failed: {e}")


def _safe_qfc_payload(
    container_id: str,
    wave: WaveState,
    symbolic_tree: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a minimal, robust QFC payload. If glyph_to_qfc.to_qfc_payload is available,
    try a few call patterns to enrich; otherwise return the minimal structure.
    """
    nodes = _symbolic_tree_to_nodes(symbolic_tree)

    # Minimal, self-sufficient payload that broadcast_qfc_update can use.
    beam_dict = {
        "id": getattr(wave, "wave_id", None),
        "glyph_id": getattr(wave, "glyph_id", None),
        "carrier_type": getattr(wave, "carrier_type", None),
        "modulation": getattr(wave, "modulation_strategy", None),
        "timestamp": getattr(wave, "timestamp", None),
        "coherence": getattr(wave, "coherence", None),
        "glow_intensity": getattr(wave, "glow_intensity", None),
        "pulse_frequency": getattr(wave, "pulse_frequency", None),
        "origin": "workspace_bridge",
    }

    payload: Dict[str, Any] = {
        "type": "qfc_workspace_update",
        "container_id": container_id,
        "nodes": nodes,
        "beam": beam_dict,
    }

    # Opportunistically enrich via to_qfc_payload if present.
    if callable(to_qfc_payload):
        attempts: List[Callable[[], Any]] = [
            # common patterns used in other modules (unknown exact sig)
            lambda: to_qfc_payload(payload),                      # type: ignore
            lambda: to_qfc_payload(beam_dict, {"nodes": nodes}),  # type: ignore
            lambda: to_qfc_payload({"nodes": nodes, "beam": beam_dict}),  # type: ignore
            lambda: to_qfc_payload(wave, {"nodes": nodes}),       # type: ignore
        ]
        for make in attempts:
            try:
                enriched = make()
                if isinstance(enriched, dict):
                    # Sanity: ensure at least nodes survive; otherwise keep minimal payload.
                    if "nodes" in enriched or "beam" in enriched or "qfc" in enriched:
                        payload = enriched
                        break
            except Exception:
                # ignore and try next pattern
                pass

    return payload


def _emit_to_qfc(container_id: str, wave: WaveState, symbolic_tree: Dict[str, Any]) -> None:
    """
    Push a small update to the QFC. Does not assume any specific to_qfc_payload signature.
    """
    try:
        payload = _safe_qfc_payload(container_id, wave, symbolic_tree)
        broadcast_qfc_update(container_id, payload)
    except Exception as e:
        print(f"[WorkspaceBridge] ⚠️ QFC update failed: {e}")


# --- Public API ----------------------------------------------------------------

def submit_workspace_query(
    *,
    container_id: str,
    query_type: str = "symbolic_query",
    symbolic_tree: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
    carrier_type: Any = DEFAULT_CARRIER,
) -> Dict[str, Any]:
    """
    Bridge entrypoint: take a Workspace query (e.g., AtomSheet hypothesis) and route it
    into the Research/Creative pipeline, then emit a beam + HUD/QFC updates.

    Returns a small dict suitable for unit tests/CLI.
    """

    if query_type not in {"symbolic_query", "codex", "hypothesis"}:
        raise ValueError(f"Unsupported query_type: {query_type}")

    # --- Step 1: Choose/prepare a tree ------------------------------------------------
    tree: Dict[str, Any] = symbolic_tree or {"label": "root", "children": []}

    # --- Step 2: Run a light mutation and score innovation ----------------------------
    try:
        mutated_list = mutate_symbolic_logic(tree, max_variants=1)
    except Exception as e:
        print(f"[WorkspaceBridge] ❌ mutation failed: {e}")
        mutated_list = [tree]

    mutated = mutated_list[0] if mutated_list else tree

    try:
        innovation = compute_innovation_score(mutated, mutated=True)
    except Exception as e:
        print(f"[WorkspaceBridge] ❌ scoring failed: {e}")
        innovation = 0.0

    glow = round(innovation * 5, 2)
    pulse = round(1 + (innovation * 4), 2)

    # --- Step 3: Build a wave for the result ------------------------------------------
    wave_id = _new_wave_id()
    wave = WaveState(
        wave_id=wave_id,
        glyph_data={"symbolic_tree": mutated, "origin": "workspace_bridge"},
        glyph_id="workspace_beam",
        carrier_type=carrier_type,
        modulation_strategy="bridge",
    )

    # --- Step 4: Write metrics / indices ----------------------------------------------
    try:
        log_collapse_metric(container_id, wave_id, innovation, "entangled")
    except Exception as e:
        print(f"[WorkspaceBridge] ⚠️ collapse metric failed: {e}")

    try:
        log_sqi_drift(container_id, wave_id, glow, pulse)
    except Exception as e:
        print(f"[WorkspaceBridge] ⚠️ SQI drift log failed: {e}")

    try:
        add_innovation_score_entry(
            wave_id=wave_id,
            parent_wave_id=None,
            score=innovation,
            glow=glow,
            pulse=pulse,
            cause=reason or "workspace_query",
        )
    except Exception as e:
        print(f"[WorkspaceBridge] ⚠️ innovation index write failed: {e}")

    # --- Step 5: Emit to QWave + WS + QFC ---------------------------------------------
    _emit_qwave(
        container_id=container_id,
        wave=wave,
        metadata={"scores": {"innovation_score": round(innovation, 3)}, "reason": reason or "workspace"},
    )

    # Carrier packet (reserved/optional): keep lightweight for now
    carrier_packet: Optional[Dict[str, Any]] = None

    _broadcast_fork(
        container_id=container_id,
        wave=wave,
        packet=carrier_packet,
        scores={"innovation_score": round(innovation, 3)},
        reason=reason,
    )

    _emit_to_qfc(container_id, wave, mutated)

    # --- Step 6: Return a minimal response --------------------------------------------
    return {
        "ok": True,
        "wave_id": wave_id,
        "scores": {"innovation_score": round(innovation, 3)},
    }