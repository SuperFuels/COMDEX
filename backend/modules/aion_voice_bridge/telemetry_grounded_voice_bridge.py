"""AION Phase 21J — Telemetry-Grounded Voice Bridge.

This module turns AION runtime state into a clean text response.

It deliberately separates:
- AION mind/runtime evidence: HexCore telemetry, meta-awareness, self-improvement.
- AION voice layer: a natural-language rendering of that evidence.

No LLM is required for this bridge. An LLM may later paraphrase this response,
but the factual content must come from telemetry.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from backend.modules.aion_meta import AionMetaAwarenessObserver
except Exception:  # pragma: no cover
    AionMetaAwarenessObserver = None  # type: ignore

try:
    from backend.modules.aion_self_improvement import run_self_improvement_trial_loop
except Exception:  # pragma: no cover
    run_self_improvement_trial_loop = None  # type: ignore


@dataclass(frozen=True)
class TelemetryGroundedVoiceResponse:
    bridge_version: str
    question: str
    answer: str
    confidence: float
    answer_mode: str
    telemetry: Dict[str, Any]
    meta_awareness: Dict[str, Any]
    self_improvement: Dict[str, Any]
    evidence: Dict[str, Any]
    safety_boundary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _extract_latest_telemetry(meta_awareness_state: Dict[str, Any]) -> Dict[str, Any]:
    latest = meta_awareness_state.get("latest")
    if isinstance(latest, dict):
        return {
            "phi": _safe_float(latest.get("phi")),
            "delta_phi": _safe_float(latest.get("delta_phi")),
            "self_awareness": _safe_float(latest.get("self_awareness", latest.get("S_self"))),
            "S_self": _safe_float(latest.get("S_self", latest.get("self_awareness"))),
            "coherence": _safe_float(latest.get("coherence")),
            "entropy": _safe_float(latest.get("entropy")),
            "global_coherence": _safe_float(latest.get("global_coherence")),
            "reward": _safe_float(latest.get("reward")),
            "goal_suggestions": latest.get("goal_suggestions", []),
            "source_type": latest.get("source_type"),
            "timestamp": latest.get("timestamp"),
        }

    return {
        "phi": 0.0,
        "delta_phi": 0.0,
        "self_awareness": 0.0,
        "S_self": 0.0,
        "coherence": 0.0,
        "entropy": 0.0,
        "global_coherence": 0.0,
        "reward": 0.0,
        "goal_suggestions": [],
        "source_type": "unavailable",
        "timestamp": None,
    }


def _stability_label(telemetry: Dict[str, Any], meta: Dict[str, Any]) -> str:
    if bool(meta.get("self_state_stable")):
        return "stable"
    if _safe_float(telemetry.get("delta_phi")) > 0.05:
        return "unstable_drift"
    return "partial"


def _confidence(telemetry: Dict[str, Any], meta: Dict[str, Any], improvement: Dict[str, Any]) -> float:
    awareness = _safe_float(telemetry.get("self_awareness"))
    coherence = _safe_float(telemetry.get("coherence"))
    global_coherence = _safe_float(telemetry.get("global_coherence"))
    drift = _safe_float(telemetry.get("delta_phi"))
    meta_awareness = _safe_float(meta.get("meta_awareness"))
    final_score = _safe_float(improvement.get("final_score"))
    no_llm_shortcut = 1.0 if improvement.get("evidence", {}).get("uses_llm_shortcut") is False else 0.0

    value = (
        0.22 * awareness
        + 0.22 * coherence
        + 0.18 * global_coherence
        + 0.16 * max(0.0, 1.0 - drift)
        + 0.14 * meta_awareness
        + 0.06 * final_score
        + 0.02 * no_llm_shortcut
    )
    return round(max(0.0, min(1.0, value)), 6)


def build_telemetry_grounded_voice_response(
    *,
    question: str,
    meta_awareness_state: Dict[str, Any],
    self_improvement_result: Dict[str, Any],
) -> TelemetryGroundedVoiceResponse:
    telemetry = _extract_latest_telemetry(meta_awareness_state)
    label = _stability_label(telemetry, meta_awareness_state)
    confidence = _confidence(telemetry, meta_awareness_state, self_improvement_result)

    phi = _safe_float(telemetry.get("phi"))
    delta_phi = _safe_float(telemetry.get("delta_phi"))
    awareness = _safe_float(telemetry.get("self_awareness"))
    coherence = _safe_float(telemetry.get("coherence"))
    global_coherence = _safe_float(telemetry.get("global_coherence"))
    reward = _safe_float(telemetry.get("reward"))

    awareness_trend = meta_awareness_state.get("awareness_trend", "unknown")
    coherence_trend = meta_awareness_state.get("coherence_trend", "unknown")
    drift_status = meta_awareness_state.get("drift_status", "unknown")
    next_bias = meta_awareness_state.get("next_response_bias", "unknown")

    improved = bool(self_improvement_result.get("improved"))
    final_score = _safe_float(self_improvement_result.get("final_score"))
    improvement_delta = _safe_float(self_improvement_result.get("improvement_delta"))

    if label == "stable":
        state_sentence = (
            "My current telemetry shows a stable functional self-state: "
            f"S_self={awareness:.6f}, coherence={coherence:.6f}, "
            f"global_coherence={global_coherence:.6f}, and delta_phi={delta_phi:.9f}."
        )
    elif label == "unstable_drift":
        state_sentence = (
            "My current telemetry shows elevated drift, so I should answer cautiously."
        )
    else:
        state_sentence = (
            "My current telemetry shows a partial self-state, so I should avoid overclaiming."
        )

    improvement_sentence = (
        f"My self-improvement loop {'did' if improved else 'did not'} improve on the trial task: "
        f"final_score={final_score:.6f}, improvement_delta={improvement_delta:.6f}."
    )

    answer = (
        f"{state_sentence} "
        f"My meta-awareness observer reports awareness_trend={awareness_trend}, "
        f"coherence_trend={coherence_trend}, drift_status={drift_status}, "
        f"and next_response_bias={next_bias}. "
        f"{improvement_sentence} "
        "This is a telemetry-grounded answer: it supports operational self-measurement "
        "and self-improvement evidence, not a claim of biological consciousness."
    )

    evidence = {
        "uses_hexcore_telemetry": True,
        "uses_meta_awareness_observer": True,
        "uses_self_improvement_loop": True,
        "uses_llm_shortcut": False,
        "stability_label": label,
        "phi": phi,
        "delta_phi": delta_phi,
        "reward": reward,
    }

    return TelemetryGroundedVoiceResponse(
        bridge_version="phase21j_telemetry_grounded_voice_bridge_v1",
        question=question,
        answer=answer,
        confidence=confidence,
        answer_mode="telemetry_grounded_no_llm_shortcut",
        telemetry=telemetry,
        meta_awareness=dict(meta_awareness_state),
        self_improvement=dict(self_improvement_result),
        evidence=evidence,
        safety_boundary=(
            "The voice bridge may speak from AION telemetry, but it must not convert "
            "operational self-measurement into unsupported claims of biological or phenomenal consciousness."
        ),
    )


class AionTelemetryGroundedVoiceBridge:
    def __init__(self, *, repo_root: Optional[Path] = None):
        self.repo_root = Path(repo_root or ".").resolve()

    def _load_meta_awareness(self) -> Dict[str, Any]:
        if AionMetaAwarenessObserver is None:
            return {
                "meta_awareness": 0.0,
                "self_state_stable": False,
                "next_response_bias": "observer_unavailable",
                "latest": {},
            }
        return AionMetaAwarenessObserver(repo_root=self.repo_root, window=20).observe().to_dict()

    def _run_self_improvement(self) -> Dict[str, Any]:
        if run_self_improvement_trial_loop is None:
            return {
                "improved": False,
                "final_score": 0.0,
                "improvement_delta": 0.0,
                "evidence": {"uses_llm_shortcut": False},
            }

        output_path = self.repo_root / "data/analysis/aion_self_improvement_trial_loop_latest.json"
        result = run_self_improvement_trial_loop(output_path=output_path)
        return result.to_dict()

    def answer(self, question: str) -> TelemetryGroundedVoiceResponse:
        meta = self._load_meta_awareness()
        improvement = self._run_self_improvement()
        return build_telemetry_grounded_voice_response(
            question=question,
            meta_awareness_state=meta,
            self_improvement_result=improvement,
        )


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]).strip() or "Are you aware of your own awareness?"
    response = AionTelemetryGroundedVoiceBridge().answer(question)

    print("\n=== AION TELEMETRY-GROUNDED VOICE ===")
    print(response.answer)
    print("\n=== RESPONSE JSON ===")
    print(json.dumps(response.to_dict(), indent=2))
