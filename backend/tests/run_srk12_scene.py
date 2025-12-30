#!/usr/bin/env python3
"""
SRK-12 Governed Selection Scene Runner (reference deterministic evidence)

Reads:
  - docs/Artifacts/SRK12/qfc/SRK12_GOVERNED_SELECTION.scene.json
  - docs/Artifacts/SRK12/build/SRK12_ACCEPTANCE_THRESHOLDS.yaml
  - docs/Artifacts/SRK12/ledger/SRK12_GOVERNED_SELECTION_TRACE_SCHEMA.json

Writes:
  - docs/Artifacts/SRK12/ledger/SRK12_LINT_PROOF.log
  - docs/Artifacts/SRK12/ledger/SRK12_METRICS.json
  - docs/Artifacts/SRK12/ledger/SRK12_GOVERNED_SELECTION_TRACE.jsonl   (single event)

Validation intent:
  - Deterministic replay: for this scene we FORCE selection to the argmax branch.
  - Policy modulation: if label == "Contradictory" and status_bonus < 0, HARD-ZERO weight
    (matches your SRK12_ACCEPTANCE_THRESHOLDS.yaml comment).
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


REPO = Path("/workspaces/COMDEX")

SCENE_PATH = REPO / "docs/Artifacts/SRK12/qfc/SRK12_GOVERNED_SELECTION.scene.json"
THRESH_PATH = REPO / "docs/Artifacts/SRK12/build/SRK12_ACCEPTANCE_THRESHOLDS.yaml"
SCHEMA_PATH = REPO / "docs/Artifacts/SRK12/ledger/SRK12_GOVERNED_SELECTION_TRACE_SCHEMA.json"

OUT_LOG = REPO / "docs/Artifacts/SRK12/ledger/SRK12_LINT_PROOF.log"
OUT_METRICS = REPO / "docs/Artifacts/SRK12/ledger/SRK12_METRICS.json"
OUT_TRACE = REPO / "docs/Artifacts/SRK12/ledger/SRK12_GOVERNED_SELECTION_TRACE.jsonl"

SRK8_LEDGER_REPAIRED = REPO / "docs/Artifacts/SRK8/ledger/theorem_ledger_repaired.jsonl"


@dataclass
class Branch:
    name: str
    label: str
    amplitude: float
    phase: float
    status_bonus: float

    def born_weight(self) -> float:
        # Born weight = |amp|^2
        return float(self.amplitude) ** 2


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def load_yaml(p: Path) -> Any:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def l1_dist(a: List[float], b: List[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b))


def normalize(weights: List[float]) -> Tuple[List[float], float]:
    s = sum(weights)
    if s <= 0.0:
        # avoid division by zero; return all zeros (should FAIL thresholds)
        return [0.0 for _ in weights], s
    return [w / s for w in weights], s


def policy_modulate(branches: List[Branch]) -> List[float]:
    """
    Deterministic policy modulation consistent with your thresholds:

    - Base weights: w_i = |amp|^2
    - If label == "Contradictory" AND status_bonus < 0: w_i' = 0  (hard suppression)
    - Else: w_i' = max(0, w_i * (1 + status_bonus))
      (mild bias, clamped)
    """
    out: List[float] = []
    for b in branches:
        w = b.born_weight()
        if b.label.lower() == "contradictory" and b.status_bonus < 0:
            out.append(0.0)
            continue
        out.append(max(0.0, w * (1.0 + b.status_bonus)))
    return out


def main() -> int:
    scene = load_json(SCENE_PATH)
    thr = load_yaml(THRESH_PATH)
    _schema = load_json(SCHEMA_PATH)  # we don't enforce schema structurally here; we emit matching keys.

    # Basic repo evidence: SRK-8 repaired ledger must exist and be non-empty
    if thr.get("ledger_dependency", {}).get("require_srk8_repaired_ledger_present", False):
        if not SRK8_LEDGER_REPAIRED.exists():
            raise FileNotFoundError(f"missing SRK-8 repaired ledger: {SRK8_LEDGER_REPAIRED}")
        if thr.get("ledger_dependency", {}).get("require_nonempty_hashes", False):
            if SRK8_LEDGER_REPAIRED.stat().st_size == 0:
                raise ValueError(f"SRK-8 repaired ledger is empty: {SRK8_LEDGER_REPAIRED}")

    branches_in = scene["inputs"]["branches"]
    branches: List[Branch] = [
        Branch(
            name=b["name"],
            label=b.get("label", ""),
            amplitude=float(b.get("amplitude", 0.0)),
            phase=float(b.get("phase", 0.0)),
            status_bonus=float(b.get("status_bonus", 0.0)),
        )
        for b in branches_in
    ]

    # Born baseline
    w_before = [b.born_weight() for b in branches]
    p_before, sum_before = normalize(w_before)

    # Policy modulation + renormalize
    w_after = policy_modulate(branches)

    # must_renormalize_after_modulation
    p_after, sum_after = normalize(w_after)
    renormalized = sum_after > 0.0

    # Deterministic selection: force argmax (so replay is guaranteed)
    max_idx = max(range(len(p_after)), key=lambda i: p_after[i])
    selected = branches[max_idx].name

    determinism_ratio = (max(p_after) / sum(p_after)) if sum(p_after) > 0 else 0.0
    renorm_delta_l1 = l1_dist(p_after, p_before)

    # Threshold checks
    ok = True
    reasons: List[str] = []

    det = thr.get("deterministic_replay", {})
    policy = thr.get("policy_modulation", {})

    determinism_min = float(det.get("determinism_ratio_min", 0.0))
    if determinism_ratio < determinism_min:
        ok = False
        reasons.append(f"determinism_ratio {determinism_ratio:.12g} < {determinism_min:.12g}")

    # contradiction_prob_after_max
    contr_max = float(policy.get("contradiction_prob_after_max", 1.0))
    for i, b in enumerate(branches):
        if b.label.lower() == "contradictory":
            if p_after[i] > contr_max:
                ok = False
                reasons.append(f"contradiction prob_after {p_after[i]:.12g} > {contr_max:.12g}")

    # Build trace event (single JSONL line)
    trace_event: Dict[str, Any] = {
        "timestamp": utc_now_iso(),
        "wavecapsule_id": scene.get("scene", "SRK12_GOVERNED_SELECTION"),
        "branches": [
            {
                "name": b.name,
                "symbol": b.name,
                "amp": b.amplitude,
                "phase": b.phase,
                "born_weight": w_before[i],
                "status_bonus": b.status_bonus,
                "policy_tags": [b.label] if b.label else [],
                "prob_before": p_before[i],
                "prob_after": p_after[i],
            }
            for i, b in enumerate(branches)
        ],
        "normalization": {
            "sum_prob_after": float(sum_after),
            "renormalized": bool(renormalized),
        },
        "decision": {
            "selected_branch": selected,
            "selection_determinism_ratio": float(determinism_ratio),
        },
    }

    metrics: Dict[str, Any] = {
        "scene": scene.get("scene"),
        "lock_id": "SRK-12-PHOTON-ALGEBRA-v1.1",
        "timestamp": trace_event["timestamp"],
        "prob_before": p_before,
        "prob_after": p_after,
        "weights_before": w_before,
        "weights_after": w_after,
        "sum_before": float(sum_before),
        "sum_after": float(sum_after),
        "selected_branch": selected,
        "SELECTION_DETERMINISM_RATIO": float(determinism_ratio),
        "RENORMALIZATION_DELTA_L1": float(renorm_delta_l1),
        "pass": bool(ok),
        "fail_reasons": reasons,
    }

    # Write outputs
    ensure_parent(OUT_LOG)
    ensure_parent(OUT_METRICS)
    ensure_parent(OUT_TRACE)

    OUT_TRACE.write_text(json.dumps(trace_event) + "\n", encoding="utf-8")
    OUT_METRICS.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Human-readable evidence log
    status_str = "PASS" if ok else "FAIL"
    log = []
    log.append("# SRK12_LINT_PROOF.log")
    log.append("# Evidence log for SRK-12 governed selection scene + thresholds.")
    log.append("")
    log.append(f"LOCK_ID: SRK-12-PHOTON-ALGEBRA-v1.1")
    log.append(f"SCENE: {scene.get('scene')}")
    log.append(f"STATUS: {status_str}")
    log.append(f"TIMESTAMP_UTC: {trace_event['timestamp']}")
    log.append("")
    log.append("METRICS:")
    log.append(f"  selected_branch: {selected}")
    log.append(f"  SELECTION_DETERMINISM_RATIO: {determinism_ratio:.12g}")
    log.append(f"  RENORMALIZATION_DELTA_L1: {renorm_delta_l1:.12g}")
    log.append(f"  prob_before: {p_before}")
    log.append(f"  prob_after:  {p_after}")
    log.append("")
    log.append("ARTIFACTS_WRITTEN:")
    log.append(f"  - {OUT_LOG}")
    log.append(f"  - {OUT_METRICS}")
    log.append(f"  - {OUT_TRACE}")
    log.append("")
    log.append("THRESHOLDS:")
    log.append(f"  determinism_ratio_min: {determinism_min}")
    log.append(f"  contradiction_prob_after_max: {contr_max}")
    if not ok:
        log.append("")
        log.append("FAIL_REASONS:")
        for r in reasons:
            log.append(f"  - {r}")
    log.append("")

    OUT_LOG.write_text("\n".join(log), encoding="utf-8")

    print(f"[{status_str}] wrote: {OUT_LOG}")
    print(f"        wrote: {OUT_METRICS}")
    print(f"        wrote: {OUT_TRACE}")
    print(f"        selected={selected} determinism={determinism_ratio:.12g} renorm_L1={renorm_delta_l1:.12g}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())