# File: backend/modules/holograms/ghx_replay_broadcast.py

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.config import GW_ENABLED

from backend.modules.websocket_manager import broadcast_event  # async: broadcast_event(tag, payload)
from backend.modules.symbolic.symbol_tree_generator import SymbolicMeaningTree
from backend.modules.sqi.metrics_bus import metrics_bus
from backend.modules.symbolic.decoherence import calc_decoherence
from backend.modules.glyphwave.gwip.gwip_encoder import encode_gwip_packet
from backend.modules.glyphwave.carrier.carrier_types import CarrierType  # noqa: F401
from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam

# 🧩 Metrics + Feedback
from backend.modules.symbolic.metrics_logger import log_metrics
from backend.modules.symbolic.runtime_feedback import send_runtime_feedback
from backend.modules.symbolic.decoherence_alerts import check_anomaly
from backend.modules.symbolic.mutation_trigger import trigger_mutation_if_needed

# ✅ GWV snapshot buffer
from backend.modules.dna_chain.container_index_writer import add_gwv_trace_entry
from backend.modules.glyphwave.gwv_writer import SnapshotRingBuffer

# ✅ DreamOS ghost replay
from backend.modules.dreamos.ghost_entry import inject_ghost_from_gwv

# ✅ Signing
from backend.modules.glyphvault.waveglyph_signer import sign_waveglyph
from backend.modules.encryption.glyph_vault import GlyphVault

from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.identity.avatar_registry import get_avatar_identity
from backend.modules.holograms.morphic_ledger import morphic_ledger

# ✅ HUD event import (fallback-safe)
try:
    from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
except Exception:

    async def send_codex_ws_event(event_type: str, payload: dict):
        print(f"[Fallback HUD] {event_type} -> {payload}")


log = logging.getLogger(__name__)
QUIET = os.getenv("AION_QUIET_MODE", "0") == "1"

# Optional hard kill-switch for WS broadcasts (useful for perf tests)
DISABLE_GHX_WS = os.getenv("AION_DISABLE_GHX_WS", "0") == "1"

# Throttles to prevent IO/CPU spikes
GHX_METRICS_TICK_S = float(os.getenv("AION_GHX_METRICS_TICK_S", "1.0"))  # default 1s
GWV_EXPORT_INTERVAL_S = float(os.getenv("AION_GWV_EXPORT_INTERVAL_S", "10.0"))  # default 10s
GWV_MAX_EXPORTS_PER_MIN = int(os.getenv("AION_GWV_MAX_EXPORTS_PER_MIN", "6"))  # default 6/min

snapshot_buffer = SnapshotRingBuffer(maxlen=60)

# Runtime state
collapse_counter = 0
last_tick_time = time.time()
previous_decoherence: Optional[float] = None
_last_gwv_export_ts = 0.0
_gwv_exports_window: List[float] = []  # timestamps of recent exports


