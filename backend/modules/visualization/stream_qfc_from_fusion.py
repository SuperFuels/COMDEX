from __future__ import annotations

import asyncio
import json
import math
from typing import Any, Dict, Optional

import websockets

from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update

FUSION_WS = "ws://localhost:8005/ws/fusion"


def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        x = float(v)
        if not math.isfinite(x):
            return default
        return x
    except Exception:
        return default


def fusion_to_qfc_metrics(pkt: Dict[str, Any]) -> Dict[str, Any]:
    # TCFK canonical fields
    stability = fnum(pkt.get("sigma", pkt.get("stability", pkt.get("σ"))), 1.0)          # σ
    coherence = fnum(pkt.get("coherence", pkt.get("fusion_coherence", 1.0)), 1.0)
    psi = fnum(pkt.get("cognition_signal", pkt.get("psi_tilde", pkt.get("ψ̃"))), 0.0)   # ψ̃

    curl_rms = fnum(pkt.get("curl_rms", pkt.get("kappa_tilde", pkt.get("κ̃"))), 0.0)    # κ̃
    coupling = fnum(pkt.get("coupling_score", pkt.get("gamma_tilde", pkt.get("γ̃"))), 1.0)  # γ̃
    curv = fnum(pkt.get("curv", 0.0), 0.0)
    max_norm = fnum(pkt.get("max_norm", 0.0), 0.0)

    # Derived QFC fields expected by renderer / shader demos
    sigma = clamp01(stability)
    chi = clamp01(abs(psi))                          # drive “pinch”
    alpha = clamp01(coherence)                       # drive “opacity/energy”
    kappa = clamp01(0.6 * sigma + 0.4 * alpha)       # stable synthetic kappa if missing

    return {
        "kappa": kappa,
        "chi": chi,
        "sigma": sigma,
        "alpha": alpha,
        "curv": clamp01(curv) if curv <= 1.5 else curv,  # keep sane if someone sends >1
        "curl_rms": max(0.0, curl_rms),
        "coupling_score": clamp01(coupling),
        "max_norm": max(0.0, max_norm),
        # helpful for mode selection
        "scenario_id": "SYNC_FUSION",
        # keep originals if UI wants them
        "stability": stability,
        "coherence": coherence,
        "cognition_signal": psi,
    }


async def run_fusion_bridge(*, container_id: str = "fusion::global") -> None:
    backoff = 1.0
    while True:
        try:
            async with websockets.connect(FUSION_WS, ping_interval=20, ping_timeout=20) as ws:
                backoff = 1.0
                async for msg in ws:
                    try:
                        pkt = json.loads(msg)
                    except Exception:
                        continue
                    if not isinstance(pkt, dict):
                        continue

                    metrics = fusion_to_qfc_metrics(pkt)

                    # Legacy path: (container_id, payload) works with your bridge
                    await broadcast_qfc_update(container_id, metrics)

        except Exception as e:
            print(f"[fusion->qfc] disconnected: {e} (retry in {backoff:.1f}s)")
            await asyncio.sleep(backoff)
            backoff = min(10.0, backoff * 1.6)


if __name__ == "__main__":
    asyncio.run(run_fusion_bridge())