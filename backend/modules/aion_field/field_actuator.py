# backend/modules/aion_field/field_actuator.py
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


class FieldActuator:
    """
    Chooses and applies field control updates.

    Policy:
      1. keep current control
      2. apply proposed control
      3. apply best search candidate

    Selection rule:
      - if actuation is not ready: hold current
      - else if best search candidate clearly beats current: apply best search candidate
      - else if proposed control clearly beats current: apply proposed control
      - else: hold current

    Non-breaking:
      - fail-open
      - always returns a structured result
      - only applies keys that are safe for field control
    """

    SAFE_CONTROL_KEYS = {
        "resonance_gain",
        "symbolic_temperature",
        "stabilization_bias",
        "awareness_coupling",
        "mode",
        "goal_bias",
        "control_priority",
        "reasoning_depth",
    }

    def __init__(self) -> None:
        self.last_decision: Optional[Dict[str, Any]] = None
        self.last_applied_control: Optional[Dict[str, Any]] = None

    def choose_control(
        self,
        *,
        current_control: Optional[Dict[str, Any]],
        field_operator: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        current_control = deepcopy(current_control or {})
        field_operator = field_operator or {}

        stability_score = self._safe_float(field_operator.get("stability_score"), 0.0)
        reasoning_state = field_operator.get("reasoning_state") or {}
        actuation_ready = bool(reasoning_state.get("actuation_ready", False))

        proposed_adjustments = field_operator.get("proposed_adjustments") or {}
        proposed_control = proposed_adjustments.get("proposed_control") or {}

        search_result = field_operator.get("search_result") or {}
        best_candidate = search_result.get("best_candidate") or {}
        best_score = self._safe_float(search_result.get("best_score"), -1.0)
        current_score = self._safe_float(search_result.get("current_score"), stability_score)

        chosen_mode = "hold_current"
        chosen_control = deepcopy(current_control)
        reason = "No better candidate available; holding current control."

        # estimate proposal quality if not explicitly supplied by operator
        proposed_score = -1.0
        if proposed_control:
            proposed_score = self._estimate_control_score(
                candidate=self._merge_control(current_control, proposed_control),
                field_operator=field_operator,
                fallback_score=stability_score,
            )

        score_margin = 0.003

        if not actuation_ready:
            chosen_mode = "hold_current"
            chosen_control = deepcopy(current_control)
            reason = "Actuation not ready; holding current control."
        else:
            best_is_better = bool(best_candidate) and (best_score > current_score + score_margin)
            proposed_is_better = bool(proposed_control) and (proposed_score > current_score + score_margin)

            if best_is_better and best_score > proposed_score:
                chosen_mode = "apply_best_search_candidate"
                chosen_control = self._merge_control(current_control, best_candidate)
                reason = (
                    f"Best search candidate improves score from {current_score:.3f} "
                    f"to {best_score:.3f}."
                )
            elif proposed_is_better:
                chosen_mode = "apply_proposed_control"
                chosen_control = self._merge_control(current_control, proposed_control)
                reason = (
                    f"Proposed control improves score from {current_score:.3f} "
                    f"to {proposed_score:.3f}."
                )
            else:
                chosen_mode = "hold_current"
                chosen_control = deepcopy(current_control)
                reason = (
                    f"No candidate clearly improves current score "
                    f"({current_score:.3f}); holding current control."
                )

        decision = {
            "mode": chosen_mode,
            "reason": reason,
            "actuation_ready": actuation_ready,
            "current_control": current_control,
            "chosen_control": chosen_control,
            "stability_score": stability_score,
            "current_score": current_score,
            "best_score": best_score,
            "proposed_score": proposed_score,
        }
        self.last_decision = decision
        return decision

    def apply_control(
        self,
        *,
        runtime_bundle: Optional[Dict[str, Any]],
        control: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        runtime_bundle = runtime_bundle or {}
        control = self._sanitize_control(control or {})

        if not control:
            result = {
                "ok": False,
                "applied": False,
                "reason": "No valid control keys to apply.",
                "control": {},
            }
            self.last_applied_control = {}
            return result

        engine = runtime_bundle.get("engine") if isinstance(runtime_bundle, dict) else None

        if engine is None:
            result = {
                "ok": False,
                "applied": False,
                "reason": "No live Symatics engine available.",
                "control": control,
            }
            self.last_applied_control = control
            return result

        applied = False
        applied_via = None

        # Preferred method names on engine
        for method_name in (
            "apply_control",
            "set_control",
            "update_control",
            "set_field_control",
            "inject_control",
        ):
            method = getattr(engine, method_name, None)
            if callable(method):
                try:
                    method(deepcopy(control))
                    applied = True
                    applied_via = method_name
                    break
                except TypeError:
                    try:
                        method(**deepcopy(control))
                        applied = True
                        applied_via = method_name
                        break
                    except Exception:
                        pass
                except Exception:
                    pass

        # Fallback: direct attribute patch
        if not applied:
            try:
                for key, value in control.items():
                    setattr(engine, key, value)
                applied = True
                applied_via = "setattr_patch"
            except Exception:
                applied = False
                applied_via = None

        result = {
            "ok": applied,
            "applied": applied,
            "applied_via": applied_via,
            "control": control,
        }
        self.last_applied_control = control
        return result

    def decide_and_apply(
        self,
        *,
        runtime_bundle: Optional[Dict[str, Any]],
        current_control: Optional[Dict[str, Any]],
        field_operator: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        decision = self.choose_control(
            current_control=current_control,
            field_operator=field_operator,
        )
        apply_result = self.apply_control(
            runtime_bundle=runtime_bundle,
            control=decision.get("chosen_control"),
        )
        return {
            "decision": decision,
            "apply_result": apply_result,
        }

    def _merge_control(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        merged = deepcopy(base)
        for key, value in (update or {}).items():
            if key in self.SAFE_CONTROL_KEYS:
                merged[key] = value
        return self._sanitize_control(merged)

    def _sanitize_control(self, control: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, value in control.items():
            if key not in self.SAFE_CONTROL_KEYS:
                continue
            out[key] = value
        return out

    def _estimate_control_score(
        self,
        *,
        candidate: Dict[str, Any],
        field_operator: Dict[str, Any],
        fallback_score: float,
    ) -> float:
        """
        Conservative local score estimate used only when the operator did not
        provide an explicit proposal score.

        It intentionally mirrors the search preference logic:
        - lower symbolic_temperature is often better for entropy suppression
        - moderate resonance_gain is preferred over over-driving
        - high stabilization_bias is preferred
        - awareness_coupling gets a small positive effect when present
        """
        candidate = self._sanitize_control(candidate or {})
        if not candidate:
            return fallback_score

        score = fallback_score

        rg = self._safe_float(candidate.get("resonance_gain"), 0.5)
        st = self._safe_float(candidate.get("symbolic_temperature"), 0.1)
        sb = self._safe_float(candidate.get("stabilization_bias"), 1.0)
        ac = self._safe_float(candidate.get("awareness_coupling"), 0.0)

        pattern_signature = field_operator.get("pattern_signature") or {}
        regime = str(pattern_signature.get("observed_regime", "")).lower()
        constructive = regime == "constructive"

        if constructive:
            if 0.42 <= rg <= 0.58:
                score += 0.04
            elif rg > 0.70:
                score -= 0.06
            elif rg < 0.35:
                score -= 0.03
        else:
            if rg <= 0.48:
                score += 0.03
            elif rg > 0.65:
                score -= 0.06

        if st <= 0.08:
            score += 0.05
        elif st > 0.20:
            score -= 0.10

        if sb >= 0.95:
            score += 0.04
        elif sb < 0.70:
            score -= 0.06

        if ac > 0.0:
            score += min(0.03, 0.06 * ac)

        return max(0.0, min(1.0, score))

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)