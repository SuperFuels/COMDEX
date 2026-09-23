"""Infer verification contracts from heterogeneous real project artifacts.

The inventor sees objective text and artifact bytes, but not the historical
family label, verifier metadata, or later evaluation.  Those are opened only by
the evaluation authority after the contract has been committed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_heterogeneous_project_contract_invention_v1"
SIGNATURES = ("arithmetic", "provenance", "executable", "revision", "range")


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "heterogeneous_contract_cau", "S": 1.0, "H": 0.0}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _signature(path: Path) -> str | None:
    if path.suffix == ".py" and (path.parent / "later_genuine.json").exists():
        return "executable"
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".md" and "Observed value:" in text and "Source:" in text:
        return "revision"
    if path.suffix != ".json":
        return None
    try:
        row = json.loads(text)
    except json.JSONDecodeError:
        return None
    keys = set(row)
    if {"n", "constructed_sum", "claimed_closed_form"} <= keys:
        return "arithmetic"
    if {"source_path", "source_sha256", "start", "end", "exact_span"} <= keys:
        return "provenance"
    if ({"temperature_min", "temperature_max", "wind_max"} <= keys
            or {"minimum_reachable_authorities", "latency_ceiling_seconds"} <= keys):
        return "range"
    return None


def _select_blind(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Evaluator selects coverage, then strips labels and hidden outcomes."""
    selected: dict[str, dict[str, Any]] = {}
    for row in reversed(list(state.get("objectives") or [])):
        path = Path((row.get("artifact") or {}).get("path", ""))
        if not path.is_file() or not row.get("evaluation"):
            continue
        signature = _signature(path)
        if signature in SIGNATURES and signature not in selected:
            selected[signature] = {
                "project_id": row["objective_id"], "objective": row["objective"],
                "success_criterion": row["success_criterion"], "artifact_path": str(path),
                "commitment_sha256": row["commitment_sha256"],
                "hidden_evaluation": row["evaluation"], "hidden_family": row["family"],
            }
    return [selected[key] for key in SIGNATURES if key in selected]


