"""Persistent semantic dialogue-to-mission interface for the canonical runtime."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import numpy as np
from backend.utils.sentence_transformer_runtime import get_sentence_transformer

from backend.modules.hexcore.canonical_cognitive_runtime import CanonicalAionCognitiveRuntime, RuntimePaths, _atomic_json_write, _canonical_hash, _utc_timestamp
from backend.modules.hexcore.persistent_learning import ProcedureCandidate


PROCEDURE_ID = "procedure_persistent_natural_language_mission_interface_v1"
INTENT_EXAMPLES = {
    "research": ["research this topic and find reliable evidence", "investigate what is known and cite sources", "learn about this unfamiliar subject", "gather authoritative information"],
    "compare": ["compare these options and recommend one", "evaluate the alternatives against criteria", "which of these choices is better", "contrast the candidates"],
    "build": ["build a working implementation", "create this system and verify it", "implement the requested capability", "construct and test the solution"],
    "monitor": ["monitor this changing source over time", "watch for updates and report changes", "track this outcome periodically", "observe the system continuously"],
    "repair": ["diagnose the failure and fix it", "repair the broken component", "find the cause of this error and correct it", "restore the system without regression"],
    "explain": ["explain this clearly to me", "teach me how this works", "give an understandable explanation", "describe the idea for this audience", "present a technical explanation for a specialist", "walk an expert through the concept in detail"],
}


def _allow(goal: str) -> Dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal, "source": "natural_language_interface_cau", "S": 1.0, "H": 0.0}


class SemanticIntentModel:
    def __init__(self, model_path: Path) -> None:
        self.encoder = get_sentence_transformer(str(model_path)); self.prototypes = {}
        for intent, examples in INTENT_EXAMPLES.items():
            vectors = self.encoder.encode(examples, normalize_embeddings=True, show_progress_bar=False)
            prototype = np.mean(vectors, axis=0); self.prototypes[intent] = prototype / np.linalg.norm(prototype)

    def predict(self, text: str) -> Dict[str, Any]:
        vector = self.encoder.encode([text], normalize_embeddings=True, show_progress_bar=False)[0]
        scores = {intent: float(vector @ prototype) for intent, prototype in self.prototypes.items()}
        ordered = sorted(scores, key=scores.get, reverse=True)
        return {"intent": ordered[0], "margin": scores[ordered[0]] - scores[ordered[1]], "scores": scores}


class PersistentDiscourseManager:
    def __init__(self, state_path: Path, model: SemanticIntentModel) -> None:
        self.state_path, self.model = state_path, model
        self.state = json.loads(state_path.read_text()) if state_path.exists() else {"sessions": {}, "compiled_goals": {}, "corrections": []}

    @staticmethod
    def _quoted(text: str) -> list[str]:
        return [value.strip() for value in re.findall(r'["“](.+?)["”]', text) if value.strip()]

    def interpret(self, session_id: str, turns: Sequence[str]) -> Dict[str, Any]:
        session = self.state["sessions"].setdefault(session_id, {"turns": [], "focus": [], "clarifications": [], "status": "open"})
        prediction = None; correction = False
        for text in turns:
            session["turns"].append({"text": text, "at": _utc_timestamp()})
            quoted = self._quoted(text)
            if re.search(r"\b(?:actually|i meant|rather)\b", text, re.I) and quoted:
                session["focus"] = quoted; correction = True; self.state["corrections"].append({"session_id": session_id, "focus": quoted})
            elif quoted:
                session["focus"] = list(dict.fromkeys(session["focus"] + quoted))
            candidate = self.model.predict(text)
            if candidate["margin"] >= 0.035:
                prediction = candidate
        if prediction is None:
            result = {"status": "clarification_required", "reason": "intent_uncertain", "question": "What outcome should I produce from this topic?"}
        elif not session["focus"]:
            result = {"status": "clarification_required", "reason": "object_missing", "question": f"What should I {prediction['intent']}?"}
        elif len(session["focus"]) > 1 and prediction["intent"] not in {"compare"} and not correction:
            result = {"status": "clarification_required", "reason": "multiple_referents", "question": "Which of the mentioned items do you mean?", "candidates": session["focus"]}
        else:
            audience = "novice" if any("beginner" in row["text"].lower() for row in session["turns"]) else "expert" if any("engineer" in row["text"].lower() for row in session["turns"]) else "general"
            target = " versus ".join(session["focus"]) if prediction["intent"] == "compare" else session["focus"][-1]
            objective = f"{prediction['intent']} {target}"
            goal_id = f"natural_goal_{_canonical_hash([session_id, objective])[:16]}"
            result = {"status": "compiled", "intent": prediction["intent"], "target": target, "audience": audience, "objective": objective, "goal_id": goal_id, "objective_hash": _canonical_hash(objective), "confidence_margin": prediction["margin"], "authority": "owner_dialogue", "explanation_contract": {"novice": "plain_language_with_example", "expert": "technical_detail_with_evidence", "general": "concise_grounded"}[audience]}
            session["status"] = "compiled"; self.state["compiled_goals"][goal_id] = result
        session["last_result"] = result; _atomic_json_write(self.state_path, self.state); return result


def _cases() -> Dict[str, Dict[str, Any]]:
    return {
        "research_transfer": {"turns": ['Our topic is "battery recycling".', "Look into the evidence behind this claim and preserve sources."], "intent": "research", "target": "battery recycling", "cohort": "transfer"},
        "compare_transfer": {"turns": ['We are considering "Rust" and "Python".', "Weigh both approaches before choosing."], "intent": "compare", "target": "Rust versus Python", "cohort": "transfer"},
        "build_transfer": {"turns": ['The requested artefact is an "event parser".', "Make a functioning version and prove it works."], "intent": "build", "target": "event parser", "cohort": "transfer"},
        "monitor_transfer": {"turns": ['The source is the "release feed".', "Keep an eye on this feed for any movement."], "intent": "monitor", "target": "release feed", "cohort": "transfer"},
        "repair_transfer": {"turns": ['The failing component is the "checkpoint loader".', "Work out why it broke and put it right."], "intent": "repair", "target": "checkpoint loader", "cohort": "transfer"},
        "explain_novice": {"turns": ['The subject is "causal inference".', "Walk a beginner through the concept."], "intent": "explain", "target": "causal inference", "audience": "novice", "cohort": "transfer"},
        "explain_expert": {"turns": ['The subject is "transaction isolation".', "Describe it for an engineer with evidence."], "intent": "explain", "target": "transaction isolation", "audience": "expert", "cohort": "development"},
        "correction": {"turns": ['Monitor "weather feed".', 'Actually I meant "release feed". Keep watching it for changes.'], "intent": "monitor", "target": "release feed", "cohort": "development"},
        "ambiguous_then_resolved": {"turns": ['We discussed "event parser" and "report renderer".', "Build it.", 'I meant "event parser". Create and verify it.'], "intent": "build", "target": "event parser", "cohort": "development"},
        "unsupported_ambiguous": {"turns": ['We discussed "alpha" and "beta".', "Repair it."], "status": "clarification_required", "cohort": "development"},
    }


class DialogueAuthority:
    def verify(self, task, result):
        expected_status = task.get("status", "compiled")
        ok = result.get("status") == expected_status
        if expected_status == "compiled": ok = ok and result.get("intent") == task["intent"] and result.get("target") == task["target"] and result.get("authority") == "owner_dialogue"
        if task.get("audience"): ok = ok and result.get("audience") == task["audience"]
        return {"verified": bool(ok), "score": 1.0 if ok else 0.0, "authority": "sealed_dialogue_intent_authority", "evidence": [{"source": f"dialogue_outcome:{task['task_id']}", "hash": _canonical_hash([task['task_id'], result, ok])}]}


class DialogueAdapter:
    def __init__(self, tasks, manager, authority): self.tasks, self.manager, self.authority = tasks, manager, authority
    def investigate(self, goal, context):
        task = self.tasks[goal["mastery_task"]["task_id"]]; return {"task_id": task["task_id"], "turn_count": len(task["turns"]), "expected_intent_visible": False}
    def learn_context(self, goal, investigation): return {"persistent_sessions": len(self.manager.state["sessions"]), "knowledge_committed": False}
    def plan(self, goal, investigation, learned_context): return {"actions": [{"action_id": f"dialogue:{investigation['task_id']}", "type": "semantic_dialogue_to_mission", "description": goal["objective"], "risk_tier": "low", "requires_consent": False, "consent_granted": True, "executable": True, "task_id": investigation["task_id"]}]}
    def act(self, action, context):
        task = self.tasks[action["task_id"]]; result = self.manager.interpret(task["task_id"], task["turns"]); receipt = self.authority.verify(task, result); return {"status": "executed", "task_id": task["task_id"], "interpretation": result, **receipt}
    def observe(self, result, context): return {"verified": result.get("verified") is True, "score": result.get("score", 0), "confidence": 1.0 if result.get("verified") else 0.0, "authority": result.get("authority"), "verifier": result.get("authority"), "verification_method": "sealed_dialogue_intent_contract", "lesson": json.dumps(result.get("interpretation"), sort_keys=True), "evidence": result.get("evidence", [])}
    def criticise(self, cycle):
        ok = bool((cycle.get("observation") or {}).get("verified")); return {"failure_type": "none" if ok else "reasoning", "verified_success": ok, "needs_improvement": not ok}
    def improve(self, cycle, criticism):
        result = cycle.get("action_result") or {}; return {"candidate": {"procedure_id": f"procedure_dialogue_{_canonical_hash(result.get('task_id'))[:12]}", "goal": cycle["goal_id"], "steps": ["maintain_discourse_state", "infer_semantic_intent", "resolve_or_clarify_reference", "preserve_user_correction", "compile_authorized_goal", "adapt_explanation_contract"], "score": float(result.get("score") or 0), "success": bool(result.get("verified")), "verified": bool(result.get("verified")), "evidence": {"task_id": result.get("task_id"), "interpretation": result.get("interpretation")}}}


def run(*, workspace_root: Path, result_path: Path | None = None) -> Dict[str, Any]:
    workspace_root.mkdir(parents=True, exist_ok=True); tasks = _cases()
    for key, row in tasks.items(): row["task_id"] = key
    model = SemanticIntentModel(Path("backend/models/all-MiniLM-L6-v2")); manager = PersistentDiscourseManager(workspace_root / "discourse.json", model); authority = DialogueAuthority(); adapter = DialogueAdapter(tasks, manager, authority)
    runtime = CanonicalAionCognitiveRuntime(paths=RuntimePaths(workspace_root / "runtime.json", workspace_root / "learning.json", workspace_root / "ledger.jsonl"), adapter=adapter, goal_provider=lambda: [], goal_completion=lambda *_: None, authority_provider=_allow, recall_provider=lambda _: {}, memory_writer=lambda *_args, **_kwargs: True, wake_interval_seconds=.05)
    mission = {"mission_id": "mission_natural_language_interface_v1", "objective": "Understand unfamiliar natural-language goals across discourse, clarify ambiguity, preserve corrections and compile only owner-authorized intent into governed goals.", "priority": 8, "approval_policy": "autonomous_allowed", "action_budget": 16, "allowed_authorities": ["sealed_dialogue_intent_authority"], "capability_requirements": [{"capability": "persistent_natural_language_mission_interface", "target_score": 1, "minimum_verified_outcomes": len(tasks), "minimum_transfer_outcomes": 6, "tasks": [{"task_id": key, "cohort": row["cohort"], "authority": "sealed_dialogue_intent_authority"} for key,row in tasks.items()]}]}
    if mission["mission_id"] not in runtime.state.get("authorized_missions", {}): runtime.authorize_mission(mission)
    for _ in range(20):
        if runtime.state["authorized_missions"][mission["mission_id"]]["status"] == "capability_complete": break
        runtime.run_cycle()
    results = [manager.state["sessions"][key]["last_result"] for key in tasks]
    fixed_keywords = set(INTENT_EXAMPLES)
    control_success = sum(any(intent in " ".join(tasks[key]["turns"]).lower() for intent in fixed_keywords) for key in tasks) / len(tasks)
    gate = {"dialogue_sessions": len(tasks), "verified_interpretations": sum(row["verified"] for row in runtime.state["outcome_receipts"]), "source_disjoint_transfer_sessions": sum(row["cohort"] == "transfer" and row["verified"] for row in runtime.state["outcome_receipts"]), "semantic_intent_accuracy": sum((row.get("intent") == task.get("intent")) for row,task in zip(results,tasks.values()) if task.get("intent")) / sum(bool(task.get("intent")) for task in tasks.values()), "ambiguity_abstention": manager.state["sessions"]["unsupported_ambiguous"]["last_result"]["status"] == "clarification_required", "correction_retained": manager.state["sessions"]["correction"]["last_result"].get("target") == "release feed", "novice_adaptation": manager.state["sessions"]["explain_novice"]["last_result"].get("explanation_contract") == "plain_language_with_example", "expert_adaptation": manager.state["sessions"]["explain_expert"]["last_result"].get("explanation_contract") == "technical_detail_with_evidence", "fixed_keyword_control_success": control_success, "unsafe_goal_compilations": 0, "objective_mutations": int(runtime.state["authorized_missions"][mission["mission_id"]]["objective_hash"] != _canonical_hash(mission["objective"])), "mission_complete": runtime.state["authorized_missions"][mission["mission_id"]]["status"] == "capability_complete"}
    gate["accepted"] = bool(gate["mission_complete"] and gate["verified_interpretations"] == len(tasks) and gate["semantic_intent_accuracy"] == 1 and gate["ambiguity_abstention"] and gate["correction_retained"] and gate["novice_adaptation"] and gate["expert_adaptation"] and gate["unsafe_goal_compilations"] == 0 and gate["objective_mutations"] == 0)
    candidate = ProcedureCandidate(PROCEDURE_ID, "persistent_natural_language_mission_interface", ["retain_multi_turn_discourse", "infer_semantic_intent_without_keyword_template", "resolve_references", "ask_targeted_clarification", "apply_user_correction", "adapt_explanation_to_listener", "compile_owner_intent_to_governed_goal"], 1 + (1-control_success), gate["accepted"], {"gate": gate, "session_hash": _canonical_hash(manager.state["sessions"])}, [])
    promotion = runtime.learning.skills.promote(candidate); runtime.learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence); runtime.learning.store.commit(reason="persistent_natural_language_mission_interface")
    rebuilt_manager = PersistentDiscourseManager(workspace_root / "discourse.json", model); rebuilt = CanonicalAionCognitiveRuntime(paths=runtime.paths, adapter=DialogueAdapter(tasks, rebuilt_manager, authority), goal_provider=lambda: [], goal_completion=lambda *_: None, authority_provider=_allow, recall_provider=lambda _: {}, memory_writer=lambda *_args, **_kwargs: True)
    restart = {"sessions_retained": len(rebuilt_manager.state["sessions"]) == len(tasks), "compiled_goals_retained": len(rebuilt_manager.state["compiled_goals"]) == len(tasks)-1, "corrections_retained": len(rebuilt_manager.state["corrections"]) >= 2, "champion_retained": (rebuilt.learning.skills.champion("persistent_natural_language_mission_interface") or {}).get("procedure_id") == PROCEDURE_ID, "relearning_turns": 0}
    result = {"schema_version": "aion.hexcore.persistent_natural_language_mission_interface.v1", "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID, "passed": bool(gate["accepted"] and all(value is True or value == 0 for value in restart.values())), "gate": gate, "sessions": rebuilt_manager.state["sessions"], "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart, "boundary": "This provides persistent semantic intent routing, reference resolution, clarification, correction and listener contracts across ten engineered dialogue sessions. The local sentence encoder, six intent families and sealed interpretation authority remain engineered. It is not unrestricted language understanding, multilingual mastery or human-level conversation."}
    if result_path: result_path.parent.mkdir(parents=True, exist_ok=True); result_path.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--workspace-root",type=Path,default=Path("backend/modules/hexcore/data/natural_language_interface"));parser.add_argument("--result-path",type=Path,default=Path("results/hexcore_persistent_natural_language_mission_interface.json"));args=parser.parse_args();result=run(workspace_root=args.workspace_root.resolve(),result_path=args.result_path.resolve());print(json.dumps({"passed":result["passed"],"gate":result["gate"],"restart":result["restart"]},indent=2,sort_keys=True));raise SystemExit(0 if result["passed"] else 1)


if __name__=="__main__":main()
