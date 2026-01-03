# File: backend/modules/visualization/qfc_websocket_bridge.py

import asyncio
import inspect
from typing import Any, Dict, List, Optional, Union
import time
from fastapi import WebSocket

from backend.modules.websocket_manager import websocket_manager
from backend.modules.sim.QFC_Renderer import QFCRenderer

# Optional: real dynamics engine that produces the HUD metrics QFCRenderer expects.
# If the engine module isn't present yet, we gracefully degrade to "renderer-only".
try:
    from backend.modules.sim.qfc_engine import QFCEngine  # type: ignore
except Exception:
    QFCEngine = None  # type: ignore


# one renderer per container (keeps smooth transitions + event history)
_QFC_RENDERERS: Dict[str, QFCRenderer] = {}
_QFC_LAST_TS: Dict[str, float] = {}

# one engine per container (keeps real sim state)
_QFC_ENGINES: Dict[str, Any] = {}

# 🌐 Track container-specific sockets (live sync)
active_qfc_sockets: Dict[str, WebSocket] = {}


# 🔐 Safe coercion for hashable/loggable source values
def coerce_source(value: Any) -> str:
    """
    Convert any value to a string suitable for source tagging.
    Falls back to hash/id for non-serializable objects.
    """
    try:
        if isinstance(value, (dict, list)):
            return f"invalid_source_{hash(str(value))}"
        return str(value)
    except Exception:
        return f"invalid_source_{id(value)}"


