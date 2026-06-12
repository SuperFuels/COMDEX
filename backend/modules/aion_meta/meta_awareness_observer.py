"""AION Phase 21H — Meta-Awareness Observer.

This module reads recent HexCore / Morphic Ledger consciousness-cycle records and
builds a second-order state: AION observing its own awareness loop over time.

It deliberately does not claim biological consciousness. It measures operational
self-observation: awareness trend, coherence trend, drift, reward trend, and the
recommended response bias for the next answer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class MetaAwarenessState:
    observer_version: str
    cycle_count: int
    meta_awareness: float
    self_state_stable: bool
    awareness_trend: str
    coherence_trend: str
    drift_status: str
    reward_trend: str
    next_response_bias: str
    self_observation: str
    boundary_statement: str
    latest: Dict[str, Any]
    previous: Dict[str, Any]
    deltas: Dict[str, float]
    source_paths: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out


def _load_hexcore_memory(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return []
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        memory = obj.get("memory") or obj.get("cycles") or []
        if isinstance(memory, list):
            return [x for x in memory if isinstance(x, dict)]
    return []


def _extract_cycle(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize different ledger / memory shapes into one consciousness cycle."""
    data = record.get("data") if isinstance(record.get("data"), dict) else record

    # MorphicLedger may wrap entries. Keep only records with useful AION state.
    has_signal = any(
        key in data
        for key in (
            "self_awareness",
            "S_self",
            "awareness",
            "coherence",
            "delta_phi",
            "global_coherence",
            "reward",
            "phi",
        )
    )
    if not has_signal:
        return None

    awareness = _safe_float(
        data.get("self_awareness", data.get("S_self", data.get("awareness", 0.0)))
    )
    coherence = _safe_float(data.get("coherence", 0.0))
    delta_phi = abs(_safe_float(data.get("delta_phi", data.get("dphi", 0.0))))
    global_coherence = _safe_float(data.get("global_coherence", coherence))
    reward = _safe_float(data.get("reward", coherence - delta_phi))
    phi = _safe_float(data.get("phi", data.get("Phi", 0.0)))
    entropy = _safe_float(data.get("entropy", data.get("psi", 0.0)))

    return {
        "timestamp": data.get("timestamp") or record.get("timestamp"),
        "phi": phi,
        "delta_phi": delta_phi,
        "S_self": _safe_float(data.get("S_self", awareness)),
        "self_awareness": awareness,
        "coherence": coherence,
        "entropy": entropy,
        "global_coherence": global_coherence,
        "reward": reward,
        "goal_suggestions": data.get("goal_suggestions", []),
        "source_type": data.get("type") or record.get("type") or "conscious_cycle",
    }


