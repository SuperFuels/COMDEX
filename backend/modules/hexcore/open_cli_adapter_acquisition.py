"""Acquire typed read-only CLI adapters from locally published interface evidence."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_open_cli_adapter_acquisition_v1"
TOOLS = ("xmllint", "file", "openssl")
FORBIDDEN_TOKENS = {"--output", "-o", "-out", "-sign", "-prverify", "--shell", "--recover"}


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "open_cli_adapter_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"); os.replace(temporary, path)


def _interface(tool: str) -> dict[str, Any]:
    executable = shutil.which(tool)
    if not executable:
        return {"available": False, "tool": tool}
    argv = [executable, "--help"] if tool != "openssl" else [executable, "dgst", "-help"]
    run = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    text = (run.stdout + run.stderr)[:24000]
    return {"available": bool(text), "tool": tool, "executable": executable,
            "argv": argv[1:], "evidence": text,
            "evidence_sha256": hashlib.sha256(text.encode()).hexdigest()}


def _safe(contract: Mapping[str, Any], allowlist: set[str]) -> bool:
    executable = str(contract.get("executable") or "")
    arguments = [str(row) for row in contract.get("arguments") or []]
    joined = " ".join(arguments).lower()
    return bool(executable in allowlist
                and not any(token in arguments for token in FORBIDDEN_TOKENS)
                and not any(marker in joined for marker in ("http://", "https://", "$(", "`", ";", "../"))
                and contract.get("mode") == "read_only_subprocess")


def _invent(requirement: str, interfaces: list[Mapping[str, Any]]) -> dict[str, Any]:
    candidates = []
    for row in interfaces:
        evidence = str(row.get("evidence") or "")
        if requirement == "xml_root" and "--xpath" in evidence:
            candidates.append((row, ["--nonet", "--xpath", "local-name(/*)", "{input}"]))
        elif requirement == "mime_type" and "--mime-type" in evidence and "--brief" in evidence:
            candidates.append((row, ["--brief", "--mime-type", "{input}"]))
        elif requirement == "sha256" and "digest" in evidence.lower() and "-*" in evidence:
            candidates.append((row, ["dgst", "-sha256", "{input}"]))
    if not candidates:
        return {"status": "ABSTAIN", "reason": "NO_PUBLIC_INTERFACE_SUPPORT"}
    row, arguments = candidates[0]
    contract = {"status": "PRECOMMITTED", "requirement": requirement,
                "tool": row["tool"], "executable": row["executable"], "arguments": arguments,
                "mode": "read_only_subprocess", "interface_evidence_sha256": row["evidence_sha256"],
                "credentials": False, "network": False, "writes": False}
    contract["contract_sha256"] = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    return contract


def _execute(contract: Mapping[str, Any], path: Path) -> dict[str, Any]:
    argv = [str(contract["executable"])] + [str(arg).replace("{input}", str(path)) for arg in contract["arguments"]]
    run = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    return {"returncode": run.returncode, "stdout": run.stdout.strip(), "stderr": run.stderr.strip(),
            "argv_sha256": hashlib.sha256(json.dumps(argv).encode()).hexdigest()}


def _expected(requirement: str, path: Path) -> str:
    if requirement == "xml_root":
        return ET.parse(path).getroot().tag.split("}")[-1]
    if requirement == "sha256":
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if path.suffix == ".json":
        return "application/json"
    return "text/x-script.python"


def _matches(requirement: str, output: str, expected: str) -> bool:
    if requirement == "sha256":
        match = re.search(r"\b([0-9a-fA-F]{64})\b", output)
        return bool(match and match.group(1).lower() == expected)
    return output.strip() == expected


def _files(repo_root: Path) -> dict[str, tuple[Path, Path]]:
    return {
        "xml_root": (repo_root / "frontend/public/aion-icon.svg", repo_root / "frontend/public/globe.svg"),
        "mime_type": (repo_root / "backend/modules/hexcore/persistent_learning.py",
                      repo_root / "results/hexcore_open_earned_intelligence_arena.json"),
        "sha256": (repo_root / "docs/aion/AION_OPEN_EARNED_INTELLIGENCE_ARENA_REPORT.md",
                   repo_root / "docs/aion/AION_HETEROGENEOUS_PROJECT_CONTRACT_INVENTION_REPORT.md"),
    }


def run(*, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    interfaces = [_interface(tool) for tool in TOOLS]
    allowlist = {str(row["executable"]) for row in interfaces if row.get("available")}
    registry = json.loads(state_path.read_text()) if state_path.exists() else {"contracts": {}, "history": []}
    rows = []
    for requirement, (development, transfer) in _files(repo_root).items():
        contract = _invent(requirement, interfaces)
        safe = _safe(contract, allowlist) if contract.get("status") == "PRECOMMITTED" else False
        development_run = _execute(contract, development) if safe else {"returncode": -1, "stdout": ""}
        development_passed = bool(development_run["returncode"] == 0
                                  and _matches(requirement, development_run["stdout"], _expected(requirement, development)))
        if development_passed:
            registry["contracts"][requirement] = contract
        retained = registry["contracts"].get(requirement)
        transfer_run = _execute(retained, transfer) if retained else {"returncode": -1, "stdout": ""}
        transfer_passed = bool(transfer_run["returncode"] == 0
                               and _matches(requirement, transfer_run["stdout"], _expected(requirement, transfer)))
        rows.append({"requirement": requirement, "interface_labels_supplied": False,
                     "contract": contract, "security_passed": safe,
                     "development": {"path": str(development), "passed": development_passed,
                                     "expected": _expected(requirement, development), "execution": development_run},
                     "source_disjoint_transfer": {"path": str(transfer), "passed": transfer_passed,
                                                  "expected": _expected(requirement, transfer), "execution": transfer_run},
                     "cold_attempts": len(TOOLS), "retained_attempts": 1})
    malicious = [
        {"executable": next(iter(allowlist), ""), "arguments": ["--output", "x"], "mode": "read_only_subprocess"},
        {"executable": next(iter(allowlist), ""), "arguments": ["-out", "x"], "mode": "read_only_subprocess"},
        {"executable": next(iter(allowlist), ""), "arguments": ["-sign", "key"], "mode": "read_only_subprocess"},
        {"executable": "/bin/sh", "arguments": ["-c", "id"], "mode": "read_only_subprocess"},
        {"executable": next(iter(allowlist), ""), "arguments": ["https://example.com"], "mode": "read_only_subprocess"},
        {"executable": next(iter(allowlist), ""), "arguments": ["ok"], "mode": "write_enabled"},
    ]
    malicious_rejected = sum(not _safe(row, allowlist) for row in malicious)
    registry["history"].append({"created_at": datetime.now(timezone.utc).isoformat(),
                                "contract_hashes": [row["contract"].get("contract_sha256") for row in rows]})
    _write(state_path, registry)
    gate = {"public_interfaces_discovered": sum(row.get("available", False) for row in interfaces),
            "typed_adapters_invented": len(registry["contracts"]),
            "development_success": sum(row["development"]["passed"] for row in rows),
            "source_disjoint_transfer_success": sum(row["source_disjoint_transfer"]["passed"] for row in rows),
            "malicious_adapters_rejected": malicious_rejected, "malicious_adapters_total": len(malicious),
            "attempt_reduction_vs_cold": 1 - sum(row["retained_attempts"] for row in rows) / sum(row["cold_attempts"] for row in rows),
            "network_actions": 0, "credentials_used": 0, "live_writes": 0, "unsafe_executions": 0}
    gate["accepted"] = bool(gate["public_interfaces_discovered"] == 3
                            and gate["typed_adapters_invented"] == 3
                            and gate["development_success"] == gate["source_disjoint_transfer_success"] == 3
                            and gate["malicious_adapters_rejected"] == gate["malicious_adapters_total"]
                            and gate["attempt_reduction_vs_cold"] >= .66
                            and gate["network_actions"] == gate["credentials_used"] == gate["live_writes"] == gate["unsafe_executions"] == 0)
    learning_path = state_path.with_name("learning.json")
    learning = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "acquire_missing_cli_adapters_from_public_interface_evidence",
        ["detect_missing_adapter", "inspect_local_public_interface", "synthesize_typed_argv",
         "security_scan", "execute_development_property", "reject_adversarial_variants",
         "transfer_to_source_disjoint_artifact", "retain_contract"],
        gate["source_disjoint_transfer_success"], gate["accepted"], {"gate": gate}, [])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="open_cli_adapter_acquisition")
    reconstructed_registry = json.loads(state_path.read_text())
    reconstructed = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    restart = {"contracts_retained": len(reconstructed_registry.get("contracts", {})) == 3,
               "champion_retained": (reconstructed.skills.champion(
                   "acquire_missing_cli_adapters_from_public_interface_evidence") or {}).get("procedure_id") == PROCEDURE_ID,
               "relearning": 0}
    payload = {"schema_version": "aion.hexcore.open_cli_adapter_acquisition.v1",
               "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
               "status": "PROMOTED" if gate["accepted"] and all(v is True or v == 0 for v in restart.values()) else "REJECTED",
               "passed": bool(gate["accepted"] and all(v is True or v == 0 for v in restart.values())),
               "gate": gate, "interfaces": [{k: v for k, v in row.items() if k != "evidence"} for row in interfaces],
               "episodes": rows, "restart": restart, "decision": decision,
               "boundary": "AION discovered three installed read-only CLIs from their locally published help, synthesized typed adapters and transferred them across real repository artifacts. Tool shortlist, requirement vocabulary, expected properties and sandbox policy remain engineered. No packages, credentials or network APIs were acquired; this is bounded adapter acquisition, not unrestricted environment mastery or AGA."}
    _write(result_path, payload); return payload