def _safe_dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _decorate_qfc_payload(container_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Takes whatever you're already sending to the UI and adds:
      payload["mode"], payload["theme"], payload["flags"]
    without removing anything.

    IMPORTANT:
    - If a real QFC engine is available, we synthesize/complete the metric keys that QFCRenderer expects:
        kappa, chi, sigma, alpha, curv, curl_rms, coupling_score, max_norm
      so the renderer is never "dead" due to missing metrics.
    """
    if not isinstance(payload, dict):
        return payload

    # scenario id can be in different keys depending on route
    scenario_id = (
        payload.get("scenario_id")
        or payload.get("scenario")
        or payload.get("scenarioId")
        or payload.get("scenarioID")
        or ""
    )

    # metrics might be top-level or nested
    metrics = payload.get("metrics")
    if isinstance(metrics, dict):
        metrics_dict = metrics
    else:
        # preserve legacy behavior: treat top-level payload as metrics dict
        metrics_dict = payload

    # dt for smoothing + engine step
    now = time.time()
    last = _QFC_LAST_TS.get(container_id, now)
    _QFC_LAST_TS[container_id] = now
    dt = max(0.0, min(0.25, now - last))  # clamp dt to avoid crazy jumps

    # prefer numeric t if present
    t_val = payload.get("t")
    try:
        t_num = float(t_val)
    except Exception:
        t_num = now

    # ------------------------------------------------------------------
    # REAL SIM METRICS (if engine exists): synthesize/complete HUD keys
    # ------------------------------------------------------------------
    if QFCEngine is not None:
        eng = _QFC_ENGINES.get(container_id)
        if eng is None:
            try:
                eng = QFCEngine()
            except Exception:
                eng = None
            if eng is not None:
                _QFC_ENGINES[container_id] = eng

        if eng is not None:
            # If caller already provides sigma (or nested metrics.sigma), let it drive the gate.
            sigma_in = None
            if "sigma" in metrics_dict:
                sigma_in = metrics_dict.get("sigma")
            elif isinstance(payload.get("sigma"), (int, float, str)):
                sigma_in = payload.get("sigma")

            if sigma_in is not None:
                try:
                    eng.set_sigma(_safe_float(sigma_in, 0.0))
                except Exception:
                    pass

            # Step engine and fill any missing metric keys.
            try:
                sim_metrics = eng.step(dt)
                if isinstance(sim_metrics, dict):
                    for k, v in sim_metrics.items():
                        # Do NOT overwrite explicit caller values; only fill gaps.
                        if k not in metrics_dict:
                            metrics_dict[k] = v
            except Exception:
                # engine errors must never break the websocket path
                pass

    # ------------------------------------------------------------------
    # RENDERER (palette/flags): always runs once metrics exist (or defaults)
    # ------------------------------------------------------------------
    r = _QFC_RENDERERS.get(container_id)
    if r is None:
        r = QFCRenderer()
        _QFC_RENDERERS[container_id] = r

    # mode hint if you already send it
    mode_hint = payload.get("mode")

    out = r.update(
        t=t_num,
        scenario_id=str(scenario_id),
        metrics=metrics_dict,
        dt=dt,
        mode_hint=str(mode_hint) if mode_hint else None,
    )

    # Merge render fields in WITHOUT deleting your existing keys.
    payload["mode"] = out.get("mode")
    payload["theme"] = out.get("theme")
    payload["flags"] = out.get("flags")

    # optional: also ensure these exist at top-level for frontend convenience
    for k in ("kappa", "chi", "sigma", "alpha", "curv", "curl_rms", "coupling_score", "max_norm", "t"):
        if k in out and k not in payload:
            payload[k] = out[k]

    # If metrics were nested, keep them updated for downstream consumers.
    if isinstance(payload.get("metrics"), dict):
        payload["metrics"].update({k: payload[k] for k in ("kappa", "chi", "sigma", "alpha", "curv",
                                                          "curl_rms", "coupling_score", "max_norm")
                                   if k in payload})

    return payload


def _extract_container_id(field_state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Best-effort container_id extraction, matching the shapes seen in QQC logs + field packets.
    """
    if isinstance(metadata, dict):
        cid = metadata.get("container_id")
        if isinstance(cid, str) and cid:
            return cid

    cid2 = field_state.get("container_id")
    if isinstance(cid2, str) and cid2:
        return cid2

    ctx = field_state.get("context")
    if isinstance(ctx, dict):
        cid3 = ctx.get("container_id")
        if isinstance(cid3, str) and cid3:
            return cid3

    meta = field_state.get("metadata")
    if isinstance(meta, dict) and isinstance(meta.get("context"), dict):
        cid4 = meta["context"].get("container_id")
        if isinstance(cid4, str) and cid4:
            return cid4

    return None


# 📡 Broadcast QFC update to all connected clients (via websocket_manager)
async def send_qfc_update(render_packet: Dict[str, Any]) -> None:
    """
    Send a symbolic update to all connected QFC WebSocket clients.

    Args:
        render_packet (Dict[str, Any]): Data payload containing QWave beams, glyphs, etc.
    """
    try:
        source = coerce_source(render_packet.get("source", "unknown"))

        payload = {
            "type": "qfc_update",
            "source": source,
            "payload": _safe_dict(render_packet.get("payload", {})),
        }

        # ✅ Correct argument order: message first, then tag via keyword
        await websocket_manager.broadcast(payload, tag="qfc_update")
        print("🚀 QFC WebSocket update broadcasted.")
    except Exception as e:
        print(f"❌ Failed to broadcast QFC update: {e}")


# 🧠 Register live QFC sync socket for a specific container
async def register_qfc_socket(container_id: str, websocket: WebSocket):
    """
    Accepts a WebSocket and registers it to a specific container ID.
    """
    await websocket.accept()
    active_qfc_sockets[container_id] = websocket
    print(f"🔌 WebSocket registered for QFC container: {container_id}")


# ❌ Unregister QFC sync socket
async def unregister_qfc_socket(container_id: str):
    if container_id in active_qfc_sockets:
        del active_qfc_sockets[container_id]
        print(f"🛑 WebSocket unregistered for QFC container: {container_id}")


async def _broadcast_container_sync(
    container_id: str,
    payload: Dict[str, Any],
    observer_id: Optional[str] = None,
    source: Optional[str] = None,
    **_kwargs: Any,
) -> None:
    """
    Internal: Send live QFC sync update to a specific container WebSocket.

    Compatible with callers that pass extra kwargs (e.g. observer_id/source).
    """
    socket = active_qfc_sockets.get(container_id)
    if not socket:
        return

    try:
        # ✅ decorate *right before* emit (adds mode/theme/flags + ensures metrics if engine exists)
        payload = _decorate_qfc_payload(container_id, payload)

        await socket.send_json(
            {
                "type": "qfc_update",
                "source": source or (observer_id or "container_sync"),
                "payload": _safe_dict(payload),
            }
        )
        print(f"📡 Live sync update sent to container: {container_id}")
    except Exception as e:
        print(f"❌ Failed to send live QFC sync: {e}")


def _is_coroutine_fn(fn: Any) -> bool:
    return inspect.iscoroutinefunction(fn)


def safe_fire_and_forget(coro_or_fn, *args, **kwargs):
    """
    Execute a coroutine or function safely without awaiting.
    Falls back to asyncio.run if no running loop exists.
    """
    try:
        if _is_coroutine_fn(coro_or_fn):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro_or_fn(*args, **kwargs))
            except RuntimeError:
                asyncio.run(coro_or_fn(*args, **kwargs))
        else:
            coro_or_fn(*args, **kwargs)
    except Exception as e:
        print(f"⚠️ QFC Bridge fallback dispatch failed: {e}")


