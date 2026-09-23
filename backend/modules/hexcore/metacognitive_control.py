"""Cheap-first, AION-native metacognitive review before action commitment."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _json_safe, _utc_timestamp


RISK = {"low": 0.1, "medium": 0.45, "high": 0.8, "critical": 1.0}


class MetacognitiveController:
    """Independent contract critic; it never calls an LLM or executes an action."""

    @staticmethod
    def _route_uncertainty(investigation: Mapping[str, Any]) -> float:
        routes=[]
        for key in ("native_specialist_route",):
            row=investigation.get(key) or {}
            if row.get("status")=="proposed": routes.append(1.0-float(row.get("confidence") or 0.0))
            elif row.get("status")=="abstained": routes.append(1.0)
        composition=investigation.get("native_composition_proposal") or {}
        for row in composition.get("steps") or []:
            routes.append(1.0-float(row.get("confidence") or 0.0) if row.get("status")=="proposed" else 1.0)
        return max(routes,default=0.0)

    @staticmethod
    def action_signature(action: Mapping[str, Any]) -> str:
        return _canonical_hash([str(action.get("type") or "unknown"),str(action.get("risk_tier") or "low"),bool(action.get("irreversible") is True),bool(action.get("reversible") is True or action.get("rollback_plan"))])[:16]

    @staticmethod
    def _history_risk(action: Mapping[str, Any], history: Sequence[Mapping[str, Any]]) -> tuple[float,int]:
        signature=MetacognitiveController.action_signature(action)
        rows=[row for row in history if row.get("action_signature")==signature]
        failures=sum(
            row.get("verified") is False or row.get("outcome_grade") == "bad"
            for row in rows
        )
        return (failures/max(1,len(rows))),failures

    @staticmethod
    def _relevant_lessons(
        action: Mapping[str, Any], history: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        signature = MetacognitiveController.action_signature(action)
        lessons: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in reversed(history):
            if row.get("action_signature") != signature:
                continue
            reflection = row.get("outcome_reflection") or {}
            lesson = reflection.get("lesson") if isinstance(reflection, Mapping) else None
            if not isinstance(lesson, Mapping):
                continue
            lesson_id = str(lesson.get("lesson_id") or "")
            if lesson_id and lesson_id not in seen:
                lessons.append(dict(lesson))
                seen.add(lesson_id)
            if len(lessons) >= 3:
                break
        return lessons

    @staticmethod
    def _best_alternative(action: Mapping[str, Any], plan: Mapping[str, Any]) -> Mapping[str, Any] | None:
        alternatives=[dict(row) for row in plan.get("alternatives") or [] if isinstance(row,Mapping)]
        if not alternatives:return None
        def utility(row):
            return float(row.get("predicted_success",0.0))-float(row.get("worst_case_loss",0.0))*.7+float(row.get("reversible") is True)*.1
        current=utility(action);best=max(alternatives,key=utility)
        return best if utility(best)>current+.05 else None

    @staticmethod
    def _invent_criticism(
        action: Mapping[str, Any], assumptions: Sequence[str]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Invent bounded criticism when a planner supplies no opposition.

        These are questions and proposal-only information actions, never claims
        that the imagined failure is true and never executable authority.
        """
        counterfactuals: list[dict[str, Any]] = []
        for assumption in assumptions[:3]:
            counterfactuals.append({
                "source": "aion_self_generated_criticism",
                "assumption": assumption,
                "opposing_scenario": f"Suppose this assumption is false: {assumption}",
                "diagnostic_question": f"What observable evidence would falsify: {assumption}?",
                "invalidates_action": False,
                "status": "unverified_counterfactual",
            })
        if not counterfactuals:
            counterfactuals.append({
                "source": "aion_self_generated_criticism",
                "opposing_scenario": "The proposed action executes correctly but fails to achieve its intended outcome.",
                "diagnostic_question": "Which observable outcome would distinguish decision failure from execution failure?",
                "invalidates_action": False,
                "status": "unverified_counterfactual",
            })
        information_actions = [{
            "action_id": "diagnose_" + _canonical_hash([
                action.get("type"), row["diagnostic_question"]
            ])[:12],
            "type": "information_action",
            "question": row["diagnostic_question"],
            "risk_tier": "low",
            "reversible": True,
            "proposal_only": True,
            "requires_independent_outcome": True,
        } for row in counterfactuals]
        return counterfactuals, information_actions

    def review(self, *, goal: Mapping[str,Any], investigation: Mapping[str,Any], learned_context: Mapping[str,Any], plan: Mapping[str,Any], action: Mapping[str,Any], history: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
        risk_tier=str(action.get("risk_tier") or goal.get("risk_tier") or "low").lower();risk=RISK.get(risk_tier,.5);route_uncertainty=self._route_uncertainty(investigation);explicit_uncertainty=float(action.get("uncertainty") or plan.get("uncertainty") or 0.0);unresolved=len(investigation.get("unresolved_questions") or []);uncertainty=max(route_uncertainty,explicit_uncertainty,min(.8,unresolved*.2));history_risk,prior_failures=self._history_risk(action,history)
        assumptions=list(dict.fromkeys(str(x) for x in [*(plan.get("assumptions") or []),*(action.get("assumptions") or [])] if str(x).strip()));counterfactuals=[dict(x) for x in plan.get("counterfactuals") or [] if isinstance(x,Mapping)];contradictions=[dict(x) if isinstance(x,Mapping) else {"claim":str(x)} for x in plan.get("contradictions") or []];reversible=bool(action.get("reversible") is True or action.get("rollback_plan"));irreversible=bool(action.get("irreversible") is True or (risk>=.8 and not reversible));learned_lessons=self._relevant_lessons(action,history);deep=bool(risk>=.8 or uncertainty>=.45 or irreversible or contradictions or prior_failures or counterfactuals or learned_lessons)
        self_generated_criticism = False
        information_actions: list[dict[str, Any]] = []
        if deep and not counterfactuals:
            counterfactuals, information_actions = self._invent_criticism(action, assumptions)
            self_generated_criticism = True
        checks=["executable_contract","consent_contract","known_contradiction_scan"]
        decision="execute";reason="cheap_checks_passed";revised_action=None
        if action.get("executable") is not True: decision,reason="abstain","action_not_executable"
        elif action.get("requires_consent") and not action.get("consent_granted"):decision,reason="escalate","required_consent_missing"
        elif contradictions:decision,reason="investigate","unresolved_contradiction"
        elif deep:
            checks += ["assumption_audit","counterfactual_opponent_reply","historical_failure_recall","reversibility_and_rollback","alternative_dominance"]
            for lesson in learned_lessons:
                for required_check in lesson.get("required_checks") or []:
                    if str(required_check) not in checks:
                        checks.append(str(required_check))
            alternative=self._best_alternative(action,plan);invalidated=any(row.get("invalidates_action") is True for row in counterfactuals)
            if (invalidated or history_risk>=.5) and alternative is not None:
                revised_action={**dict(action),**dict(alternative),"metacognitive_revision_of":action.get("action_id")};decision,reason="revise","counterfactual_or_history_favours_alternative"
            elif invalidated:decision,reason="investigate","counterfactual_invalidates_action"
            elif irreversible and not action.get("verification_plan"):decision,reason="investigate","irreversible_action_lacks_verification"
            elif uncertainty>=.7 and not action.get("verification_plan"):decision,reason="investigate","uncertainty_exceeds_evidence"
            else:reason="deep_review_passed"
        score=min(1.0,.35*risk+.35*uncertainty+.2*history_risk+.1*float(irreversible))
        material={"goal":goal.get("goal_id"),"action":action.get("action_id"),"decision":decision,"checks":checks,"reason":reason}
        return {"schema_version":"aion.hexcore.metacognitive_review.v1","review_id":"meta_"+_canonical_hash(material)[:16],"reviewed_at":_utc_timestamp(),"decision":decision,"reason":reason,"depth":"deep" if deep else "cheap","deliberation_units":len(checks),"risk_tier":risk_tier,"risk_score":risk,"uncertainty":uncertainty,"historical_failure_rate":history_risk,"prior_failures":prior_failures,"learned_lessons":_json_safe(learned_lessons),"action_signature":self.action_signature(action),"assumption_ledger":assumptions,"counterfactuals":counterfactuals,"self_generated_criticism":self_generated_criticism,"information_actions":_json_safe(information_actions),"contradictions":contradictions,"reversible":reversible,"irreversible":irreversible,"metacognitive_pressure":score,"checks":checks,"original_action_hash":_canonical_hash(action),"revised_action":_json_safe(revised_action),"proposal_only":True}

    def reflect_outcome(
        self,
        *,
        goal: Mapping[str, Any],
        plan: Mapping[str, Any],
        action: Mapping[str, Any],
        review: Mapping[str, Any],
        action_result: Mapping[str, Any],
        observation: Mapping[str, Any],
        criticism: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Turn a surprising outcome into a narrow, evidence-linked future check."""
        verified = observation.get("verified") is True
        score = max(0.0, min(1.0, float(observation.get("score") or 0.0)))
        predicted = max(
            0.0,
            min(
                1.0,
                float(
                    action.get("predicted_success")
                    if action.get("predicted_success") is not None
                    else plan.get("predicted_success", 1.0 if verified else 0.5)
                ),
            ),
        )
        if verified and score >= 0.85:
            grade = "good"
        elif verified and score >= 0.5:
            grade = "average"
        else:
            grade = "bad"
        prediction_error = abs(predicted - score)
        reflect = bool(
            grade != "good"
            or prediction_error >= 0.25
            or float(review.get("risk_score") or 0.0) >= 0.8
        )

        failure_type = str(criticism.get("failure_type") or "none")
        assumptions = list(review.get("assumption_ledger") or [])
        if failure_type in {"unknown", "ambiguous", "multiple_plausible_causes"}:
            attribution = "ambiguous"
        elif action_result.get("status") == "denied" or failure_type == "authority":
            attribution = "authority"
        elif failure_type in {"execution", "interrupted_action", "tool"} or action_result.get("error"):
            attribution = "execution"
        elif failure_type in {"world_change", "environment", "distribution_shift"}:
            attribution = "environment"
        elif failure_type in {"verification", "evidence", "perception"}:
            attribution = "evidence"
        elif grade in {"bad", "average"} and assumptions:
            attribution = "assumption"
        elif grade in {"bad", "average"}:
            attribution = "decision_model"
        else:
            attribution = "none"

        lesson = None
        if reflect and attribution != "ambiguous":
            required = {
                "authority": ["consent_contract", "authority_scope_check"],
                "execution": ["execution_adapter_check", "precondition_check"],
                "environment": ["environment_freshness_check", "change_detection"],
                "evidence": ["independent_evidence_check", "observation_quality_check"],
                "assumption": ["assumption_audit", "counterexample_search"],
                "decision_model": ["counterfactual_opponent_reply", "alternative_dominance"],
                "none": ["retain_provisional_success_pattern"],
            }[attribution]
            adjustment = {
                "authority": "escalate_or_reduce_scope_before_retry",
                "execution": "repair_or_replace_execution_path_before_retry",
                "environment": "reobserve_then_replan_under_current_state",
                "evidence": "investigate_before_accepting_or_repeating",
                "assumption": "falsify_key_assumption_before_repeating",
                "decision_model": "compare_a_reversible_alternative_before_repeating",
                "none": "retain_as_provisional_until_repeated",
            }[attribution]
            evidence_material = {
                "goal_id": goal.get("goal_id"),
                "action_signature": review.get("action_signature")
                or self.action_signature(action),
                "observation": observation,
                "criticism": criticism,
            }
            lesson_material = {
                "signature": evidence_material["action_signature"],
                "attribution": attribution,
                "required_checks": required,
                "adjustment": adjustment,
            }
            lesson = {
                "lesson_id": "lesson_" + _canonical_hash(lesson_material)[:16],
                "condition_signature": evidence_material["action_signature"],
                "attribution": attribution,
                "required_checks": required,
                "recommended_adjustment": adjustment,
                "failed_assumption": assumptions[0] if attribution == "assumption" and assumptions else None,
                "confidence": round(max(0.5, min(1.0, 0.55 + prediction_error * 0.35 + (0.1 if not verified else 0.0))), 6),
                "status": "provisional",
                "support_count": 1,
                "evidence_hash": _canonical_hash(evidence_material),
                "scope": "matching_decision_signature_only",
            }

        competing_explanations = []
        diagnostic_required = attribution == "ambiguous"
        if diagnostic_required:
            competing_explanations = [
                {"cause": cause, "status": "plausible_unresolved"}
                for cause in (
                    "assumption", "decision_model", "execution",
                    "evidence", "environment", "authority",
                )
            ]

        material = {
            "review_id": review.get("review_id"),
            "grade": grade,
            "score": score,
            "attribution": attribution,
            "lesson": lesson,
        }
        return {
            "schema_version": "aion.hexcore.post_action_reflection.v1",
            "reflection_id": "reflection_" + _canonical_hash(material)[:16],
            "reflected_at": _utc_timestamp(),
            "performed": reflect,
            "outcome_grade": grade,
            "verified": verified,
            "predicted_success": predicted,
            "observed_score": score,
            "prediction_error": prediction_error,
            "attribution": attribution,
            "lesson": _json_safe(lesson),
            "diagnostic_required": diagnostic_required,
            "competing_explanations": competing_explanations,
            "cheap_noop": not reflect,
            "llm_calls": 0,
        }
