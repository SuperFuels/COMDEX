# ──────────────────────────────────────────────────────────────
#  AION Field Operator
#  Rich field reasoning / proposal / search layer for Symatics
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import copy
import math


@dataclass
class FieldScore:
    stability_score: float
    coherence: float
    entropy: float
    delta_phi: float
    resonance: float
    phase_lock: float
    constructive_index: float


class FieldOperator:
    """
    Reads a Symatics packet and produces:
      - pattern_signature
      - reasoning_state
      - query_state
      - proposed_adjustments
      - search_result
      - question_result

    Designed to be conservative but useful:
      - if field is already strong, suggests gentle refinements
      - if field is unstable, suggests stabilising moves
      - always returns search candidates so actuator has options
    """

    def __init__(self):
        self.last_result: Optional[Dict[str, Any]] = None

    # ──────────────────────────────────────────────────────────
    # PUBLIC ENTRYPOINT
    # ──────────────────────────────────────────────────────────
    def operate(
        self,
        *,
        packet: Dict[str, Any],
        current_control: Optional[Dict[str, Any]] = None,
        question: str = "",
    ) -> Dict[str, Any]:
        raw = packet.get("raw", {}) or {}

        query_state = self._build_query_state(packet, raw)
        pattern_signature = self._build_pattern_signature(packet, raw)
        score = self._score_field(query_state, pattern_signature)
        reasoning_state = self._build_reasoning_state(score, pattern_signature)
        proposed_adjustments = self._build_proposed_adjustments(
            current_control=current_control or {},
            score=score,
            pattern_signature=pattern_signature,
            query_state=query_state,
        )
        search_result = self._search_control_space(
            current_control=current_control or {},
            score=score,
            query_state=query_state,
            pattern_signature=pattern_signature,
        )
        question_result = self._answer_question(
            question=question or "",
            score=score,
            pattern_signature=pattern_signature,
            query_state=query_state,
            proposed_adjustments=proposed_adjustments,
            search_result=search_result,
            packet=packet,
        )

        result = {
            "stability_score": score.stability_score,
            "actuation_ready": reasoning_state.get("actuation_ready", False),
            "pattern_signature": pattern_signature,
            "reasoning_state": reasoning_state,
            "query_state": query_state,
            "proposed_adjustments": proposed_adjustments,
            "search_result": search_result,
            "question_result": question_result,
        }

        self.last_result = result
        return result

    # ──────────────────────────────────────────────────────────
    # BUILDERS
    # ──────────────────────────────────────────────────────────
    def _build_query_state(self, packet: Dict[str, Any], raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "coherence": self._f(packet.get("coherence"), 0.0),
            "entropy": self._f(packet.get("entropy", raw.get("entropy")), 0.0),
            "delta_phi": self._f(packet.get("delta_phi", raw.get("delta_phi")), 0.0),
            "resonance": self._f(raw.get("resonance", packet.get("symatics", {}).get("resonance")), 0.0),
            "amplitude": self._f(raw.get("amplitude", packet.get("amplitude")), 0.0),
            "frequency": self._f(raw.get("frequency", packet.get("frequency")), 0.0),
            "phase": self._f(raw.get("phase", packet.get("phase")), 0.0),
        }

    def _build_pattern_signature(self, packet: Dict[str, Any], raw: Dict[str, Any]) -> Dict[str, Any]:
        dominant_symbol = (
            packet.get("predicted_symbol")
            or packet.get("symatics", {}).get("dominant_symbol")
            or raw.get("predicted_symbol")
            or "unknown"
        )

        observed_regime = (
            packet.get("observed_regime")
            or raw.get("observed_regime")
            or "unknown"
        )

        coherence = self._f(packet.get("coherence"), 0.0)
        resonance = self._f(raw.get("resonance", packet.get("symatics", {}).get("resonance")), 0.0)
        delta_phi = abs(self._f(packet.get("delta_phi"), 1.0))

        phase_lock = self._clamp(1.0 - delta_phi, 0.0, 1.0)

        constructive_index = 0.0
        if str(observed_regime).lower() == "constructive":
            constructive_index += 0.5
        if str(dominant_symbol).upper() == "S1":
            constructive_index += 0.2
        if coherence >= 0.9:
            constructive_index += 0.2
        if resonance >= 0.9:
            constructive_index += 0.1

        return {
            "dominant_symbol": dominant_symbol,
            "observed_regime": observed_regime,
            "constructive_index": self._clamp(constructive_index, 0.0, 1.0),
            "phase_lock": phase_lock,
        }

    def _score_field(
        self,
        query_state: Dict[str, Any],
        pattern_signature: Dict[str, Any],
    ) -> FieldScore:
        coherence = self._clamp(self._f(query_state.get("coherence"), 0.0), 0.0, 1.0)
        entropy = self._clamp(self._f(query_state.get("entropy"), 1.0), 0.0, 1.0)
        delta_phi = self._clamp(abs(self._f(query_state.get("delta_phi"), 1.0)), 0.0, 1.0)
        resonance = self._clamp(self._f(query_state.get("resonance"), 0.0), 0.0, 1.0)
        phase_lock = self._clamp(self._f(pattern_signature.get("phase_lock"), 0.0), 0.0, 1.0)
        constructive_index = self._clamp(self._f(pattern_signature.get("constructive_index"), 0.0), 0.0, 1.0)

        stability_score = (
            0.35 * coherence
            + 0.20 * (1.0 - entropy)
            + 0.15 * (1.0 - delta_phi)
            + 0.15 * resonance
            + 0.10 * phase_lock
            + 0.05 * constructive_index
        )

        return FieldScore(
            stability_score=self._clamp(stability_score, 0.0, 1.0),
            coherence=coherence,
            entropy=entropy,
            delta_phi=delta_phi,
            resonance=resonance,
            phase_lock=phase_lock,
            constructive_index=constructive_index,
        )

    def _build_reasoning_state(
        self,
        score: FieldScore,
        pattern_signature: Dict[str, Any],
    ) -> Dict[str, Any]:
        actuation_ready = bool(
            score.stability_score >= 0.70
            or score.coherence >= 0.85
            or pattern_signature.get("observed_regime") in {"constructive", "stable"}
        )

        return {
            "question_ready": True,
            "search_ready": True,
            "actuation_ready": actuation_ready,
            "stability_score": score.stability_score,
            "pattern_signature": pattern_signature,
            "candidate_action_space": {
                "phase_shift": True,
                "frequency_shift": True,
                "amplitude_shift": True,
                "resonance_gain": True,
                "stabilization_bias": True,
            },
        }

    # ──────────────────────────────────────────────────────────
    # PROPOSAL LAYER
    # ──────────────────────────────────────────────────────────
    def _build_proposed_adjustments(
        self,
        *,
        current_control: Dict[str, Any],
        score: FieldScore,
        pattern_signature: Dict[str, Any],
        query_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        proposed = copy.deepcopy(current_control or {})
        adjustments: List[str] = []

        rg = self._f(proposed.get("resonance_gain"), 0.5)
        st = self._f(proposed.get("symbolic_temperature"), 0.1)
        sb = self._f(proposed.get("stabilization_bias"), 0.8)
        ac = self._f(proposed.get("awareness_coupling"), 0.0)

        regime = str(pattern_signature.get("observed_regime", "unknown")).lower()
        dominant_symbol = str(pattern_signature.get("dominant_symbol", "unknown")).upper()

        if regime == "constructive" and score.stability_score >= 0.85:
            new_rg = self._clamp(rg + 0.03, 0.0, 1.0)
            if new_rg != rg:
                proposed["resonance_gain"] = new_rg
                adjustments.append("slightly increase resonance_gain to intensify stable constructive lock")

            if score.entropy <= 0.10:
                new_ac = self._clamp(max(ac, 0.5 * packet_awareness_hint(query_state, score)), 0.0, 1.0)
                if new_ac != ac:
                    proposed["awareness_coupling"] = new_ac
                    adjustments.append("increase awareness_coupling to align operator response with stable field state")

        if score.entropy > 0.20:
            new_st = self._clamp(st - 0.05, 0.0, 1.0)
            if new_st != st:
                proposed["symbolic_temperature"] = new_st
                adjustments.append("reduce symbolic_temperature to suppress entropy growth")

        if score.delta_phi > 0.10:
            new_sb = self._clamp(sb + 0.05, 0.0, 1.0)
            if new_sb != sb:
                proposed["stabilization_bias"] = new_sb
                adjustments.append("increase stabilization_bias to reduce phase drift")

        if dominant_symbol != "S1" and score.coherence < 0.85:
            new_rg = self._clamp(rg - 0.03, 0.0, 1.0)
            proposed["resonance_gain"] = new_rg
            adjustments.append("slightly reduce resonance_gain to avoid over-driving an unstable symbol regime")

        if not adjustments:
            adjustments.append("hold current control; field is already near a stable operating point")

        reason = (
            f"Field is in {regime} regime with dominant symbol {dominant_symbol}, "
            f"stability {score.stability_score:.3f}, coherence {score.coherence:.3f}, "
            f"entropy {score.entropy:.3f}, drift {score.delta_phi:.3f}. "
            f"Prefer local control search and stability-preserving adjustments."
        )

        return {
            "current_control": current_control,
            "proposed_control": proposed,
            "adjustments": adjustments,
            "stability_score": score.stability_score,
            "reason": reason,
        }

    # ──────────────────────────────────────────────────────────
    # SEARCH LAYER
    # ──────────────────────────────────────────────────────────
    def _search_control_space(
        self,
        *,
        current_control: Dict[str, Any],
        score: FieldScore,
        query_state: Dict[str, Any],
        pattern_signature: Dict[str, Any],
    ) -> Dict[str, Any]:
        base_control = copy.deepcopy(current_control or {})
        base_rg = self._f(base_control.get("resonance_gain"), 0.5)
        base_st = self._f(base_control.get("symbolic_temperature"), 0.1)
        base_sb = self._f(base_control.get("stabilization_bias"), 1.0)

        rg_offsets = (-0.05, 0.0, 0.05)
        st_offsets = (-0.05, 0.0, 0.05)
        sb_offsets = (-0.05, 0.0, 0.05)

        scored: List[Dict[str, Any]] = []
        seen = set()

        for d_rg in rg_offsets:
            for d_st in st_offsets:
                for d_sb in sb_offsets:
                    candidate = copy.deepcopy(base_control)
                    candidate["resonance_gain"] = self._clamp(base_rg + d_rg, 0.0, 1.0)
                    candidate["symbolic_temperature"] = self._clamp(base_st + d_st, 0.0, 1.0)
                    candidate["stabilization_bias"] = self._clamp(base_sb + d_sb, 0.0, 1.0)

                    key = (
                        round(self._f(candidate.get("resonance_gain")), 6),
                        round(self._f(candidate.get("symbolic_temperature")), 6),
                        round(self._f(candidate.get("stabilization_bias")), 6),
                        round(self._f(candidate.get("awareness_coupling")), 6),
                        str(candidate.get("mode")),
                        str(candidate.get("goal_bias")),
                        str(candidate.get("control_priority")),
                        round(self._f(candidate.get("reasoning_depth"), 1.0), 6),
                    )
                    if key in seen:
                        continue
                    seen.add(key)

                    cand_score = self._estimate_candidate_score(
                        candidate=candidate,
                        field_score=score,
                        pattern_signature=pattern_signature,
                    )
                    scored.append({"candidate": candidate, "score": cand_score})

        current_score = self._estimate_candidate_score(
            candidate=base_control,
            field_score=score,
            pattern_signature=pattern_signature,
        )

        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[:5]
        best = top[0] if top else {"candidate": base_control, "score": current_score}

        return {
            "best_candidate": best.get("candidate"),
            "best_score": best.get("score", current_score),
            "current_score": current_score,
            "top_candidates": top,
            "search_basis": {
                "current_control": base_control,
                "coherence": score.coherence,
                "entropy": score.entropy,
                "delta_phi": score.delta_phi,
                "resonance": score.resonance,
            },
        }

    def _estimate_candidate_score(
        self,
        *,
        candidate: Dict[str, Any],
        field_score: FieldScore,
        pattern_signature: Dict[str, Any],
    ) -> float:
        rg = self._f(candidate.get("resonance_gain"), 0.5)
        st = self._f(candidate.get("symbolic_temperature"), 0.1)
        sb = self._f(candidate.get("stabilization_bias"), 1.0)
        ac = self._f(candidate.get("awareness_coupling"), 0.0)

        base = field_score.stability_score
        regime = str(pattern_signature.get("observed_regime", "")).lower()
        constructive = regime == "constructive"

        delta = 0.0

        if constructive:
            # Prefer staying close to the current constructive lock window
            if 0.49 <= rg <= 0.54:
                delta += 0.004
            elif 0.45 <= rg < 0.49:
                delta += 0.001
            elif 0.54 < rg <= 0.58:
                delta += 0.001
            elif rg < 0.42:
                delta -= 0.010
            elif rg > 0.62:
                delta -= 0.020

            # Slight preference for mild cooling, but do not let temperature dominate
            if 0.04 <= st <= 0.08:
                delta += 0.003
            elif st < 0.02:
                delta -= 0.004
            elif st > 0.12:
                delta -= 0.010

            # Stabilization bias should help slightly, not saturate
            if 0.95 <= sb <= 1.0:
                delta += 0.003
            elif sb < 0.85:
                delta -= 0.010

            # Awareness coupling is helpful in stable constructive states
            if 0.15 <= ac <= 0.60:
                delta += 0.004
            elif ac > 0.75:
                delta -= 0.003

        else:
            if 0.40 <= rg <= 0.50:
                delta += 0.004
            elif rg > 0.65:
                delta -= 0.020

            if st <= 0.06:
                delta += 0.004
            elif st > 0.20:
                delta -= 0.020

            if sb >= 0.95:
                delta += 0.004
            elif sb < 0.80:
                delta -= 0.012

            if ac > 0.0:
                delta += min(0.003, 0.01 * ac)

        # Soft ceiling so near-perfect states do not collapse into 1.0 ties
        score = min(base + delta, 0.999)

        return self._clamp(score, 0.0, 1.0)
    # ──────────────────────────────────────────────────────────
    # QUESTION LAYER
    # ──────────────────────────────────────────────────────────
    def _answer_question(
        self,
        *,
        question: str,
        score: FieldScore,
        pattern_signature: Dict[str, Any],
        query_state: Dict[str, Any],
        proposed_adjustments: Dict[str, Any],
        search_result: Dict[str, Any],
        packet: Dict[str, Any],
    ) -> Dict[str, Any]:
        q = (question or "").strip()

        if not q:
            answer = (
                "Field query interface is ready. Use coherence, entropy, drift, and resonance "
                "to ask stability, optimisation, or transition questions."
            )
        elif "stabil" in q.lower():
            answer = (
                "Use coherence, entropy, drift, and resonance together. "
                "Search locally around the current control point and prefer candidates "
                "that increase stability without raising entropy."
            )
        elif "entropy" in q.lower():
            answer = (
                "To minimise entropy, reduce symbolic_temperature first, then maintain "
                "high stabilization_bias and moderate resonance_gain."
            )
        elif "resonance" in q.lower() or "lock" in q.lower():
            answer = (
                "To strengthen resonance lock, keep phase drift low, preserve constructive regime, "
                "and test small resonance_gain changes rather than large jumps."
            )
        else:
            answer = (
                "Question understood as a field reasoning task. "
                "Use the proposed adjustment and search candidates to test nearby control states."
            )

        return {
            "question": q,
            "answer": answer,
            "evaluation": {
                "stability_score": score.stability_score,
                "pattern_signature": pattern_signature,
                "reasoning_state": {
                    "question_ready": True,
                    "search_ready": True,
                    "actuation_ready": score.stability_score >= 0.70,
                    "stability_score": score.stability_score,
                    "pattern_signature": pattern_signature,
                    "candidate_action_space": {
                        "phase_shift": True,
                        "frequency_shift": True,
                        "amplitude_shift": True,
                        "resonance_gain": True,
                        "stabilization_bias": True,
                    },
                },
                "query_state": query_state,
                "field_state": {
                    "self_awareness": packet.get("self_awareness"),
                    "global_coherence": packet.get("global_coherence"),
                    "locked": packet.get("locked"),
                    "tick_count": packet.get("tick_count"),
                },
            },
            "proposed_adjustments": proposed_adjustments,
            "search_result": search_result,
        }

    # ──────────────────────────────────────────────────────────
    # UTILS
    # ──────────────────────────────────────────────────────────
    def _f(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except Exception:
            return float(default)

    def _clamp(self, value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))


def packet_awareness_hint(query_state: Dict[str, Any], score: FieldScore) -> float:
    coherence = float(query_state.get("coherence", 0.0) or 0.0)
    resonance = float(query_state.get("resonance", 0.0) or 0.0)
    phase_lock = float(score.phase_lock)
    return max(0.0, min(1.0, (coherence + resonance + phase_lock) / 3.0))