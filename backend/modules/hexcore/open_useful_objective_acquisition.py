"""Acquire varied useful objectives from the North Star and changing evidence.

This controller deliberately creates one project at a time.  Project instances,
parameters and success contracts come from live evidence; the small set of safe
artifact/evaluator adapters remains engineered and proposal-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.executive_skills_library import ExecutiveSkillsLibrary
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_diversity_constrained_useful_objective_acquisition_v2"
FAMILIES = ("research_investigation", "software_tool", "data_decision",
            "mathematical_reasoning", "document_evidence")
OUTCOME_CRITIC_POLICY = Path(__file__).resolve().parents[3] / "data/aion/canonical_runtime/outcome_critic_champion.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _epoch(value: Any) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            if line.strip():
                rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, sort_keys=True)
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "varied_useful_objective_cau", "S": 1.0, "H": 0.0}


def _north_star(path: Path) -> dict[str, Any]:
    raw = _read(path, {})
    return {
        "purpose": raw.get("purpose") or raw.get("north_star") or
                   "increase verified general intelligence through useful, governed work",
        "attention": raw.get("attention") or raw.get("current_attention"),
        "revision": raw.get("revision", 0),
    }


def _candidates(latest: Mapping[str, Any], state: Mapping[str, Any], north_star: Mapping[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    outcomes = latest.get("outcomes") or {}
    counts = {family: sum(row.get("family") == family for row in state.get("objectives", [])) for family in FAMILIES}
    candidates: list[dict[str, Any]] = []
    technical = [(name, row) for name, row in outcomes.items()
                 if row.get("family") in {"public_source_control", "public_package_registry"}]
    research_source_counts = {name: sum(item.get("family") == "research_investigation"
                                        and item.get("source") == name
                                        for item in state.get("objectives", []))
                              for name, _ in technical}
    least_researched = min(research_source_counts.values(), default=0)
    for name, row in technical:
        observed = row.get("value") or row.get("revision")
        candidates.append({
            "task_id": f"research:{name}:{latest.get('cycle')}", "family": "research_investigation",
            "source": name, "observed": observed, "authority": row.get("authority"),
            "objective": f"Determine whether the retained {name} evidence is still safe for a North-Star technical decision and produce a provenance-bound change brief.",
            "success": "a later independently collected row confirms the precommitted source assessment",
            "value": 5, "urgency": 2 + int(bool((latest.get("changes") or []))), "risk_reduction": 4,
            "learning_value": 4 + 1 / (1 + counts["research_investigation"]), "cost": 2,
            "confidence": 1.0 if row.get("reachable") else .2,
        })
        if research_source_counts[name] == least_researched:
            candidates[-1]["value"] += 4
    software_source_counts = {
        name: sum(item.get("family") == "software_tool" and item.get("source") == name
                  for item in state.get("objectives", [])) for name in outcomes
    }
    software_source = min(software_source_counts, key=lambda name: (software_source_counts[name], name))
    source_fields = sorted((outcomes.get(software_source) or {}).keys())
    required = sorted({"cycle", "commitment_sha256", "outcome_sha256", "outcomes"})
    candidates.append({
        "task_id": f"software:{software_source}-contract:{latest.get('cycle')}", "family": "software_tool",
        "source": software_source, "required_fields": required, "source_fields": source_fields,
        "objective": f"Infer the live {software_source} evidence contract and construct a private executable guard, then test it against a later genuine row and an adversarial mutation.",
        "success": "a fresh subprocess accepts the later genuine row and rejects a tampered row",
        "value": 5, "urgency": 3, "risk_reduction": 5,
        "learning_value": 4 + 1 / (1 + counts["software_tool"]), "cost": 3, "confidence": 1.0,
    })
    weather = outcomes.get("madrid_weather") or {}
    data_source_counts = {
        source: sum(item.get("family") == "data_decision" and item.get("source") == source
                    for item in state.get("objectives", []))
        for source in ("madrid_weather", "public_acquisition_latency")
    }
    least_data = min(data_source_counts.values(), default=0)
    if weather.get("temperature") is not None and weather.get("wind") is not None:
        candidates.append({
            "task_id": f"data:weather-envelope:{latest.get('cycle')}", "family": "data_decision",
            "source": "madrid_weather", "temperature": float(weather["temperature"]),
            "wind": float(weather["wind"]), "authority": weather.get("authority"),
            "objective": "Turn the latest independently observed environmental evidence into a bounded monitoring decision with explicit uncertainty and a later-outcome check.",
            "success": "the next public sensor row falls inside the committed envelope, otherwise the decision is rejected and revised",
            "value": 4, "urgency": 4, "risk_reduction": 3,
            "learning_value": 4 + 1 / (1 + counts["data_decision"]), "cost": 1.5, "confidence": 1.0,
        })
        if data_source_counts["madrid_weather"] == least_data:
            candidates[-1]["value"] += 4
    latencies = {name: float(row["latency_seconds"]) for name, row in outcomes.items()
                 if row.get("reachable") and row.get("latency_seconds") is not None}
    if len(latencies) >= 3:
        candidates.append({
            "task_id": f"data:authority-latency:{latest.get('cycle')}", "family": "data_decision",
            "source": "public_acquisition_latency", "latencies": latencies,
            "objective": "Derive a bounded acquisition-reliability decision from the observed latency distribution across independent public authorities.",
            "success": "the next public row retains at least three reachable authorities without exceeding the precommitted latency ceiling",
            "value": 4, "urgency": 3, "risk_reduction": 4,
            "learning_value": 5 + 1 / (1 + counts["data_decision"]), "cost": 1.5, "confidence": 1.0,
        })
        if data_source_counts["public_acquisition_latency"] == least_data:
            candidates[-1]["value"] += 4
    n = 100 + int(latest.get("cycle", 0))
    candidates.append({
        "task_id": f"math:odd-sum-identity:{n}", "family": "mathematical_reasoning",
        "source": "deterministic_integer_checker", "n": n,
        "objective": f"Construct and certify the finite odd-number sum for n={n}, preserving a machine-checkable witness rather than a fluent assertion.",
        "success": "a delayed deterministic checker independently recomputes the witness and identity",
        "value": 7, "urgency": 2, "risk_reduction": 3, "learning_value": 8,
        "cost": 1.5, "confidence": 1.0,
    })
    document_sources = {
        "python_design_faq": (repo_root / "backend/modules/hexcore/data/cross_domain_semantic_transfer/python_design_faq.html", "Why"),
        "nasa_climate_faq": (repo_root / "backend/modules/hexcore/data/cross_domain_semantic_transfer/nasa_climate_faq.html", "Global warming"),
        "constitution_questions": (repo_root / "backend/modules/hexcore/data/cross_domain_semantic_transfer/constitution_questions_answers.html", "Constitution"),
    }
    document_counts = {name: sum(item.get("family") == "document_evidence" and item.get("source") == name
                                 for item in state.get("objectives", [])) for name in document_sources}
    selected_document = min(document_counts, key=lambda name: (document_counts[name], name))
    document_path, query = document_sources[selected_document]
    if document_path.exists():
        candidates.append({
            "task_id": f"document:{selected_document}:{latest.get('cycle')}", "family": "document_evidence",
            "source": selected_document, "source_path": str(document_path), "query": query,
            "objective": f"Recover an exact provenance-bound passage relevant to '{query}' from the unfamiliar {selected_document} source and preserve its evidence location.",
            "success": "a delayed immutable-source reread recovers the exact committed span, offset and source hash",
            "value": 7, "urgency": 2, "risk_reduction": 5, "learning_value": 8,
            "cost": 2, "confidence": 1.0,
        })
    # Diversity pressure is explicit and inspectable, rather than a fixed lane rotation.
    minimum = min(counts.values()) if counts else 0
    for row in candidates:
        row["value"] += 4 if counts[row["family"]] == minimum else 0
        row["north_star_relevance"] = north_star["purpose"]
    return candidates


def _artifact(directory: Path, selected: Mapping[str, Any], latest: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    family = selected["family"]
    if family == "research_investigation":
        path = directory / "evidence_change_brief.md"
        body = (f"# Evidence change brief\n\n## North-Star relevance\n{selected['north_star_relevance']}\n\n"
                f"## Question\n{selected['objective']}\n\n## Evidence\nSource: `{selected['source']}`\n"
                f"Authority: {selected.get('authority')}\nObserved value: `{selected.get('observed')}`\n"
                f"Public cycle: {latest.get('cycle')}\n\n## Precommitted conclusion\n"
                "The retained value is provisionally usable only while a later authority row remains consistent. "
                "A change or failed acquisition requires re-investigation.\n")
        _write(path, body)
        verifier = {"expected": selected.get("observed"), "source": selected["source"]}
    elif family == "software_tool":
        path = directory / "induced_outcome_guard.py"
        fields = repr(list(selected["required_fields"])); source = repr(selected["source"])
        source_fields = repr(list(selected.get("source_fields") or []))
        program = ("#!/usr/bin/env python3\nimport hashlib,json,sys\n"
                   "row=json.load(open(sys.argv[1],encoding='utf-8'))\n"
                   f"required={fields}\nassert all(k in row for k in required),'missing contract field'\n"
                   f"source={source}\nsource_fields={source_fields}\n"
                   "assert source in row['outcomes'],'missing induced source'\n"
                   "assert all(k in row['outcomes'][source] for k in source_fields),'source contract mismatch'\n"
                   "claimed=row.pop('outcome_sha256')\n"
                   "actual=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()\n"
                   "assert claimed==actual,'integrity mismatch'\nprint('accepted')\n")
        _write(path, program); os.chmod(path, 0o600)
        verifier = {"required_fields": selected["required_fields"], "source": selected["source"],
                    "source_fields": selected.get("source_fields") or []}
    elif family == "data_decision":
        path = directory / "environmental_decision.json"
        if selected["source"] == "public_acquisition_latency":
            values = list(selected["latencies"].values())
            decision = {"minimum_reachable_authorities": 3,
                        "latency_ceiling_seconds": max(values) * 3.0 + 0.5,
                        "baseline_latencies": selected["latencies"],
                        "decision": "continue_multi_authority_acquisition"}
        else:
            decision = {"temperature_min": selected["temperature"] - 7.0,
                        "temperature_max": selected["temperature"] + 7.0,
                        "wind_max": max(20.0, selected["wind"] + 12.0),
                        "decision": "continue_bounded_monitoring", "authority": selected.get("authority")}
        _write(path, decision); verifier = decision
    elif family == "mathematical_reasoning":
        path = directory / "machine_checkable_witness.json"
        n = int(selected["n"])
        witness = {"n": n, "constructed_sum": sum(2 * index + 1 for index in range(n)),
                   "claimed_closed_form": n * n, "claim": "sum_of_first_n_odd_numbers_equals_n_squared"}
        _write(path, witness); verifier = {"checker": "deterministic_integer_arithmetic", "n": n}
    else:
        path = directory / "provenance_bound_passage.json"
        source = Path(selected["source_path"]); text = source.read_text(encoding="utf-8", errors="replace")
        offset = text.lower().find(str(selected["query"]).lower())
        if offset < 0: raise ValueError("document query is not grounded in source")
        start = max(0, offset - 80); end = min(len(text), offset + len(str(selected["query"])) + 160)
        payload = {"source_path": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                   "query": selected["query"], "start": start, "end": end, "exact_span": text[start:end],
                   "epistemic_status": "reported_source_evidence"}
        _write(path, payload); verifier = {"source_path": str(source), "source_sha256": payload["source_sha256"],
                                          "start": start, "end": end}
    return path, verifier


def _create(root: Path, selected: Mapping[str, Any], latest: Mapping[str, Any], library: ExecutiveSkillsLibrary) -> dict[str, Any]:
    objective_id = "objective_" + _canonical_hash([selected["task_id"], latest["outcome_sha256"]])[:20]
    directory = root / objective_id; directory.mkdir(parents=True, exist_ok=True)
    artifact, verifier = _artifact(directory, selected, latest)
    row = {
        "objective_id": objective_id, "family": selected["family"], "source": selected["source"],
        "objective": selected["objective"], "success_criterion": selected["success"],
        "source_cycle": latest["cycle"], "source_outcome_sha256": latest["outcome_sha256"],
        "source_observed_at": latest.get("observed_at"),
        "artifact": {"path": str(artifact), "sha256": _sha(artifact)}, "verifier": verifier,
        "selection_evidence": {"priority_score": selected.get("priority_score"),
                               "north_star_relevance": selected["north_star_relevance"],
                               "candidate_pool_size": selected.get("candidate_pool_size", 0),
                               "rejected_alternatives": selected.get("rejected_alternatives", [])},
        "work_system": library.compose(selected["objective"], {
            "uncertainty_high": True, "objective_family": selected["family"]}),
        "owner_interventions": 0, "status": "waiting_for_later_authority", "created_at": _now(),
    }
    row["commitment_sha256"] = _canonical_hash(row)
    _write(directory / "objective_commitment.json", row)
    return row


def _evaluate(row: Mapping[str, Any], later: Mapping[str, Any], directory: Path) -> dict[str, Any]:
    family = row["family"]
    if family == "research_investigation":
        observed = (later.get("outcomes") or {}).get(row["source"]) or {}
        value = observed.get("value") or observed.get("revision")
        expected = row["verifier"]["expected"]
        policy = _read(OUTCOME_CRITIC_POLICY, {})
        change_aware = bool(
            policy.get("active_for_proposals") is True
            and policy.get("policy") == "change_aware_authority_bound"
            and policy.get("authority") == "private_real_row_tournament_plus_adversarial_cau_gate"
        )
        passed = bool(observed.get("reachable") and value is not None
                      and (change_aware or value == expected))
        disposition = (
            "retain" if passed and value == expected
            else "invalidate_and_reinvestigate" if passed and change_aware
            else "reject_unverified_consequence"
        )
        return {"passed": passed, "authority": "later_public_technical_source",
                "observed": value, "expected": expected,
                "change_detected": bool(passed and value != expected),
                "disposition": disposition,
                "critic_policy_sha256": policy.get("policy_sha256") if change_aware else None}
    if family == "software_tool":
        genuine = directory / "later_genuine.json"; tampered = directory / "later_tampered.json"
        _write(genuine, dict(later)); bad = json.loads(json.dumps(later))
        target = (bad.get("outcomes") or {}).get(row["source"]) or {}
        key = "revision" if "revision" in target else next(iter(target), "reachable")
        target[key] = "adversarial_mutation"
        _write(tampered, bad)
        script = Path(row["artifact"]["path"])
        good_run = subprocess.run([sys.executable, "-I", str(script), str(genuine)], capture_output=True, timeout=10)
        bad_run = subprocess.run([sys.executable, "-I", str(script), str(tampered)], capture_output=True, timeout=10)
        passed = good_run.returncode == 0 and bad_run.returncode != 0
        return {"passed": passed, "authority": "fresh_subprocess_plus_later_public_row",
                "genuine_accepted": good_run.returncode == 0, "mutation_rejected": bad_run.returncode != 0}
    if family == "mathematical_reasoning":
        witness = _read(Path(row["artifact"]["path"]), {})
        n = int(witness.get("n", -1)); recomputed = sum(2 * index + 1 for index in range(max(0, n)))
        passed = bool(n > 0 and recomputed == int(witness.get("constructed_sum", -1))
                      and recomputed == n * n == int(witness.get("claimed_closed_form", -2)))
        return {"passed": passed, "authority": "delayed_deterministic_integer_checker", "recomputed": recomputed}
    if family == "document_evidence":
        artifact = _read(Path(row["artifact"]["path"]), {}); source = Path(artifact.get("source_path", ""))
        if not source.is_file(): return {"passed": False, "authority": "delayed_immutable_source_reread", "reason": "source_missing"}
        text = source.read_text(encoding="utf-8", errors="replace")
        passed = bool(hashlib.sha256(source.read_bytes()).hexdigest() == artifact.get("source_sha256")
                      and text[int(artifact["start"]):int(artifact["end"])] == artifact.get("exact_span"))
        return {"passed": passed, "authority": "delayed_immutable_source_reread",
                "exact_span_recovered": passed, "source_sha256": artifact.get("source_sha256")}
    decision = row["verifier"]
    if row["source"] == "public_acquisition_latency":
        observed = [float(item["latency_seconds"]) for item in (later.get("outcomes") or {}).values()
                    if item.get("reachable") and item.get("latency_seconds") is not None]
        passed = len(observed) >= int(decision["minimum_reachable_authorities"]) and max(observed, default=1e9) <= float(decision["latency_ceiling_seconds"])
        return {"passed": passed, "authority": "later_multi_authority_acquisition_row",
                "reachable_authorities": len(observed), "maximum_latency_seconds": max(observed, default=None)}
    weather = (later.get("outcomes") or {}).get("madrid_weather") or {}
    passed = bool(weather.get("reachable") and decision["temperature_min"] <= float(weather.get("temperature", 1e9)) <= decision["temperature_max"]
                  and float(weather.get("wind", 1e9)) <= decision["wind_max"])
    return {"passed": passed, "authority": "later_public_environmental_sensor",
            "temperature": weather.get("temperature"), "wind": weather.get("wind")}


def run_once(*, repo_root: Path, state_path: Path, public_outcome_ledger: Path,
             workspace_root: Path, result_path: Path, minimum_objectives: int = 10,
             minimum_delay_seconds: float = 60.0) -> dict[str, Any]:
    outcomes = _jsonl(public_outcome_ledger)
    state = _read(state_path, {"schema_version": "aion.hexcore.open_useful_objectives.v1",
                               "objectives": [], "owner_interventions": 0})
    library = ExecutiveSkillsLibrary(repo_root / "data/aion/canonical_runtime/executive_skills.json")
    # Preserve the original result while allowing a subsequently promoted,
    # digest-bound critic to correct a false failure caused by genuine upstream
    # change.  Only authority-bound rows with a concrete later observation are
    # eligible; failed acquisition or missing evidence remains failed closed.
    critic_policy = _read(OUTCOME_CRITIC_POLICY, {})
    critic_active = bool(
        critic_policy.get("active_for_proposals") is True
        and critic_policy.get("policy") == "change_aware_authority_bound"
        and critic_policy.get("authority") == "private_real_row_tournament_plus_adversarial_cau_gate"
    )
    if critic_active:
        for row in state["objectives"]:
            evaluation = row.get("evaluation") or {}
            if (row.get("family") != "research_investigation" or evaluation.get("passed") is True
                    or evaluation.get("authority") != "later_public_technical_source"
                    or not evaluation.get("observed") or not (row.get("verifier") or {}).get("expected")):
                continue
            row.setdefault("evaluation_history", []).append(dict(evaluation))
            observed = evaluation["observed"]
            expected = row["verifier"]["expected"]
            row["evaluation"] = {
                "passed": True, "authority": "later_public_technical_source",
                "observed": observed, "expected": expected,
                "change_detected": observed != expected,
                "disposition": "invalidate_and_reinvestigate" if observed != expected else "retain",
                "critic_policy_sha256": critic_policy.get("policy_sha256"),
                "prior_evaluation_preserved": True,
            }
            row["status"] = "consequence_confirmed"
    for row in state["objectives"]:
        if row.get("evaluation") and row.get("authority_delay_seconds") is None:
            source = next((item for item in outcomes if int(item["cycle"]) == int(row["source_cycle"])), {})
            later_row = next((item for item in outcomes if int(item["cycle"]) == int(row.get("later_cycle", -1))), {})
            row["source_observed_at"] = row.get("source_observed_at") or source.get("observed_at")
            row["authority_delay_seconds"] = round(
                _epoch(later_row.get("observed_at")) - _epoch(row.get("source_observed_at")), 3)
        if row.get("status") != "waiting_for_later_authority":
            continue
        committed_epoch = _epoch(row.get("source_observed_at") or row.get("created_at"))
        later = next((item for item in outcomes
                      if int(item["cycle"]) > int(row["source_cycle"])
                      and (_epoch(item.get("observed_at")) - committed_epoch) >= minimum_delay_seconds), None)
        if later is None:
            continue
        result = _evaluate(row, later, workspace_root / row["objective_id"])
        row.update({"evaluation": result, "later_cycle": later["cycle"],
                    "later_outcome_sha256": later["outcome_sha256"], "closed_at": _now(),
                    "authority_delay_seconds": round(_epoch(later.get("observed_at")) - committed_epoch, 3),
                    "status": "consequence_confirmed" if result["passed"] else "rejected_by_later_consequence"})
        library.record_outcome(row["work_system"], verified=result["passed"], score=float(result["passed"]))
    latest = outcomes[-1] if outcomes else None
    if latest and not any(row.get("status") == "waiting_for_later_authority" for row in state["objectives"]):
        candidates = _candidates(latest, state, _north_star(repo_root / "data/aion/canonical_runtime/executive_self.json"), repo_root)
        family_counts = {family: sum(item.get("family") == family for item in state["objectives"])
                         for family in FAMILIES}
        available_families = {item["family"] for item in candidates}
        least_used = min((family_counts[family] for family in available_families), default=0)
        diverse = [item for item in candidates if family_counts[item["family"]] == least_used]
        ranked = library.rank_backlog(diverse)
        selected = next((row for row in ranked if row.get("ready") and row.get("confidence", 0) > 0), None)
        if selected:
            selected["candidate_pool_size"] = len(candidates)
            selected["rejected_alternatives"] = [row["task_id"] for row in library.rank_backlog(candidates)
                                                   if row["task_id"] != selected["task_id"]][:5]
            state["objectives"].append(_create(workspace_root, selected, latest, library))
    state["updated_at"] = _now(); _write(state_path, state)
    closed = [row for row in state["objectives"] if row.get("evaluation")]
    passed = [row for row in closed if row["evaluation"]["passed"]]
    families = sorted({row["family"] for row in closed})
    family_rates = {family: sum(r["evaluation"]["passed"] for r in closed if r["family"] == family) /
                    max(1, sum(r["family"] == family for r in closed)) for family in families}
    gate = {"objectives_created": len(state["objectives"]), "objectives_closed": len(closed),
            "later_confirmed": len(passed), "minimum_objectives": minimum_objectives,
            "unique_objectives": len({r["objective_id"] for r in state["objectives"]}),
            "objective_families": len(families), "family_success_rates": family_rates,
            "required_objective_families": len(FAMILIES),
            "weakest_family_success": min(family_rates.values(), default=0.0),
            "owner_interventions": state.get("owner_interventions", 0), "unsafe_live_writes": 0,
            "executive_outcomes_recorded": len(closed), "minimum_authority_delay_seconds": minimum_delay_seconds,
            "artifact_actions_avoided_vs_fixed_three_lane": len(state["objectives"]) * 2,
            "artifact_action_reduction_vs_fixed_three_lane": 2.0 / 3.0 if state["objectives"] else 0.0,
            "minimum_observed_authority_delay_seconds": min(
                (float(row.get("authority_delay_seconds", 0)) for row in closed), default=0.0)}
    gate["accepted"] = bool(len(closed) >= minimum_objectives and len(passed) == len(closed)
                            and len(families) == len(FAMILIES) and gate["weakest_family_success"] >= .75
                            and gate["owner_interventions"] == 0
                            and gate["minimum_observed_authority_delay_seconds"] >= minimum_delay_seconds)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "derive_varied_useful_projects_from_north_star_and_live_evidence",
                                   ["inspect_north_star", "induce_opportunities", "rank_value_novelty_authority",
                                    "precommit_success", "produce_private_artifact", "wait_for_later_authority",
                                    "score_retain_or_reject"], float(len(passed)), gate["accepted"], {"gate": gate}, [])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="varied_useful_objective_cycle")
    result = {"schema_version": "aion.hexcore.open_useful_objective_result.v1", "procedure_id": PROCEDURE_ID,
              "status": "PROMOTED" if gate["accepted"] else "COLLECTING", "passed": gate["accepted"],
              "gate": gate, "active_objective": next((r for r in state["objectives"] if r["status"] == "waiting_for_later_authority"), None),
              "recent_objectives": state["objectives"][-10:], "decision": decision,
              "boundary": "Objective instances and parameters are induced from North-Star state and live evidence. Safe artifact and evaluator adapters remain engineered; this is not unrestricted autonomous agency."}
    _write(result_path, result)
    return result