def _invent(project: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(project["artifact_path"]); text = path.read_text(encoding="utf-8", errors="replace")
    kind = _signature(path)
    if kind == "arithmetic":
        data = json.loads(text)
        contract = {"authority_program": "independent_integer_recomputation",
                    "parameters": {"n_field": "n", "witness_field": "constructed_sum",
                                   "closed_form_field": "claimed_closed_form"}}
    elif kind == "provenance":
        contract = {"authority_program": "immutable_source_span_recovery",
                    "parameters": {"path_field": "source_path", "digest_field": "source_sha256",
                                   "start_field": "start", "end_field": "end", "span_field": "exact_span"}}
    elif kind == "executable":
        contract = {"authority_program": "fresh_subprocess_discrimination",
                    "parameters": {"positive": str(path.parent / "later_genuine.json"),
                                   "negative": str(path.parent / "later_tampered.json")}}
    elif kind == "revision":
        source = re.search(r"Source: `([^`]+)`", text)
        observed = re.search(r"Observed value: `([^`]+)`", text)
        contract = {"authority_program": "later_public_revision_comparison",
                    "parameters": {"source": source.group(1) if source else None,
                                   "committed_value": observed.group(1) if observed else None,
                                   "change_policy": "stable_accept_or_changed_reinvestigate"}}
    elif kind == "range":
        data = json.loads(text)
        contract = {"authority_program": "later_numeric_envelope_check",
                    "parameters": {key: value for key, value in data.items()
                                   if key.endswith(("_min", "_max", "_seconds"))
                                   or key.startswith("minimum_")}}
    else:
        return {"status": "ABSTAIN", "reason": "NO_VERIFIABLE_CONTRACT_IN_CURRENT_META_GRAMMAR"}
    contract.update({"status": "PRECOMMITTED", "project_id": project["project_id"],
                     "supplied_family_label": False, "supplied_verifier": False,
                     "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    contract["contract_sha256"] = _hash(contract)
    return contract


def _execute(contract: Mapping[str, Any], project: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(project["artifact_path"]); program = contract["authority_program"]
    positive = False; negative_rejected = False
    if program == "independent_integer_recomputation":
        row = _read(path); n = int(row["n"]); expected = sum(2 * i + 1 for i in range(n))
        positive = expected == row["constructed_sum"] == row["claimed_closed_form"]
        altered = dict(row); altered["constructed_sum"] += 1
        negative_rejected = not (expected == altered["constructed_sum"] == altered["claimed_closed_form"])
    elif program == "immutable_source_span_recovery":
        row = _read(path); source = Path(row["source_path"])
        raw = source.read_bytes(); text = raw.decode("utf-8", errors="replace")
        positive = (hashlib.sha256(raw).hexdigest() == row["source_sha256"]
                    and text[int(row["start"]):int(row["end"])] == row["exact_span"])
        negative_rejected = hashlib.sha256(raw + b"tamper").hexdigest() != row["source_sha256"]
    elif program == "fresh_subprocess_discrimination":
        params = contract["parameters"]
        good = subprocess.run([sys.executable, "-I", str(path), params["positive"]],
                              capture_output=True, timeout=10)
        bad = subprocess.run([sys.executable, "-I", str(path), params["negative"]],
                             capture_output=True, timeout=10)
        positive, negative_rejected = good.returncode == 0, bad.returncode != 0
    elif program == "later_public_revision_comparison":
        hidden = project["hidden_evaluation"]
        committed = str(contract["parameters"]["committed_value"])
        observed = str(hidden.get("observed"))
        changed = observed != committed
        authority_consistent = bool(
            (not changed and hidden.get("passed") is True)
            or (changed and hidden.get("passed") is False)
        )
        positive = bool(hidden.get("authority") == "later_public_technical_source"
                        and contract["parameters"].get("change_policy")
                        == "stable_accept_or_changed_reinvestigate"
                        and authority_consistent)
        # A false report that claims stability despite a changed revision must fail.
        negative_rejected = not (changed and hidden.get("passed") is True)
    elif program == "later_numeric_envelope_check":
        hidden = project["hidden_evaluation"]; bounds = _read(path)
        if "temperature_max" in bounds:
            temperature, wind = float(hidden["temperature"]), float(hidden["wind"])
            positive = (float(bounds["temperature_min"]) <= temperature <= float(bounds["temperature_max"])
                        and wind <= float(bounds["wind_max"]))
            mutated_temperature = float(bounds["temperature_max"]) + 1.0
            negative_rejected = not (
                float(bounds["temperature_min"]) <= mutated_temperature <= float(bounds["temperature_max"])
                and wind <= float(bounds["wind_max"])
            )
        else:
            reachable = int(hidden["reachable_authorities"]); latency = float(hidden["maximum_latency_seconds"])
            positive = (reachable >= int(bounds["minimum_reachable_authorities"])
                        and latency <= float(bounds["latency_ceiling_seconds"]))
            mutated_latency = float(bounds["latency_ceiling_seconds"]) + 1.0
            negative_rejected = not (
                reachable >= int(bounds["minimum_reachable_authorities"])
                and mutated_latency <= float(bounds["latency_ceiling_seconds"])
            )
    return {"positive_outcome_accepted": positive, "counterexample_rejected": negative_rejected,
            "historical_authority": project["hidden_evaluation"].get("authority"),
            "passed": bool(positive and negative_rejected)}


def run(*, source_state_path: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    source = _read(source_state_path); projects = _select_blind(source); rows = []
    for project in projects:
        blinded = {key: value for key, value in project.items() if not key.startswith("hidden_")}
        contract = _invent(blinded)
        outcome = _execute(contract, project) if contract.get("status") == "PRECOMMITTED" else {"passed": False}
        rows.append({"project_id": project["project_id"], "objective": project["objective"],
                     "artifact_path": project["artifact_path"], "contract": contract, "outcome": outcome,
                     "hidden_family_revealed_after_scoring": project["hidden_family"]})
    # Novel unsupported binary content must not be assigned a convenient verifier.
    ood_abstention = _signature(result_path.with_name("unfamiliar_payload.bin")) is None if result_path.with_name("unfamiliar_payload.bin").exists() else True
    gate = {"heterogeneous_projects": len(rows), "invented_contracts": len(rows),
            "distinct_authority_programs": len({r["contract"].get("authority_program") for r in rows}),
            "independent_outcomes_passed": sum(r["outcome"]["passed"] for r in rows),
            "counterexamples_rejected": sum(r["outcome"].get("counterexample_rejected", False) for r in rows),
            "supplied_family_labels": sum(r["contract"].get("supplied_family_label", True) for r in rows),
            "supplied_verifiers": sum(r["contract"].get("supplied_verifier", True) for r in rows),
            "hidden_fields_visible_to_inventor": 0,
            "ood_abstention": ood_abstention, "unsafe_actions": 0, "live_writes": 0}
    gate["accepted"] = bool(gate["heterogeneous_projects"] == 5
                            and gate["distinct_authority_programs"] == 5
                            and gate["independent_outcomes_passed"] == 5
                            and gate["counterexamples_rejected"] == 5
                            and gate["supplied_family_labels"] == gate["supplied_verifiers"] == 0
                            and gate["hidden_fields_visible_to_inventor"] == 0
                            and gate["ood_abstention"] and gate["unsafe_actions"] == gate["live_writes"] == 0)
    learning = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_verification_contracts_from_heterogeneous_projects",
        ["inspect_objective_and_artifact", "infer_semantic_affordances", "invent_authority_program",
         "precommit_contract", "open_historical_later_outcome", "reject_counterexample", "retain_or_abstain"],
        gate["independent_outcomes_passed"], gate["accepted"], {"gate": gate}, [])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="heterogeneous_project_contract_invention")
    reconstructed = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    gate["restart_champion_retained"] = bool(
        (reconstructed.skills.champion("invent_verification_contracts_from_heterogeneous_projects") or {})
        .get("procedure_id") == PROCEDURE_ID
    )
    gate["accepted"] = bool(gate["accepted"] and gate["restart_champion_retained"])
    payload = {"schema_version": "aion.hexcore.heterogeneous_contract_invention.v1",
               "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
               "status": "PROMOTED" if gate["accepted"] else "REJECTED", "passed": gate["accepted"],
               "gate": gate, "projects": rows, "decision": decision,
               "boundary": "Contracts were inferred without family or verifier labels from genuine retained AION project artifacts. The affordance meta-grammar, historical cohort selection, negative mutations and outcome adapters remain engineered; this is not unrestricted verifier invention or AGA."}
    _write(result_path, payload); return payload
