from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _num(x: Any, d: float = 0.0) -> float:
    try:
        v = float(x)
        if v != v:  # NaN
            return d
        return v
    except Exception:
        return d

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

def _avg(xs: List[float]) -> float:
    return sum(xs) / max(1, len(xs))


def gx1_to_qfc_frame(gx1_out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort mapping from GX1 outputs -> QFCFrame.

    This makes the QFC display "mean something" immediately:
      - kappa = coherence_mean (0..1)
      - sigma = drift (0..1-ish, clamped)
      - coupling_score = rho_primary-ish (0..1)
      - topo_gate01 = pass fraction or SQI gate (0..1)
      - topology = minimal graph over scenarios (nodes=scenarios, edges=chain)

    Later you can replace topology with SQI/KG-driven topology.
    """
    metrics = gx1_out.get("metrics") or gx1_out.get("METRICS") or {}
    trace = gx1_out.get("trace") or gx1_out.get("TRACE") or []

    # Prefer SIM summaries if available (your sim core produces scenario_summaries inside payloads)
    payload = gx1_out
    sim = payload.get("sim") or payload.get("sim_core") or payload.get("sim_result") or {}

    scenario_summaries = sim.get("scenario_summaries") or metrics.get("scenario_summaries") or {}
    if isinstance(scenario_summaries, dict) and scenario_summaries:
        coh = [_num(v.get("coherence_mean"), 0.0) for v in scenario_summaries.values() if isinstance(v, dict)]
        drf = [_num(v.get("drift_mean"), 0.0) for v in scenario_summaries.values() if isinstance(v, dict)]
        rho = [_num(v.get("rho_primary"), 0.0) for v in scenario_summaries.values() if isinstance(v, dict)]
        kappa = _clamp01(_avg(coh) if coh else 0.0)
        sigma = _clamp01(_avg(drf) if drf else 0.0)
        coupling = _clamp01(_avg(rho) if rho else 0.0)
        sids = list(scenario_summaries.keys())
    else:
        # fall back to anything present
        kappa = _clamp01(_num(metrics.get("coherence_mean"), 0.0))
        sigma = _clamp01(_num(metrics.get("drift_mean"), 0.0))
        coupling = _clamp01(_num(metrics.get("rho_primary"), 0.0))
        sids = []

    # gates: if metrics has pass/fail, use it; else use kappa threshold-ish
    status = str(gx1_out.get("status") or metrics.get("status") or "UNKNOWN").upper()
    topo_gate01 = 1.0 if status in ("OK", "PASS", "PASSED", "CERTIFIED") else _clamp01(kappa)

    # minimal topology over scenarios (chain)
    nodes = [{"id": sid, "w": 1.0} for sid in sids] if sids else [{"id": "run", "w": 1.0}]
    edges = []
    for i in range(len(nodes) - 1):
        edges.append({"a": nodes[i]["id"], "b": nodes[i + 1]["id"], "w": 1.0})

    topology = {
        "epoch": int(_num(metrics.get("epoch"), 0.0)) if metrics else 0,
        "nodes": nodes,
        "edges": edges,
        "gate": topo_gate01,
    }

    frame = {
        "t": _num(metrics.get("t_ms"), 0.0) or 0.0,
        "kappa": kappa,
        "sigma": sigma,
        "alpha": _clamp01(coupling),     # reuse as a driver until you add a richer scalar
        "coupling_score": coupling,
        "topology": topology,
        "topo_gate01": topo_gate01,
        "mode": "genome",                # so QFCViewport can select QFCDemoGenome if desired
    }

    return frame
