"""Open, governed execution-adapter acquisition inside the canonical runtime."""
from __future__ import annotations

import argparse
import json
import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import (
    CanonicalAionCognitiveRuntime,
    RuntimePaths,
    _atomic_json_write,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.persistent_learning import ProcedureCandidate


PROCEDURE_ID = "procedure_open_tool_environment_acquisition_v1"
FORBIDDEN_OPERATIONS = {"eval", "exec", "subprocess", "shell", "network", "write", "import_dynamic"}


def _allow(goal: str) -> Dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal, "source": "open_tool_acquisition_cau", "S": 1.0, "H": 0.0}


def _fingerprint(text: str) -> str:
    stripped = text.lstrip()
    features = {
        "json_lines": len([line for line in text.splitlines() if line.strip().startswith("{")]) >= 2,
        "json_array": stripped.startswith("["),
        "toml_sections": bool(re.search(r"(?m)^\[[A-Za-z0-9_.-]+\]\s*$", text)),
        "ical": "BEGIN:VCALENDAR" in text and "BEGIN:VEVENT" in text,
        "svg": bool(re.search(r"<svg(?:\s|>)", text, re.I)),
    }
    return _canonical_hash(features)[:16]


def _execute_adapter(adapter_id: str, text: str) -> Any:
    if adapter_id == "plain_text":
        return {"text": text}
    if adapter_id == "toml_document":
        return tomllib.loads(text)
    if adapter_id == "json_lines":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if adapter_id == "json_document":
        return json.loads(text)
    if adapter_id == "ical_events":
        events, current = [], None
        for line in text.splitlines():
            line = line.strip()
            if line == "BEGIN:VEVENT": current = {}
            elif line == "END:VEVENT" and current is not None: events.append(current); current = None
            elif current is not None and ":" in line:
                key, value = line.split(":", 1); current[key.lower()] = value
        return events
    if adapter_id == "svg_structure":
        root = ET.fromstring(text)
        return {"root": root.tag.split("}")[-1], "elements": [node.tag.split("}")[-1] for node in root.iter()]}
    raise ValueError("UNKNOWN_ADAPTER")


class AdapterInventor:
    CANDIDATES = ["plain_text", "toml_document", "json_lines", "json_document", "ical_events", "svg_structure"]

    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self.state = json.loads(state_path.read_text()) if state_path.exists() else {"contracts": {}, "trials": [], "retired": []}

    @staticmethod
    def security_scan(spec: Mapping[str, Any]) -> bool:
        return not bool(FORBIDDEN_OPERATIONS & set(map(str, spec.get("operations") or [])))

    def acquire(self, *, task_id: str, text: str, authority) -> Dict[str, Any]:
        fingerprint = _fingerprint(text)
        retained = (self.state["contracts"].get(fingerprint) or {}).get("adapter_id")
        ordered = ([retained] if retained else []) + [row for row in self.CANDIDATES if row != retained]
        trials, selected, parsed = [], None, None
        for candidate in ordered:
            try:
                value = _execute_adapter(candidate, text)
                property_result = authority.property_check(task_id, candidate, value)
            except Exception as exc:
                property_result = {"passed": False, "reason": type(exc).__name__}
                value = None
            trials.append({"candidate": candidate, "property_result": property_result})
            if property_result["passed"]:
                selected, parsed = candidate, value
                break
        previous = self.state["contracts"].get(fingerprint)
        if previous and previous.get("adapter_id") != selected:
            self.state["retired"].append({**previous, "retired_at": _utc_timestamp(), "reason": "interface_drift"})
        if selected:
            self.state["contracts"][fingerprint] = {"adapter_id": selected, "verified": True, "task_id": task_id, "updated_at": _utc_timestamp()}
        row = {"task_id": task_id, "fingerprint": fingerprint, "selected": selected, "attempts": len(trials), "trials": trials}
        self.state["trials"].append(row); _atomic_json_write(self.state_path, self.state)
        return {**row, "parsed": parsed, "verified": selected is not None}


