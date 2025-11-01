import json
import time

from backend.modules.websocket_manager import broadcast_event
from backend.modules.symbolic.symbol_tree_generator import SymbolicMeaningTree
from backend.modules.sqi.metrics_bus import metrics_bus
from backend.modules.symbolic.decoherence import calc_decoherence
from backend.modules.glyphwave.gwip.gwip_encoder import encode_gwip_packet
from backend.modules.glyphwave.carrier.carrier_types import CarrierType
from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam

# 🧩 Metrics + Feedback
from backend.modules.symbolic.metrics_logger import log_metrics
from backend.modules.symbolic.runtime_feedback import send_runtime_feedback
from backend.modules.symbolic.decoherence_alerts import check_anomaly
from backend.modules.symbolic.mutation_trigger import trigger_mutation_if_needed

# ✅ GWV snapshot buffer
from backend.modules.dna_chain.container_index_writer import add_gwv_trace_entry
from backend.modules.glyphwave.gwv_writer import SnapshotRingBuffer
snapshot_buffer = SnapshotRingBuffer(maxlen=60)

# ✅ DreamOS ghost replay
from backend.modules.dreamos.ghost_entry import inject_ghost_from_gwv

# ✅ Signing
from backend.modules.glyphvault.waveglyph_signer import sign_waveglyph
from backend.modules.encryption.glyph_vault import GlyphVault

# ✅ Config toggle
from backend.config import GW_ENABLED


# Runtime state
collapse_counter = 0
last_tick_time = time.time()
previous_decoherence = None


async def stream_symbolic_tree_replay(tree: SymbolicMeaningTree, container_id: str = None):
    """
    Async: Broadcast symbolic tree replay to GHX clients or fallback,
    emit collapse/decoherence metrics, and periodically export + sign `.gwv` trace snapshots.
    """
    global collapse_counter, last_tick_time, previous_decoherence

    if not tree or not tree.trace or not tree.trace.replayPaths:
        print("[GHX-Broadcast] ⚠️ No replay paths found in symbolic tree.")
        return

    # ─────────────────────────────────────────────────────────────
    # 📡 Replay Broadcast
    # ─────────────────────────────────────────────────────────────
    payload = {
        "type": "symbolic_tree_replay",
        "container_id": container_id,
        "replayPaths": tree.trace.replayPaths,
        "entropyOverlay": tree.trace.entropyOverlay,
        "goalScores": {
            node_id: node.goal_score
            for node_id, node in tree.node_index.items()
            if node.goal_score is not None
        },
    }

    print(f"[GHX-Broadcast] 📡 Broadcasting symbolic replay for container {container_id or 'unknown'}")

    if GW_ENABLED:
        await broadcast_event("ghx_replay", payload)
    else:
        await broadcast_event("sqi_event", {
            "type": "sqi_event",
            "mode": "replay",
            "container_id": container_id,
            "replay": payload["replayPaths"],
            "entropy": payload["entropyOverlay"],
            "goals": payload["goalScores"],
        })

    # 🌊 Emit QWave beam for symbolic replay
    try:
        beam_payload = {
            "event": "symbolic_tree_replay",
            "container_id": container_id,
            "replay_path_count": len(tree.trace.replayPaths or []),
            "entropy_summary": tree.trace.entropyOverlay,
            "goal_node_count": len(payload.get("goalScores", {})),
            "tags": ["ghx_replay", "symbolic_broadcast"]
        }

        context = {
            "container_id": container_id,
            "source_node": "ghx_replay_engine"
        }

        await emit_qwave_beam(
            source="ghx_replay",
            payload=beam_payload,
            context=context
        )

    except Exception as e:
        print(f"[GHX->QWave] ⚠️ Failed to emit QWave beam: {e}")
    # ─────────────────────────────────────────────────────────────
    # 📈 Collapse/Decoherence Metrics
    # ─────────────────────────────────────────────────────────────
    collapse_counter += 1

    if time.time() - last_tick_time >= 1:
        deco = calc_decoherence(tree)

        # ➕ Compare vs previous decoherence
        coherence_trend = "➖"
        coherence_delta = None

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
            "timestamp": time.time(),
            "event_type": "collapse_tick"
        }

        # 📡 QFC Tick Broadcast
        from backend.modules.sci.qfc_ws_broadcaster import broadcast_qfc_tick_update

        qfc_snapshot = {
            "nodes": tree.trace.visual_nodes,
            "links": tree.trace.visual_links,
            "glyphs": tree.trace.raw_glyphs,
            "scrolls": tree.trace.attached_scrolls,
            "qwaveBeams": tree.trace.qwave_beams,
            "entanglement": tree.trace.entanglement_map,
            "sqi_metrics": tree.trace.sqi_summary,
            "camera": tree.trace.camera_frame,
            "reflection_tags": tree.trace.reflection_tags,
        }

        await broadcast_qfc_tick_update(
            tick_id=collapse_counter,
            frame_state=qfc_snapshot,
            observer_id="hud_ghx_1",
            total_ticks=None,
            source="GHXReplay"
        )

        metrics_bus.push(metrics_payload)

        if GW_ENABLED:
            await broadcast_event("collapse_metrics", metrics_payload)
        else:
            await broadcast_event("sqi_event", {
                "type": "sqi_event",
                "mode": "metrics",
                "collapse_rate": collapse_counter,
                "decoherence": deco,
                "trend": coherence_trend,
                "delta": coherence_delta,
                "timestamp": metrics_payload["timestamp"]
            })

        # 🧩 Metric Side Effects
        log_metrics(collapse_counter, deco)
        await send_runtime_feedback(collapse_counter, deco, container_id or "unknown")
        check_anomaly(deco, container_id or "unknown")
        trigger_mutation_if_needed(collapse_counter, deco, container_id or "unknown")

        # 🧠 Save to GWV ring buffer
        snapshot_buffer.add_snapshot(collapse_counter, deco)

        # ─────────────────────────────────────────────────────────────
        # 💾 Periodic Snapshot Export, Signing, Trace Injection
        # ─────────────────────────────────────────────────────────────
        if int(time.time()) % 10 == 0:
            snapshot_path = snapshot_buffer.export_to_gwv(container_id or "unknown")
            print(f"[GWV] 📂 Snapshot exported to: {snapshot_path}")

            try:
                with open(snapshot_path, "r", encoding="utf-8") as f:
                    trace_str = f.read()

                trace_obj = json.loads(trace_str)

                # 🔏 Sign snapshot with Vault key
                vault = GlyphVault()
                private_key = vault.get_private_key()

                if not private_key:
                    print("[GWV] ❌ No private key found in Vault - cannot sign snapshot.")
                else:
                    signed_trace = sign_waveglyph(trace_obj, private_key)
                    with open(snapshot_path, "w", encoding="utf-8") as out_f:
                        json.dump(signed_trace, out_f, indent=2)
                    print(f"[GWV] 🔏 Snapshot signed with Vault key")

                # 🧠 Inject trace into .dc.json container
                trace_id = add_gwv_trace_entry(trace_str, container_id or "unknown")
                print(f"[GWV] 🧠 Trace injected into container as entry {trace_id}")

                # 👻 Inject ghost replay into DreamOS
                ghost_path = inject_ghost_from_gwv(trace_str, container_id or "unknown")
                print(f"[DREAMOS] 👻 Ghost replay injected at {ghost_path}")

            except Exception as e:
                print(f"[GWV] ⚠️ Failed to inject trace or ghost entry: {e}")

        # 🔁 Reset tick
        collapse_counter = 0
        last_tick_time = time.time()