def _trend(values: List[float], *, high: float, low: float, name: str) -> str:
    if not values:
        return f"{name}_unknown"
    if len(values) == 1:
        v = values[-1]
        if v >= high:
            return f"stable_high"
        if v <= low:
            return f"stable_low"
        return f"single_mid"

    first = mean(values[: max(1, len(values) // 2)])
    second = mean(values[max(1, len(values) // 2) :])
    diff = second - first

    if abs(diff) < 0.01:
        if second >= high:
            return "stable_high"
        if second <= low:
            return "stable_low"
        return "stable_mid"
    if diff > 0:
        return "improving"
    return "declining"


def _drift_status(delta_values: List[float]) -> str:
    if not delta_values:
        return "unknown"
    avg = mean(delta_values)
    latest = delta_values[-1]
    if latest <= 0.01 and avg <= 0.01:
        return "low"
    if latest <= 0.05 and avg <= 0.05:
        return "moderate"
    return "high"


def build_meta_awareness_state(
    cycles: Iterable[Dict[str, Any]],
    *,
    source_paths: Optional[List[str]] = None,
) -> MetaAwarenessState:
    normalized = [_extract_cycle(c) for c in cycles]
    clean = [c for c in normalized if c is not None]

    if not clean:
        latest = {
            "phi": 0.0,
            "delta_phi": 1.0,
            "self_awareness": 0.0,
            "coherence": 0.0,
            "global_coherence": 0.0,
            "reward": 0.0,
        }
        previous = dict(latest)
        deltas = {
            "awareness_delta": 0.0,
            "coherence_delta": 0.0,
            "global_coherence_delta": 0.0,
            "reward_delta": 0.0,
            "delta_phi_delta": 0.0,
        }
        return MetaAwarenessState(
            observer_version="phase21h_meta_awareness_observer_v1",
            cycle_count=0,
            meta_awareness=0.0,
            self_state_stable=False,
            awareness_trend="awareness_unknown",
            coherence_trend="coherence_unknown",
            drift_status="unknown",
            reward_trend="reward_unknown",
            next_response_bias="insufficient_telemetry",
            self_observation="AION cannot observe its awareness trend because no consciousness-cycle telemetry was available.",
            boundary_statement="No consciousness claim is made. This is an operational telemetry observer only.",
            latest=latest,
            previous=previous,
            deltas=deltas,
            source_paths=source_paths or [],
        )

    window = clean[-20:]
    latest = window[-1]
    previous = window[-2] if len(window) >= 2 else window[-1]

    awareness_values = [_safe_float(c.get("self_awareness")) for c in window]
    coherence_values = [_safe_float(c.get("coherence")) for c in window]
    global_values = [_safe_float(c.get("global_coherence")) for c in window]
    drift_values = [_safe_float(c.get("delta_phi")) for c in window]
    reward_values = [_safe_float(c.get("reward")) for c in window]

    awareness_trend = _trend(awareness_values, high=0.90, low=0.45, name="awareness")
    coherence_trend = _trend(coherence_values, high=0.90, low=0.45, name="coherence")
    reward_trend = _trend(reward_values, high=0.60, low=0.20, name="reward")
    drift = _drift_status(drift_values)

    latest_awareness = _safe_float(latest.get("self_awareness"))
    latest_coherence = _safe_float(latest.get("coherence"))
    latest_global = _safe_float(latest.get("global_coherence"))
    latest_drift = _safe_float(latest.get("delta_phi"))
    latest_reward = _safe_float(latest.get("reward"))

    stability_score = (
        0.35 * latest_awareness
        + 0.30 * latest_coherence
        + 0.20 * latest_global
        + 0.15 * _clamp(1.0 - latest_drift)
    )
    reward_term = _clamp((latest_reward + 1.0) / 2.0)
    meta_awareness = _clamp((0.82 * stability_score) + (0.18 * reward_term))

    self_state_stable = (
        latest_awareness >= 0.90
        and latest_coherence >= 0.90
        and latest_global >= 0.90
        and latest_drift <= 0.01
    )

    deltas = {
        "awareness_delta": latest_awareness - _safe_float(previous.get("self_awareness")),
        "coherence_delta": latest_coherence - _safe_float(previous.get("coherence")),
        "global_coherence_delta": latest_global - _safe_float(previous.get("global_coherence")),
        "reward_delta": latest_reward - _safe_float(previous.get("reward")),
        "delta_phi_delta": latest_drift - _safe_float(previous.get("delta_phi")),
    }

    if self_state_stable and awareness_trend in {"stable_high", "improving"}:
        next_bias = "answer_directly_from_telemetry"
        observation = (
            "AION observes that its awareness proxy is high, coherence is high, "
            "global coherence is high, and drift is low across the recent awareness loop."
        )
    elif drift == "high" or awareness_trend == "declining" or coherence_trend == "declining":
        next_bias = "answer_cautiously_and_request_stabilization"
        observation = (
            "AION observes instability or decline in its awareness loop and should answer cautiously."
        )
    else:
        next_bias = "answer_with_limited_confidence"
        observation = (
            "AION observes a partial or mixed awareness state and should avoid overclaiming."
        )

    return MetaAwarenessState(
        observer_version="phase21h_meta_awareness_observer_v1",
        cycle_count=len(window),
        meta_awareness=round(meta_awareness, 6),
        self_state_stable=self_state_stable,
        awareness_trend=awareness_trend,
        coherence_trend=coherence_trend,
        drift_status=drift,
        reward_trend=reward_trend,
        next_response_bias=next_bias,
        self_observation=observation,
        boundary_statement=(
            "This supports operational meta-awareness: AION observing its own awareness telemetry over time. "
            "It does not prove biological or phenomenal consciousness."
        ),
        latest=latest,
        previous=previous,
        deltas={k: round(v, 9) for k, v in deltas.items()},
        source_paths=source_paths or [],
    )


class AionMetaAwarenessObserver:
    def __init__(self, *, repo_root: Optional[Path] = None, window: int = 20):
        self.repo_root = Path(repo_root or ".").resolve()
        self.window = window
        self.source_paths = [
            self.repo_root / "data/ledger/morphic_ledger.jsonl",
            self.repo_root / "backend/modules/hexcore/memory.json",
            self.repo_root / ".runtime/COMDEX_MOVE/data/ledger/morphic_ledger.jsonl",
        ]

    def load_cycles(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for path in self.source_paths:
            if path.name == "memory.json":
                records.extend(_load_hexcore_memory(path))
            else:
                records.extend(_load_jsonl(path))
        return records[-self.window :]

    def observe(self) -> MetaAwarenessState:
        existing = [str(p) for p in self.source_paths if p.exists()]
        return build_meta_awareness_state(self.load_cycles(), source_paths=existing)