def _fire_and_forget(coro) -> None:
    """Schedule a coroutine safely without blocking."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # no running loop (thread/CLI) -> best effort
        try:
            asyncio.run(coro)
        except Exception:
            pass


async def _broadcast(tag: str, payload: Dict[str, Any]) -> None:
    """Guarded WS broadcast (can be disabled for perf)."""
    if DISABLE_GHX_WS:
        return
    try:
        await broadcast_event(tag, payload)
    except Exception:
        # never let GHX broadcasting break pipelines/tests
        pass


async def _emit_qwave_safe(*, container_id: Optional[str], beam_payload: Dict[str, Any]) -> None:
    """
    QWave emitter has varied signatures across branches. Try common call patterns.
    Never raise.
    """
    try:
        # pattern A: emit_qwave_beam(source=..., payload=..., context=...)
        try:
            await emit_qwave_beam(
                source="ghx_replay",
                payload=beam_payload,
                context={"container_id": container_id, "source_node": "ghx_replay_engine"},
            )
            return
        except TypeError:
            pass

        # pattern B: emit_qwave_beam(wave=..., container_id=..., source=..., metadata=...)
        # We don't have a WaveState here; skip if that's required.
    except Exception:
        pass


def _gwv_export_allowed(now: float) -> bool:
    """Simple rate limiter for GWV exports."""
    global _gwv_exports_window
    window_start = now - 60.0
    _gwv_exports_window = [t for t in _gwv_exports_window if t >= window_start]
    return len(_gwv_exports_window) < max(1, GWV_MAX_EXPORTS_PER_MIN)


async def stream_symbolic_tree_replay(tree: SymbolicMeaningTree, container_id: str = None):
    """
    Broadcast symbolic tree replay to GHX clients, emit collapse/decoherence metrics,
    and periodically export + sign `.gwv` trace snapshots (rate-limited).
    """
    global collapse_counter, last_tick_time, previous_decoherence, _last_gwv_export_ts, _gwv_exports_window

    if not tree or not getattr(tree, "trace", None) or not getattr(tree.trace, "replayPaths", None):
        if not QUIET:
            print("[GHX-Broadcast] ⚠️ No replay paths found in symbolic tree.")
        return

    # ─────────────────────────────────────────────────────────────
    # 📡 Replay Broadcast
    # ─────────────────────────────────────────────────────────────
    payload = {
        "type": "symbolic_tree_replay",
        "container_id": container_id,
        "replayPaths": tree.trace.replayPaths,
        "entropyOverlay": getattr(tree.trace, "entropyOverlay", None),
        "goalScores": {
            node_id: node.goal_score
            for node_id, node in (getattr(tree, "node_index", {}) or {}).items()
            if getattr(node, "goal_score", None) is not None
        },
    }

    if not QUIET:
        print(f"[GHX-Broadcast] 📡 Broadcasting symbolic replay for container {container_id or 'unknown'}")

    if GW_ENABLED:
        await _broadcast("ghx_replay", payload)
    else:
        await _broadcast(
            "sqi_event",
            {
                "type": "sqi_event",
                "mode": "replay",
                "container_id": container_id,
                "replay": payload["replayPaths"],
                "entropy": payload["entropyOverlay"],
                "goals": payload["goalScores"],
            },
        )

    # 🌊 Emit QWave beam for symbolic replay (best-effort)
    await _emit_qwave_safe(
        container_id=container_id,
        beam_payload={
            "event": "symbolic_tree_replay",
            "container_id": container_id,
            "replay_path_count": len(tree.trace.replayPaths or []),
            "entropy_summary": getattr(tree.trace, "entropyOverlay", None),
            "goal_node_count": len(payload.get("goalScores", {}) or {}),
            "tags": ["ghx_replay", "symbolic_broadcast"],
        },
    )

    # ─────────────────────────────────────────────────────────────
    # 📈 Collapse/Decoherence Metrics (1 Hz default)
    # ─────────────────────────────────────────────────────────────
    collapse_counter += 1
    now = time.time()

    if (now - last_tick_time) < GHX_METRICS_TICK_S:
        return

    deco = calc_decoherence(tree)

    coherence_trend = "➖"
    coherence_delta: Optional[float] = None
    if previous_decoherence is not None:
        delta = previous_decoherence - deco
        coherence_delta = delta
        if abs(delta) < 0.0001:
            coherence_trend = "➖"
        elif delta > 0:
            coherence_trend = "📈"
        else:
            coherence_trend = "📉"

    previous_decoherence = deco

    metrics_payload = {
        "collapse_per_sec": collapse_counter,
        "decoherence_rate": deco,
        "coherence_delta": coherence_delta,
        "coherence_trend": coherence_trend,
        "timestamp": now,
        "event_type": "collapse_tick",
    }

    # 📡 QFC Tick Broadcast (best effort)
    try:
        from backend.modules.sci.qfc_ws_broadcaster import broadcast_qfc_tick_update

        qfc_snapshot = {
            "nodes": getattr(tree.trace, "visual_nodes", None),
            "links": getattr(tree.trace, "visual_links", None),
            "glyphs": getattr(tree.trace, "raw_glyphs", None),
            "scrolls": getattr(tree.trace, "attached_scrolls", None),
            "qwaveBeams": getattr(tree.trace, "qwave_beams", None),
            "entanglement": getattr(tree.trace, "entanglement_map", None),
            "sqi_metrics": getattr(tree.trace, "sqi_summary", None),
            "camera": getattr(tree.trace, "camera_frame", None),
            "reflection_tags": getattr(tree.trace, "reflection_tags", None),
        }

        await broadcast_qfc_tick_update(
            tick_id=collapse_counter,
            frame_state=qfc_snapshot,
            observer_id="hud_ghx_1",
            total_ticks=None,
            source="GHXReplay",
        )
    except Exception:
        pass

    metrics_bus.push(metrics_payload)

    if GW_ENABLED:
        await _broadcast("collapse_metrics", metrics_payload)
    else:
        await _broadcast(
            "sqi_event",
            {
                "type": "sqi_event",
                "mode": "metrics",
                "collapse_rate": collapse_counter,
                "decoherence": deco,
                "trend": coherence_trend,
                "delta": coherence_delta,
                "timestamp": metrics_payload["timestamp"],
            },
        )

    # 🧩 Metric Side Effects (keep these)
    log_metrics(collapse_counter, deco)
    await send_runtime_feedback(collapse_counter, deco, container_id or "unknown")
    check_anomaly(deco, container_id or "unknown")
    trigger_mutation_if_needed(collapse_counter, deco, container_id or "unknown")

    # 🧠 Save to GWV ring buffer
    try:
        snapshot_buffer.add_snapshot(collapse_counter, deco)
    except Exception:
        pass

    # ─────────────────────────────────────────────────────────────
    # 💾 Periodic Snapshot Export, Signing, Trace Injection (rate-limited)
    # ─────────────────────────────────────────────────────────────
    if (now - _last_gwv_export_ts) >= GWV_EXPORT_INTERVAL_S and _gwv_export_allowed(now):
        _last_gwv_export_ts = now
        _gwv_exports_window.append(now)

        try:
            snapshot_path = snapshot_buffer.export_to_gwv(container_id or "unknown")
            if not QUIET:
                print(f"[GWV] 📂 Snapshot exported to: {snapshot_path}")

            with open(snapshot_path, "r", encoding="utf-8") as f:
                trace_str = f.read()
            trace_obj = json.loads(trace_str)

            # 🔏 Sign snapshot with Vault key
            try:
                vault = GlyphVault()
                private_key = vault.get_private_key()
            except Exception:
                private_key = None

            if not private_key:
                if not QUIET:
                    print("[GWV] ❌ No private key found in Vault - cannot sign snapshot.")
            else:
                signed_trace = sign_waveglyph(trace_obj, private_key)
                with open(snapshot_path, "w", encoding="utf-8") as out_f:
                    json.dump(signed_trace, out_f, indent=2)
                if not QUIET:
                    print("[GWV] 🔏 Snapshot signed with Vault key")

            # 🧠 Inject trace into .dc.json container
            try:
                trace_id = add_gwv_trace_entry(trace_str, container_id or "unknown")
                if not QUIET:
                    print(f"[GWV] 🧠 Trace injected into container as entry {trace_id}")
            except Exception as e:
                if not QUIET:
                    print(f"[GWV] ⚠️ Trace injection failed: {e}")

            # 👻 Inject ghost replay into DreamOS
            try:
                ghost_path = inject_ghost_from_gwv(trace_str, container_id or "unknown")
                if not QUIET:
                    print(f"[DREAMOS] 👻 Ghost replay injected at {ghost_path}")
            except Exception as e:
                if not QUIET:
                    print(f"[DREAMOS] ⚠️ Ghost inject failed: {e}")

        except Exception as e:
            if not QUIET:
                print(f"[GWV] ⚠️ Snapshot export/sign/inject failed: {e}")

    # 🔁 Reset tick window
    collapse_counter = 0
    last_tick_time = now


async def emit_gwave_replay(wave):
    """
    Broadcast a single GWave replay packet with carrier metadata over WebSocket.
    Also emits overlay info for HUD.
    """
    try:
        packet = encode_gwip_packet(
            wave=wave,
            carrier_type=getattr(wave, "carrier_type", None),
            modulation_strategy=getattr(wave, "modulation_strategy", None),
            delay_ms=getattr(wave, "delay_ms", 0.0),
        )

        wave_id = getattr(wave, "id", None) or getattr(wave, "wave_id", None)

        await _broadcast(
            "glyphwave.replay",
            {
                "type": "carrier_trace",
                "packet": packet,
            },
        )

        await _broadcast(
            "glyphwave.overlay",
            {
                "type": "carrier_overlay",
                "wave_id": wave_id,
                "carrier_type": getattr(getattr(wave, "carrier_type", None), "name", str(getattr(wave, "carrier_type", None))),
                "modulation_strategy": getattr(wave, "modulation_strategy", None),
                "coherence": getattr(wave, "coherence", None),
                "delay_ms": round(float(getattr(wave, "delay_ms", 0.0) or 0.0), 2),
            },
        )

        if not QUIET:
            ct = getattr(getattr(wave, "carrier_type", None), "name", str(getattr(wave, "carrier_type", None)))
            ms = getattr(wave, "modulation_strategy", None)
            print(f"[GWIP] 📡 Carrier packet broadcasted for wave {wave_id} ({ct} / {ms})")

    except Exception as e:
        if not QUIET:
            print(f"[GWIP] ⚠️ Failed to emit carrier trace: {e}")


# ──────────────────────────────────────────────
#  Tessaris * Symbolic HSX Bridge (HQCE Stage 5)
# ──────────────────────────────────────────────
class SymbolicHSXBridge:
    """Bridges symbolic cognition metrics into holographic overlays."""

    def __init__(self, avatar_id: str, ghx_packet: Dict[str, Any]):
        self.avatar_id = avatar_id
        self.ghx_packet = ghx_packet
        self.identity = get_avatar_identity(avatar_id)

    def inject_identity_trails(self) -> Dict[str, Any]:
        for node in self.ghx_packet.get("nodes", []) or []:
            if not isinstance(node, dict):
                continue
            node.setdefault("symbolic_trail", []).append(
                {
                    "by": self.identity.get("name", "anon"),
                    "avatar_id": self.avatar_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "signature": self.identity.get("signature", str(uuid.uuid4())),
                }
            )
        log.debug(f"[HSXBridge] Identity trails injected into {len(self.ghx_packet.get('nodes', []) or [])} nodes.")
        return self.ghx_packet

    def score_overlay_paths(self) -> List[Dict[str, Any]]:
        nodes = self.ghx_packet.get("nodes", []) or []
        if not nodes:
            return []

        weights: List[float] = []
        entropies: List[float] = []

        for node in nodes:
            if not isinstance(node, dict):
                continue
            symbol = node.get("symbol")
            scores = CodexMetrics.score_symbol(symbol)
            w = float(scores.get("symbolic_weight", 0.0) or 0.0)
            a = float(scores.get("goal_match_score", 0.0) or 0.0)
            entropy = float(node.get("entropy", 0.0) or 0.0)

            node.update(
                {
                    "goal_alignment_score": a,
                    "symbolic_weight": w,
                    "entropy": entropy,
                }
            )
            weights.append(w)
            entropies.append(entropy)

        if weights:
            mean_w = sum(weights) / len(weights)
            var_w = sum((w - mean_w) ** 2 for w in weights) / len(weights)
            mean_entropy = sum(entropies) / len(entropies) if entropies else 0.0
            κs = math.tanh(mean_w / (1.0 + 10.0 * var_w + mean_entropy))
            for node in nodes:
                if isinstance(node, dict):
                    node["semantic_kappa"] = κs
            log.info(f"[HSXBridge] Semantic κs={κs:.4f}")
        else:
            κs, mean_w, mean_entropy, var_w = 0.0, 0.0, 0.0, 0.0
            log.warning("[HSXBridge] No symbolic weights found for κ computation.")

        # Write to Morphic Ledger (best effort)
        try:
            morphic_ledger.append(
                {
                    "psi": mean_entropy,
                    "kappa": κs,
                    "T": 1.0,
                    "coherence": mean_w,
                    "gradient": var_w**0.5,
                    "stability": mean_w / (1.0 + var_w) if (1.0 + var_w) else 0.0,
                    "metadata": {"origin": "SymbolicHSXBridge"},
                },
                observer=self.avatar_id,
            )
        except Exception:
            pass

        return nodes

    def compute_semantic_gravity(self) -> Dict[str, Any]:
        nodes = self.ghx_packet.get("nodes", []) or []
        if not nodes:
            return {"clusters": [], "field_strength": 0.0}

        clusters = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            κs = float(node.get("semantic_kappa", 0.0) or 0.0)
            w = float(node.get("symbolic_weight", 0.0) or 0.0)
            entropy = float(node.get("entropy", 0.0) or 0.0)
            strength = (w * (1 - entropy)) * (1 + κs)
            clusters.append(
                {
                    "glyph_id": node.get("glyph_id"),
                    "symbol": node.get("symbol"),
                    "gravity_strength": round(float(strength), 4),
                    "semantic_kappa": κs,
                    "weight": w,
                    "entropy": entropy,
                }
            )

        total = sum(c["gravity_strength"] for c in clusters) or 0.0
        for c in clusters:
            c["gravity_strength"] = c["gravity_strength"] / max(total, 1e-9)

        field_strength = sum(c["gravity_strength"] for c in clusters) / max(len(clusters), 1)
        gravity_map = {
            "timestamp": datetime.utcnow().isoformat(),
            "avatar": self.avatar_id,
            "clusters": clusters,
            "field_strength": round(field_strength, 5),
        }

        log.debug(f"[HSXBridge] Semantic gravity computed ({len(clusters)} nodes, field={field_strength:.4f})")
        return gravity_map

    async def broadcast_overlay_async(self) -> None:
        payload = {
            "type": "ghx_overlay",
            "avatar": self.identity,
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": self.ghx_packet.get("nodes", []) or [],
            "projection_id": self.ghx_packet.get("projection_id"),
        }
        await _broadcast("ghx_overlay_update", payload)
        log.debug("[HSXBridge] Overlay broadcasted to GHX clients.")

    def broadcast_overlay(self) -> None:
        """
        Back-compat: callable from sync contexts.
        Schedules the async broadcaster without blocking.
        """
        _fire_and_forget(self.broadcast_overlay_async())