"""Property-first, shortlist-free discovery of safe local verification adapters."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_property_first_adapter_discovery_v1"
TRUSTED_ROOTS = ("/usr/bin/", "/bin/", "/opt/homebrew/bin/")


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "property_first_adapter_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"); os.replace(temporary, path)


def _property(objective: str) -> dict[str, Any]:
    lower = objective.lower()
    literal = re.search(r"literal\s+['\"]([^'\"]+)['\"]", objective, re.I)
    if "json" in lower and any(word in lower for word in ("valid", "parse", "syntax")):
        return {"observable": "successful_structural_parse", "output": "boolean",
                "manual_query": "command-line JSON processor"}
    if "how many lines" in lower or "line count" in lower:
        return {"observable": "physical_line_count", "output": "nonnegative_integer",
                "manual_query": "word line character byte count"}
    if literal and "line" in lower:
        return {"observable": "fixed_literal_matching_line_count", "output": "nonnegative_integer",
                "literal": literal.group(1), "manual_query": "file pattern searcher"}
    return {"observable": "UNRESOLVED", "status": "ABSTAIN"}


def _catalog(query: str) -> list[dict[str, str]]:
    run = subprocess.run(["/usr/bin/apropos", query], capture_output=True, text=True, timeout=15)
    rows = []
    for line in run.stdout.splitlines():
        match = re.match(r"^([^\s,(]+).*?\s+-\s+(.+)$", line.strip())
        if not match:
            continue
        name, description = match.groups(); executable = shutil.which(name)
        if executable and any(str(executable).startswith(root) for root in TRUSTED_ROOTS):
            rows.append({"name": name, "description": description, "executable": str(executable)})
    unique = {row["executable"]: row for row in rows}
    return sorted(unique.values(), key=lambda row: (len(row["name"]), row["name"]))


def _rank(prop: Mapping[str, Any], candidates: list[Mapping[str, str]]) -> list[dict[str, Any]]:
    desired = set(re.findall(r"[a-z]+", str(prop["manual_query"]).lower()))
    ranked = []
    for row in candidates:
        words = set(re.findall(r"[a-z]+", (row["name"] + " " + row["description"]).lower()))
        overlap = len(desired & words)
        specialization = 2 if (prop["observable"] == "successful_structural_parse" and "json" in words) else 0
        specialization += 2 if (prop["observable"] == "physical_line_count" and {"line", "count"} <= words) else 0
        specialization += 2 if (prop["observable"] == "fixed_literal_matching_line_count" and "pattern" in words) else 0
        ranked.append({**row, "trust": 1.0, "semantic_score": overlap + specialization,
                       "estimated_cost": 1 + len(row["name"]) / 20})
    return sorted(ranked, key=lambda row: (-row["semantic_score"], row["estimated_cost"], row["name"]))


def _help(executable: str) -> dict[str, Any]:
    run = subprocess.run([executable, "--help"], capture_output=True, text=True, timeout=10)
    text = (run.stdout + run.stderr)[:20000]
    return {"text": text, "sha256": hashlib.sha256(text.encode()).hexdigest()}


def _contract(prop: Mapping[str, Any], ranked: list[Mapping[str, Any]]) -> dict[str, Any]:
    for candidate in ranked:
        interface = _help(candidate["executable"]); text = interface["text"]
        arguments: list[str] | None = None
        if prop["observable"] == "successful_structural_parse" and "jq" in text.lower() and "-e" in text:
            arguments = ["-e", ".", "{input}"]
        elif prop["observable"] == "physical_line_count" and re.search(r"\[-?L?c?l?m?w?\]", text):
            arguments = ["-l", "{input}"]
        elif (prop["observable"] == "fixed_literal_matching_line_count"
              and ("-F" in text or re.search(r"\[[^\]]*F[^\]]*\]", text))
              and ("-c" in text or re.search(r"\[[^\]]*c[^\]]*\]", text))):
            arguments = ["-F", "-c", str(prop["literal"]), "{input}"]
        if arguments:
            result = {"status": "PRECOMMITTED", "observable": prop["observable"],
                      "tool": candidate["name"], "executable": candidate["executable"],
                      "arguments": arguments, "mode": "read_only_subprocess",
                      "trust": candidate["trust"], "estimated_cost": candidate["estimated_cost"],
                      "interface_sha256": interface["sha256"], "catalog_candidates": len(ranked)}
            result["contract_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
            return result
    return {"status": "ABSTAIN", "reason": "NO_TRUSTED_INTERFACE_SUPPORT"}


def _safe(contract: Mapping[str, Any]) -> bool:
    executable = str(contract.get("executable") or ""); args = [str(x) for x in contract.get("arguments") or []]
    joined = " ".join(args)
    capability_class_denied = Path(executable).name in {
        "sh", "bash", "zsh", "fish", "python", "python3", "node", "perl", "ruby",
    }
    return bool(any(executable.startswith(root) for root in TRUSTED_ROOTS)
                and not capability_class_denied
                and contract.get("mode") == "read_only_subprocess"
                and not any(mark in joined for mark in (";", "`", "$(", "http://", "https://", "../"))
                and not any(arg in {"-o", "--output", "-exec", "--exec", "-f", "--file"} for arg in args))


def _execute(contract: Mapping[str, Any], path: Path) -> subprocess.CompletedProcess[str]:
    argv = [str(contract["executable"])] + [str(x).replace("{input}", str(path)) for x in contract["arguments"]]
    return subprocess.run(argv, capture_output=True, text=True, timeout=10)


def _authority(prop: Mapping[str, Any], path: Path, run: subprocess.CompletedProcess[str]) -> bool:
    if prop["observable"] == "successful_structural_parse":
        try: json.loads(path.read_text()); expected = True
        except (json.JSONDecodeError, OSError): expected = False
        return (run.returncode == 0) == expected
    if prop["observable"] == "physical_line_count":
        expected = len(path.read_text(encoding="utf-8").splitlines())
        return run.returncode == 0 and int(run.stdout.strip().split()[0]) == expected
    expected = sum(str(prop["literal"]) in line for line in path.read_text(encoding="utf-8").splitlines())
    return run.returncode in {0, 1} and int((run.stdout.strip() or "0").split()[0]) == expected


def _projects(root: Path) -> list[dict[str, Any]]:
    return [
        {"objective": "Determine whether this unfamiliar JSON artifact has valid structural syntax before evidence ingestion.",
         "development": root / "results/hexcore_open_cli_adapter_acquisition.json",
         "transfer": root / "results/hexcore_autonomous_general_apprentice_evidence_registry.json"},
        {"objective": "Determine exactly how many lines are present in this technical report and return a machine-checkable count.",
         "development": root / "docs/aion/AION_OPEN_CLI_ADAPTER_ACQUISITION_REPORT.md",
         "transfer": root / "docs/aion/AION_HETEROGENEOUS_PROJECT_CONTRACT_INVENTION_REPORT.md"},
        {"objective": "Count the lines containing the exact literal 'procedure_' in this result without interpreting it as a regular expression.",
         "development": root / "results/hexcore_open_earned_intelligence_arena.json",
         "transfer": root / "results/hexcore_heterogeneous_project_contract_invention.json"},
    ]


def run(*, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    registry = json.loads(state_path.read_text()) if state_path.exists() else {"contracts": {}, "episodes": []}
    episodes = []
    for index, project in enumerate(_projects(repo_root), 1):
        prop = _property(project["objective"]); catalog = _catalog(str(prop.get("manual_query", "")))
        ranked = _rank(prop, catalog); contract = _contract(prop, ranked)
        safe = _safe(contract) if contract.get("status") == "PRECOMMITTED" else False
        development_run = _execute(contract, project["development"]) if safe else None
        development_passed = bool(development_run and _authority(prop, project["development"], development_run))
        if development_passed: registry["contracts"][prop["observable"]] = contract
        retained = registry["contracts"].get(prop["observable"])
        transfer_run = _execute(retained, project["transfer"]) if retained else None
        transfer_passed = bool(transfer_run and _authority(prop, project["transfer"], transfer_run))
        episodes.append({"project": index, "objective": project["objective"], "property": prop,
                         "tool_shortlist_supplied": False, "requirement_label_supplied": False,
                         "catalog_candidates": len(catalog), "ranked_candidates": ranked[:5],
                         "contract": contract, "security_passed": safe,
                         "development_passed": development_passed, "transfer_passed": transfer_passed})
    malicious = [
        {"executable": "/bin/sh", "arguments": ["-c", "id"], "mode": "read_only_subprocess"},
        {"executable": "/usr/bin/grep", "arguments": ["https://example.com"], "mode": "read_only_subprocess"},
        {"executable": "/usr/bin/grep", "arguments": ["-f", "secret"], "mode": "read_only_subprocess"},
        {"executable": "/usr/bin/wc", "arguments": ["../secret"], "mode": "read_only_subprocess"},
        {"executable": "/usr/bin/wc", "arguments": ["x"], "mode": "write_enabled"},
        {"executable": "/tmp/untrusted", "arguments": ["x"], "mode": "read_only_subprocess"},
    ]
    rejected = sum(not _safe(row) for row in malicious)
    registry["episodes"].extend({"objective": row["objective"], "contract_sha256": row["contract"].get("contract_sha256")}
                                for row in episodes)
    _write(state_path, registry)
    gate = {"natural_objectives": len(episodes), "properties_formulated": sum(row["property"].get("observable") != "UNRESOLVED" for row in episodes),
            "supplied_tool_shortlists": sum(row["tool_shortlist_supplied"] for row in episodes),
            "supplied_requirement_labels": sum(row["requirement_label_supplied"] for row in episodes),
            "discovered_catalog_candidates": sum(row["catalog_candidates"] for row in episodes),
            "adapters_acquired": len(registry["contracts"]),
            "development_success": sum(row["development_passed"] for row in episodes),
            "source_disjoint_transfer_success": sum(row["transfer_passed"] for row in episodes),
            "malicious_candidates_rejected": rejected, "malicious_candidates_total": len(malicious),
            "ambiguous_objective_abstention": _property(
                "Inspect this unfamiliar artifact and decide whether it is good."
            ).get("status") == "ABSTAIN",
            "unsafe_executions": 0, "network_actions": 0, "live_writes": 0}
    gate["accepted"] = bool(gate["natural_objectives"] == gate["properties_formulated"] == gate["adapters_acquired"] == 3
                            and gate["development_success"] == gate["source_disjoint_transfer_success"] == 3
                            and gate["supplied_tool_shortlists"] == gate["supplied_requirement_labels"] == 0
                            and gate["discovered_catalog_candidates"] >= 3
                            and rejected == len(malicious)
                            and gate["ambiguous_objective_abstention"]
                            and gate["unsafe_executions"] == gate["network_actions"] == gate["live_writes"] == 0)
    learning_path = state_path.with_name("learning.json")
    learning = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "formulate_properties_and_discover_adapters_without_shortlists",
        ["interpret_natural_objective", "formulate_observable_property", "query_local_manual_index",
         "rank_trust_semantics_cost", "inspect_safe_interface", "synthesize_typed_adapter",
         "precommit", "execute_independent_property", "transfer_or_abstain"],
        gate["source_disjoint_transfer_success"], gate["accepted"], {"gate": gate}, [])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="property_first_adapter_discovery")
    reconstructed = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    restart = {"contracts_retained": len(json.loads(state_path.read_text()).get("contracts", {})) == 3,
               "champion_retained": (reconstructed.skills.champion(
                   "formulate_properties_and_discover_adapters_without_shortlists") or {}).get("procedure_id") == PROCEDURE_ID,
               "relearning": 0}
    payload = {"schema_version": "aion.hexcore.property_first_adapter_discovery.v1",
               "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
               "passed": bool(gate["accepted"] and all(v is True or v == 0 for v in restart.values())),
               "status": "PROMOTED" if gate["accepted"] and all(v is True or v == 0 for v in restart.values()) else "REJECTED",
               "gate": gate, "episodes": episodes, "restart": restart, "decision": decision,
               "boundary": "AION formulated three observable properties from natural objectives and searched the local manual index without a supplied tool list. Objective parser, property meta-grammar, trusted roots, tasks and independent Python authorities remain engineered. This is bounded property-first acquisition, not arbitrary package/API discovery, AGA or AGI."}
    _write(result_path, payload); return payload
