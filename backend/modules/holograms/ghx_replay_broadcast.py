import json
import time

from backend.modules.websocket_manager import broadcast_event
from backend.modules.symbolic.symbol_tree_generator import SymbolicMeaningTree
from backend.modules.sqi.metrics_bus import metrics_bus
from backend.modules.symbolic.decoherence import calc_decoherence

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
                    print("[GWV] ❌ No private key found in Vault — cannot sign snapshot.")
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