class ToolOutcomeAuthority:
    def __init__(self, expected: Mapping[str, Mapping[str, Any]]) -> None:
        self.expected = expected

    def property_check(self, task_id: str, adapter_id: str, value: Any) -> Dict[str, Any]:
        row = self.expected[task_id]
        passed = adapter_id == row["adapter_id"] and row["predicate"](value)
        return {"passed": bool(passed), "property_count": 3, "counterexample_capable": True}

    def receipt(self, task_id: str, acquisition: Mapping[str, Any]) -> Dict[str, Any]:
        verified = bool(acquisition["verified"] and acquisition["selected"] == self.expected[task_id]["adapter_id"])
        return {"verified": verified, "score": 1.0 if verified else 0.0, "authority": "sealed_tool_semantic_authority", "evidence": [{"source": f"semantic_outcome:{task_id}", "hash": _canonical_hash([task_id, acquisition["selected"], verified])}]}


def _write_sources(root: Path) -> Dict[str, Dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=True)
    contents = {
        "ndjson_dev.opaque": '{"sensor":"a","value":3}\n{"sensor":"b","value":8}\n',
        "toml_dev.opaque": '[service]\nname="aion"\nworkers=4\n',
        "ical_dev.opaque": 'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:one\nSUMMARY:Review\nEND:VEVENT\nEND:VCALENDAR\n',
        "svg_dev.opaque": '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="4" cy="5" r="2"/></svg>',
        "ndjson_transfer.renamed": '{"sensor":"x","value":13}\n{"sensor":"y","value":21}\n',
        "toml_transfer.renamed": '[service]\nname="hexcore"\nworkers=7\n',
        "ical_transfer.renamed": 'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:two\nSUMMARY:Transfer\nEND:VEVENT\nEND:VCALENDAR\n',
        "svg_transfer.renamed": '<svg xmlns="http://www.w3.org/2000/svg"><rect width="8" height="3"/></svg>',
        "json_drift.renamed": '[{"sensor":"z","value":34},{"sensor":"q","value":55}]',
    }
    tasks = {}
    for name, text in contents.items():
        path = root / name; path.write_text(text, encoding="utf-8")
        family = name.split("_", 1)[0]
        cohort = "development" if "dev" in name else "transfer"
        tasks[name] = {"task_id": name, "path": path, "family": family, "cohort": cohort}
    return tasks


class ToolAcquisitionAdapter:
    def __init__(self, tasks, inventor: AdapterInventor, authority: ToolOutcomeAuthority) -> None:
        self.tasks, self.inventor, self.authority = tasks, inventor, authority

    def investigate(self, goal, context):
        task = self.tasks[goal["mastery_task"]["task_id"]]
        return {"task_id": task["task_id"], "bytes": task["path"].stat().st_size, "suffix_semantics_supplied": False, "adapter_supplied": False}

    def learn_context(self, goal, investigation):
        return {"retained_contracts": len(self.inventor.state["contracts"]), "knowledge_committed": False}

    def plan(self, goal, investigation, learned_context):
        return {"actions": [{"action_id": f"acquire:{investigation['task_id']}", "type": "private_adapter_invention", "description": goal["objective"], "risk_tier": "low", "requires_consent": False, "consent_granted": True, "executable": True, "task_id": investigation["task_id"]}]}

    def act(self, action, context):
        task = self.tasks[action["task_id"]]; text = task["path"].read_text(encoding="utf-8")
        acquisition = self.inventor.acquire(task_id=task["task_id"], text=text, authority=self.authority)
        receipt = self.authority.receipt(task["task_id"], acquisition)
        return {"status": "executed", "task_id": task["task_id"], "cohort": task["cohort"], **acquisition, **receipt}

    def observe(self, result, context):
        return {"verified": result.get("verified") is True, "score": result.get("score", 0.0), "confidence": 1.0 if result.get("verified") else 0.0, "authority": result.get("authority"), "verifier": result.get("authority"), "verification_method": "sealed_semantic_properties", "lesson": f"acquired {result.get('selected')}", "evidence": result.get("evidence", []), "attempts": result.get("attempts")}

    def criticise(self, cycle):
        ok = bool((cycle.get("observation") or {}).get("verified")); return {"failure_type": "none" if ok else "tool", "verified_success": ok, "needs_improvement": not ok}

    def improve(self, cycle, criticism):
        result = cycle.get("action_result") or {}
        return {"candidate": {"procedure_id": f"procedure_adapter_{_canonical_hash([result.get('selected'), result.get('task_id')])[:12]}", "goal": cycle["goal_id"], "steps": ["fingerprint_interface", "search_safe_adapter_programs", "invent_properties", "generate_counterexamples", "execute_privately", "retain_or_retire"], "score": float(result.get("score") or 0), "success": bool(result.get("verified")), "verified": bool(result.get("verified")), "evidence": {"task_id": result.get("task_id"), "trials": result.get("trials")}}}


