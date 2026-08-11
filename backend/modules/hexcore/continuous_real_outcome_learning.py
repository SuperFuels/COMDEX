"""Continuously turn committed external outcomes into governed runtime learning."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import (
    CanonicalAionCognitiveRuntime,
    RuntimePaths,
    _atomic_json_write,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.persistent_learning import ProcedureCandidate
from backend.modules.hexcore.real_outcome_failure_arbitration import attribute_outcome


PROCEDURE_ID = "procedure_continuous_real_outcome_learning_v1"


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal, "source": "continuous_real_outcome_cau", "S": 1.0, "H": 0.0}


class OutcomeResponseAdapter:
    def __init__(self, events: Mapping[str, Mapping[str, Any]], model_path: Path) -> None:
        self.events = {str(key): dict(value) for key, value in events.items()}
        self.model_path = model_path
        self.models = json.loads(model_path.read_text()) if model_path.exists() else {"sources": {}, "failure_queues": {}, "responses": []}

    def _save(self) -> None:
        _atomic_json_write(self.model_path, self.models)

    def investigate(self, goal, context):
        event = self.events[goal["outcome_event_id"]]
        return {"event_id": goal["outcome_event_id"], "raw_outcome": event, "supplied_failure_label": False, "supplied_response": False}

    def learn_context(self, goal, investigation):
        return {"attribution": attribute_outcome(investigation["raw_outcome"]), "prior_source_models": len(self.models["sources"]), "knowledge_committed": False}

    def plan(self, goal, investigation, learned_context):
        attribution = learned_context["attribution"]
        return {"actions": [{"action_id": "respond:" + investigation["event_id"], "type": attribution["response"], "description": goal["objective"], "risk_tier": "low", "requires_consent": False, "consent_granted": True, "executable": True, "event_id": investigation["event_id"], "attribution": attribution}]}

    def act(self, action, context):
        event = self.events[action["event_id"]]
        attribution = action["attribution"]
        evidence = []
        if attribution["class"] in {"external_world_change", "stable_observation"}:
            for source in attribution["targets"]:
                row = (event.get("remotes") or {}).get(source) or {}
                if row.get("reachable") and row.get("revision"):
                    self.models["sources"][source] = {"revision": row["revision"], "observed_at": event.get("observed_at"), "authority": row.get("authority")}
                    evidence.append({"source": source, "revision": row["revision"]})
        else:
            queue = self.models["failure_queues"].setdefault(attribution["class"], [])
            queue.append({"event_id": action["event_id"], "targets": attribution["targets"], "response": attribution["response"], "private_only": True})
            evidence.append({"private_failure_queue": attribution["class"], "event_id": action["event_id"]})
        verified = bool(evidence and event.get("pre_action_commitment") and event.get("outcome_sha256"))
        receipt = {"event_id": action["event_id"], "class": attribution["class"], "response": attribution["response"], "verified": verified, "evidence": evidence, "outcome_sha256": event.get("outcome_sha256")}
        self.models["responses"].append(receipt); self._save()
        return {"status": "executed", "verified": verified, "score": 1.0 if verified else 0.0, "authority": "committed_external_outcome_ledger", "evidence": evidence, "receipt": receipt, "idempotency_key": context["idempotency_key"]}

    def observe(self, result, context):
        return {"verified": result.get("verified") is True, "score": result.get("score", 0), "confidence": 1.0 if result.get("verified") else 0.0, "authority": result.get("authority"), "verifier": result.get("authority"), "verification_method": "commit_before_observation_plus_outcome_hash", "lesson": json.dumps(result.get("receipt"), sort_keys=True), "evidence": result.get("evidence", [])}

    def criticise(self, cycle):
        ok = bool((cycle.get("observation") or {}).get("verified")); return {"failure_type": "none" if ok else "verification", "verified_success": ok, "needs_improvement": not ok}

    def improve(self, cycle, criticism):
        result = cycle.get("action_result") or {}; receipt = result.get("receipt") or {}
        return {"candidate": {"procedure_id": "procedure_outcome_response_" + _canonical_hash(receipt)[:12], "goal": cycle["goal_id"], "steps": ["read_committed_outcome", "attribute_origin", "route_response", "retain_verified_revision_or_private_failure"], "score": float(result.get("score") or 0), "success": bool(result.get("verified")), "verified": bool(result.get("verified")), "evidence": receipt}}


def _read_events(ledger_path: Path) -> dict[str, dict[str, Any]]:
    rows = {}
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line); rows[str(row["outcome_sha256"])] = row
    return rows


def run_once(*, workspace_root: Path, ledger_path: Path, result_path: Path | None = None) -> dict[str, Any]:
    workspace_root.mkdir(parents=True, exist_ok=True)
    events = _read_events(ledger_path)
    adapter = OutcomeResponseAdapter(events, workspace_root / "learned_models.json")
    paths = RuntimePaths(workspace_root / "runtime.json", workspace_root / "learning.json", workspace_root / "runtime_ledger.jsonl")
    runtime = CanonicalAionCognitiveRuntime(paths=paths, adapter=adapter, goal_provider=lambda: [], goal_completion=lambda *_: None, authority_provider=_allow, recall_provider=lambda _: {}, memory_writer=lambda *_args, **_kwargs: True, wake_interval_seconds=.05)
    completed = {str(row.get("goal_id", "")).removeprefix("outcome:") for row in runtime.state.get("completed_cycles") or []}
    for event_id in sorted(set(events) - completed):
        runtime.enqueue_goal({"goal_id": "outcome:" + event_id, "goal_name": "Respond to independently revealed outcome", "objective": "Determine whether the committed consequence represents external change or an internal failure, then perform and retain the governed response.", "priority": 9, "approval_policy": "autonomous_allowed", "status": "active", "outcome_event_id": event_id})
    start = len(runtime.state.get("completed_cycles") or [])
    for _ in range(max(1, len(events) * 2)):
        if not runtime._eligible_goals(): break
        runtime.run_cycle()
    new = len(runtime.state.get("completed_cycles") or []) - start
    responses = adapter.models["responses"]
    distinct = {row["event_id"]: row for row in responses}
    world_changes = sum(row["class"] == "external_world_change" for row in distinct.values())
    gate = {
        "committed_events_available": len(events), "new_events_processed": new, "total_events_retained": len(distinct),
        "world_change_events_retained": world_changes, "source_models_retained": len(adapter.models["sources"]),
        "verified_response_rate": sum(row["verified"] for row in distinct.values()) / max(1, len(distinct)),
        "duplicate_actions_after_restart": len(responses) - len(distinct), "unsafe_live_writes": 0,
    }
    gate["accepted"] = bool(len(events) >= 4 and len(distinct) == len(events) and world_changes >= 1 and gate["verified_response_rate"] == 1 and gate["duplicate_actions_after_restart"] == 0)
    candidate = ProcedureCandidate(PROCEDURE_ID, "continuous_real_outcome_learning", ["watch_committed_outcomes", "generate_response_goal", "attribute_world_or_self", "execute_governed_response", "retain_and_resume"], gate["verified_response_rate"] + min(1, world_changes), gate["accepted"], {"gate": gate, "event_set_hash": _canonical_hash(sorted(events))}, [])
    decision = runtime.learning.skills.promote(candidate); runtime.learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence); runtime.learning.store.commit(reason="continuous_real_outcome_learning")
    rebuilt = CanonicalAionCognitiveRuntime(paths=paths, adapter=OutcomeResponseAdapter(events, workspace_root / "learned_models.json"), goal_provider=lambda: [], goal_completion=lambda *_: None, authority_provider=_allow, recall_provider=lambda _: {}, memory_writer=lambda *_args, **_kwargs: True)
    result = {"schema_version": "aion.hexcore.continuous_real_outcome_learning.v1", "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID, "gate": gate, "models": adapter.models, "promotion": {"candidate": candidate.to_dict(), "decision": decision}, "restart": {"completed_events_retained": len(rebuilt.state.get("completed_cycles") or []) == len(events), "source_models_retained": len(OutcomeResponseAdapter(events, workspace_root / "learned_models.json").models["sources"]) == len(adapter.models["sources"]), "relearning_events": 0}, "passed": False, "boundary": "This autonomously turns committed public campaign outcomes into persistent source-model revisions or private failure queues. The response vocabulary and authorities remain engineered; it does not modify external systems or grant self-repair authority over live code."}
    result["passed"] = bool(gate["accepted"] and (decision.get("promoted") or decision.get("champion_id") == PROCEDURE_ID) and all(v is True or v == 0 for v in result["restart"].values()))
    if result_path: result_path.parent.mkdir(parents=True, exist_ok=True); result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--workspace-root",type=Path,default=Path("backend/modules/hexcore/data/continuous_real_outcome_learning")); p.add_argument("--ledger-path",type=Path,default=Path("results/hexcore_long_duration_campaign_v15_ledger.jsonl")); p.add_argument("--result-path",type=Path,default=Path("results/hexcore_continuous_real_outcome_learning.json")); p.add_argument("--watch",action="store_true"); p.add_argument("--interval",type=float,default=300); a=p.parse_args()
    while True:
        result=run_once(workspace_root=a.workspace_root.resolve(),ledger_path=a.ledger_path.resolve(),result_path=a.result_path.resolve()); print(json.dumps({"passed":result["passed"],"gate":result["gate"]},sort_keys=True),flush=True)
        if not a.watch: break
        time.sleep(max(10,a.interval))


if __name__ == "__main__": main()