# 🌈 Stream symbolic beam updates to all clients (non-container specific)
def broadcast_qfc_beams(container_id: str, payload: Union[Dict[str, Any], List[Dict[str, Any]]]):
    """
    Broadcast multi-packet QFC visual data (e.g. QWave beams, traces) to the frontend.
    Bypasses container-specific WebSocket and goes to all clients via `send_qfc_update`.
    """
    if not isinstance(payload, list):
        payload = [payload]

    decorated_updates: List[Dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            decorated_updates.append(_decorate_qfc_payload(container_id, item))
        else:
            decorated_updates.append(item)  # type: ignore

    message = {
        "source": f"container::{container_id}",
        "payload": {
            "updates": decorated_updates,
            "type": "qfc_stream",
        },
    }

    safe_fire_and_forget(send_qfc_update, message)


# ───────────────────────────────────────────────
# 🛠 Optional helper: broadcast QPU / CPU metrics live
# ───────────────────────────────────────────────
def broadcast_cpu_qpu_metrics(container_id: str, metrics: Dict[str, Any], cpu: bool = False):
    """
    Send CPU or QPU benchmark / execution metrics to frontend.
    """
    metric_type = "cpu_metrics" if cpu else "qpu_metrics"
    payload = {
        "type": metric_type,
        "metrics": metrics,
    }
    safe_fire_and_forget(broadcast_qfc_beams, container_id, payload)


# ───────────────────────────────────────────────
# ✅ Main bridge entrypoint (BACKWARD + FORWARD compatible)
# ───────────────────────────────────────────────
async def broadcast_qfc_update(*args: Any, **kwargs: Any):
    """
    Backward compatible AND forward compatible entrypoint.

    Supports legacy live-sync:
        await broadcast_qfc_update(container_id: str, payload: Dict[str, Any])

    Supports newer callers (Codex hooks):
        await broadcast_qfc_update(
            field_state=Dict[str, Any],
            observer_id=str,
            event_type=str,
            metadata=Dict[str, Any],
            container_id=str,
        )

    New-style routes to backend.modules.sci.qfc_ws_broadcaster.broadcast_qfc_state
    so you keep the Codex WS event pipeline consistent.
    """

    # -----------------------------
    # New-style detection
    # -----------------------------
    field_state = kwargs.get("field_state")
    if field_state is None and len(args) >= 1 and isinstance(args[0], dict):
        field_state = args[0]

    if isinstance(field_state, dict):
        observer_id = kwargs.get("observer_id")
        event_type = kwargs.get("event_type")
        metadata = kwargs.get("metadata")
        container_id = kwargs.get("container_id")

        if not isinstance(observer_id, str) or not observer_id:
            observer_id = None
        if not isinstance(event_type, str) or not event_type:
            event_type = None
        if not isinstance(metadata, dict):
            metadata = None
        if not isinstance(container_id, str) or not container_id:
            container_id = _extract_container_id(field_state, metadata)

        # Prefer the canonical broadcaster (Codex WS event pipeline)
        try:
            from backend.modules.sci.qfc_ws_broadcaster import broadcast_qfc_state  # lazy import
            await broadcast_qfc_state(
                field_state=field_state,
                observer_id=observer_id,
                event_type=event_type,
                metadata=metadata,
                container_id=container_id,
            )
            return
        except Exception as e:
            # Fallback: still get *something* to the UI
            try:
                cid = container_id or "unknown"
                broadcast_qfc_beams(
                    cid,
                    {
                        "type": "qfc_field_update",
                        "observer_id": observer_id or "anonymous",
                        "event_type": event_type or "qfc_field_update",
                        "metadata": metadata or {},
                        "field_state": field_state,
                    },
                )
            except Exception:
                pass
            print(f"⚠️ QFC bridge: broadcast_qfc_state failed (fallback used): {e}")
            return

    # -----------------------------
    # Legacy live-sync path
    # -----------------------------
    container_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    observer_id: Optional[str] = None
    source: Optional[str] = None

    if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], dict):
        container_id, payload = args[0], args[1]
        if len(args) >= 3 and isinstance(args[2], str):
            observer_id = args[2]
    else:
        cid = kwargs.get("container_id")
        pl = kwargs.get("payload")
        if isinstance(cid, str) and isinstance(pl, dict):
            container_id, payload = cid, pl

    if isinstance(kwargs.get("observer_id"), str):
        observer_id = kwargs["observer_id"]
    if isinstance(kwargs.get("source"), str):
        source = kwargs["source"]

    if container_id and isinstance(payload, dict):
        payload = _decorate_qfc_payload(container_id, payload)

        await _broadcast_container_sync(
            container_id,
            payload,
            observer_id=observer_id,
            source=source,
            **kwargs,
        )
        return

    return