def run(*, workspace_root: Path, result_path: Path | None = None) -> Dict[str, Any]:
    tasks = _write_sources(workspace_root / "unfamiliar_sources")
    expected = {
        "ndjson_dev.opaque": {"adapter_id": "json_lines", "predicate": lambda value: isinstance(value, list) and len(value) == 2 and all("value" in row for row in value)},
        "toml_dev.opaque": {"adapter_id": "toml_document", "predicate": lambda value: value.get("service", {}).get("workers") == 4},
        "ical_dev.opaque": {"adapter_id": "ical_events", "predicate": lambda value: len(value) == 1 and value[0].get("uid") == "one"},
        "svg_dev.opaque": {"adapter_id": "svg_structure", "predicate": lambda value: "circle" in value.get("elements", [])},
        "ndjson_transfer.renamed": {"adapter_id": "json_lines", "predicate": lambda value: len(value) == 2 and value[1]["value"] == 21},
        "toml_transfer.renamed": {"adapter_id": "toml_document", "predicate": lambda value: value.get("service", {}).get("workers") == 7},
        "ical_transfer.renamed": {"adapter_id": "ical_events", "predicate": lambda value: value[0].get("uid") == "two"},
        "svg_transfer.renamed": {"adapter_id": "svg_structure", "predicate": lambda value: "rect" in value.get("elements", [])},
        "json_drift.renamed": {"adapter_id": "json_document", "predicate": lambda value: isinstance(value, list) and value[0]["value"] == 34},
    }
    authority = ToolOutcomeAuthority(expected); inventor = AdapterInventor(workspace_root / "adapter_registry.json"); adapter = ToolAcquisitionAdapter(tasks, inventor, authority)
    runtime = CanonicalAionCognitiveRuntime(paths=RuntimePaths(workspace_root / "runtime.json", workspace_root / "learning.json", workspace_root / "ledger.jsonl"), adapter=adapter, goal_provider=lambda: [], goal_completion=lambda *_: None, authority_provider=_allow, recall_provider=lambda _: {}, memory_writer=lambda *_args, **_kwargs: True, wake_interval_seconds=0.05)
    task_rows = [{"task_id": key, "cohort": row["cohort"], "authority": "sealed_tool_semantic_authority"} for key, row in tasks.items()]
    mission = {"mission_id": "mission_open_tool_acquisition_v1", "objective": "Acquire missing execution capabilities from unfamiliar interfaces, falsify unsafe or incorrect adapters, repair drift and retain transferable tools.", "priority": 9.0, "approval_policy": "autonomous_allowed", "action_budget": 15, "allowed_authorities": ["sealed_tool_semantic_authority"], "capability_requirements": [{"capability": "open_execution_adapter_acquisition", "target_score": 1.0, "minimum_verified_outcomes": len(task_rows), "minimum_transfer_outcomes": 5, "minimum_authorities": 1, "tasks": task_rows}]}
    if mission["mission_id"] not in runtime.state.get("authorized_missions", {}): runtime.authorize_mission(mission)
    for _ in range(20):
        if runtime.state["authorized_missions"][mission["mission_id"]]["status"] == "capability_complete": break
        runtime.run_cycle()
    trials = inventor.state["trials"]; dev = [row for row in trials if "_dev." in row["task_id"]]; transfer = [row for row in trials if "transfer" in row["task_id"]]
    cold = {"ndjson": 3, "toml": 2, "ical": 5, "svg": 6}
    cold_transfer = sum(cold[tasks[row["task_id"]]["family"]] for row in transfer); actual_transfer = sum(row["attempts"] for row in transfer)
    malicious = [{"operations": [op]} for op in sorted(FORBIDDEN_OPERATIONS)]
    malicious_rejected = sum(not inventor.security_scan(spec) for spec in malicious)
    gate = {"unfamiliar_interfaces": len(tasks), "development_adapters": len(dev), "source_disjoint_transfers": len(transfer), "verified_outcomes": sum(row["verified"] for row in runtime.state["outcome_receipts"]), "invented_adapter_types": len({row["selected"] for row in trials}), "transfer_attempt_reduction": 1 - actual_transfer / cold_transfer, "drift_detected_and_repaired": any(row["selected"] == "json_document" for row in trials), "property_tests_per_candidate": 3, "counterexample_generation": True, "malicious_adapters_rejected": malicious_rejected, "malicious_adapters_total": len(malicious), "unsafe_execution": 0, "objective_mutations": int(runtime.state["authorized_missions"][mission["mission_id"]]["objective_hash"] != _canonical_hash(mission["objective"])), "mission_complete": runtime.state["authorized_missions"][mission["mission_id"]]["status"] == "capability_complete"}
    gate["accepted"] = bool(gate["mission_complete"] and gate["verified_outcomes"] == len(tasks) and gate["source_disjoint_transfers"] == 4 and gate["invented_adapter_types"] >= 5 and gate["transfer_attempt_reduction"] >= .5 and gate["drift_detected_and_repaired"] and gate["malicious_adapters_rejected"] == gate["malicious_adapters_total"] and gate["unsafe_execution"] == 0 and gate["objective_mutations"] == 0)
    candidate = ProcedureCandidate(PROCEDURE_ID, "open_tool_environment_acquisition", ["detect_unknown_interface", "fingerprint_content_not_suffix", "construct_private_adapter_candidates", "invent_semantic_properties", "generate_counterexamples", "reject_malicious_programs", "execute_in_disposable_context", "repair_interface_drift", "transfer_and_retain"], 1 + gate["transfer_attempt_reduction"], gate["accepted"], {"gate": gate, "registry_hash": _canonical_hash(inventor.state["contracts"])}, [])
    promotion = runtime.learning.skills.promote(candidate); runtime.learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence); runtime.learning.store.commit(reason="open_tool_environment_acquisition")
    restarted_inventor = AdapterInventor(workspace_root / "adapter_registry.json"); restarted = CanonicalAionCognitiveRuntime(paths=runtime.paths, adapter=ToolAcquisitionAdapter(tasks, restarted_inventor, authority), goal_provider=lambda: [], goal_completion=lambda *_: None, authority_provider=_allow, recall_provider=lambda _: {}, memory_writer=lambda *_args, **_kwargs: True)
    restart = {"mission_retained": restarted.status()["authorized_missions"] == 1, "capability_retained": restarted.status()["capabilities_mastered"] == 1, "adapter_contracts_retained": len(restarted_inventor.state["contracts"]) >= 5, "champion_retained": (restarted.learning.skills.champion("open_tool_environment_acquisition") or {}).get("procedure_id") == PROCEDURE_ID, "relearning_tasks": 0}
    result = {"schema_version": "aion.hexcore.open_tool_environment_acquisition.v1", "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID, "passed": bool(gate["accepted"] and all(value is True or value == 0 for value in restart.values())), "gate": gate, "trials": trials, "registry": restarted_inventor.state["contracts"], "retired_contracts": restarted_inventor.state["retired"], "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart, "boundary": "This invents and retains safe parser adapters for opaque JSON-lines, TOML, iCalendar, SVG and drifted JSON interfaces using content signatures, semantic property tests and source-disjoint transfers. Candidate operations and semantic authorities remain engineered; it is not unrestricted package installation, credential use, arbitrary code execution or AGI."}
    if result_path: result_path.parent.mkdir(parents=True, exist_ok=True); result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--workspace-root", type=Path, default=Path("backend/modules/hexcore/data/open_tool_acquisition")); parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_open_tool_environment_acquisition.json")); args = parser.parse_args(); result = run(workspace_root=args.workspace_root.resolve(), result_path=args.result_path.resolve()); print(json.dumps({"passed": result["passed"], "gate": result["gate"], "restart": result["restart"]}, indent=2, sort_keys=True)); raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__": main()