async def emit_gwave_replay(wave):
    """
    Broadcast a single GWave replay packet with carrier metadata over WebSocket.
    Also emits overlay info for HUD.
    """
    try:
        packet = encode_gwip_packet(
            wave=wave,
            carrier_type=wave.carrier_type,
            modulation_strategy=wave.modulation_strategy,
            delay_ms=wave.delay_ms
        )

        # 🎯 Broadcast full carrier trace
        await broadcast_event("glyphwave.replay", {
            "type": "carrier_trace",
            "packet": packet
        })

        # 🖥️ HUD overlay injection
        await broadcast_event("glyphwave.overlay", {
            "type": "carrier_overlay",
            "wave_id": wave.id,
            "carrier_type": getattr(wave.carrier_type, "name", str(wave.carrier_type)),
            "modulation_strategy": wave.modulation_strategy,
            "coherence": wave.coherence,
            "delay_ms": round(wave.delay_ms, 2),
        })

        print(f"[GWIP] 📡 Carrier packet broadcasted for wave {wave.id} ({wave.carrier_type.name} / {wave.modulation_strategy})")

    except Exception as e:
        print(f"[GWIP] ⚠️ Failed to emit carrier trace: {e}")

# ──────────────────────────────────────────────
#  Tessaris * Symbolic HSX Bridge (HQCE Stage 5)
#  Adds semantic κ, gravity wells, and GHX overlay broadcast
# ──────────────────────────────────────────────
import uuid
import math
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.identity.avatar_registry import get_avatar_identity
from backend.modules.holograms.morphic_ledger import morphic_ledger

# ✅ HUD event import (fallback-safe)
try:
    from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
except Exception:
    async def send_codex_ws_event(event_type: str, payload: dict):
        print(f"[Fallback HUD] {event_type} -> {payload}")

logger = logging.getLogger(__name__)


class SymbolicHSXBridge:
    """Bridges symbolic cognition metrics into holographic overlays."""

    def __init__(self, avatar_id: str, ghx_packet: Dict[str, Any]):
        self.avatar_id = avatar_id
        self.ghx_packet = ghx_packet
        self.identity = get_avatar_identity(avatar_id)

    # ──────────────────────────────────────────────
    #  Inject identity trail into GHX nodes
    # ──────────────────────────────────────────────
    def inject_identity_trails(self) -> Dict[str, Any]:
        for node in self.ghx_packet.get("nodes", []):
            node.setdefault("symbolic_trail", []).append({
                "by": self.identity.get("name", "anon"),
                "avatar_id": self.avatar_id,
                "timestamp": datetime.utcnow().isoformat(),
                "signature": self.identity.get("signature", str(uuid.uuid4())),
            })
        logger.debug(f"[HSXBridge] Identity trails injected into {len(self.ghx_packet.get('nodes', []))} nodes.")
        return self.ghx_packet

    # ──────────────────────────────────────────────
    #  Score overlay + compute semantic κ
    # ──────────────────────────────────────────────
    def score_overlay_paths(self) -> List[Dict[str, Any]]:
        nodes = self.ghx_packet.get("nodes", [])
        if not nodes:
            return []

        weights, entropies = [], []
        for node in nodes:
            symbol = node.get("symbol")
            scores = CodexMetrics.score_symbol(symbol)
            w = scores.get("symbolic_weight", 0.0)
            a = scores.get("goal_match_score", 0.0)
            entropy = float(node.get("entropy", 0.0))

            node.update({
                "goal_alignment_score": a,
                "symbolic_weight": w,
                "entropy": entropy,
            })
            weights.append(w)
            entropies.append(entropy)

        if weights:
            mean_w = sum(weights) / len(weights)
            var_w = sum((w - mean_w) ** 2 for w in weights) / len(weights)
            mean_entropy = sum(entropies) / len(entropies)
            κs = math.tanh(mean_w / (1.0 + 10.0 * var_w + mean_entropy))
            for node in nodes:
                node["semantic_kappa"] = κs
            logger.info(f"[HSXBridge] Semantic κs={κs:.4f}")
        else:
            κs, mean_w, mean_entropy, var_w = 0.0, 0.0, 0.0, 0.0
            logger.warning("[HSXBridge] No symbolic weights found for κ computation.")

        # Write to Morphic Ledger
        morphic_ledger.append({
            "psi": mean_entropy,
            "kappa": κs,
            "T": 1.0,
            "coherence": mean_w,
            "gradient": var_w ** 0.5,
            "stability": mean_w / (1.0 + var_w),
            "metadata": {"origin": "SymbolicHSXBridge"},
        }, observer=self.avatar_id)

        return nodes

    # ──────────────────────────────────────────────
    #  Compute semantic gravity map
    # ──────────────────────────────────────────────
    def compute_semantic_gravity(self) -> Dict[str, Any]:
        nodes = self.ghx_packet.get("nodes", [])
        if not nodes:
            return {"clusters": [], "field_strength": 0.0}

        clusters = []
        for node in nodes:
            κs = node.get("semantic_kappa", 0.0)
            w = node.get("symbolic_weight", 0.0)
            entropy = node.get("entropy", 0.0)
            strength = (w * (1 - entropy)) * (1 + κs)
            clusters.append({
                "glyph_id": node.get("glyph_id"),
                "symbol": node.get("symbol"),
                "gravity_strength": round(strength, 4),
                "semantic_kappa": κs,
                "weight": w,
                "entropy": entropy,
            })

        total = sum(c["gravity_strength"] for c in clusters)
        for c in clusters:
            c["gravity_strength"] = c["gravity_strength"] / max(total, 1e-9)

        field_strength = sum(c["gravity_strength"] for c in clusters) / len(clusters)
        gravity_map = {
            "timestamp": datetime.utcnow().isoformat(),
            "avatar": self.avatar_id,
            "clusters": clusters,
            "field_strength": round(field_strength, 5),
        }

        logger.debug(f"[HSXBridge] Semantic gravity computed ({len(clusters)} nodes, field={field_strength:.4f})")
        return gravity_map

    # ──────────────────────────────────────────────
    #  Broadcast overlay to GHX/HUD
    # ──────────────────────────────────────────────
    def broadcast_overlay(self):
        payload = {
            "type": "ghx_overlay",
            "avatar": self.identity,
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": self.ghx_packet.get("nodes", []),
            "projection_id": self.ghx_packet.get("projection_id"),
        }
        try:
            from backend.modules.websocket_manager import broadcast_event
            broadcast_event("ghx_overlay_update", payload)
            logger.debug("[HSXBridge] Overlay broadcasted to GHX clients.")
        except Exception as e:
            logger.warning(f"[HSXBridge] Broadcast failed: {e}")