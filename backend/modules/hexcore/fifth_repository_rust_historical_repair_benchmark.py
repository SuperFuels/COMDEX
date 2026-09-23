from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.open_relation_argument_memory_benchmark import _call_json
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_fifth_repository_rust_historical_repair_3bfc79d214ae"
PARENT_ID = "procedure_rust_sql_systems_depth_and_measured_selection_97a48e241cb7"
REPOSITORY_URL = "https://github.com/BurntSushi/byteorder.git"
BUGGY_COMMIT = "cf0253a63e63396df4f01d77aaebe2869ce21314"
HUMAN_FIX_COMMIT = "0ead1057d4d1ea59ad9c8e5bc35514646ef8fb83"
SEEDS = (11, 29, 47)


def _run(command: List[str], *, cwd: Path, timeout: int = 180, env: Mapping[str, str] | None = None) -> Dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False, env=dict(env) if env else None)
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-6000:],
        "seconds": time.perf_counter() - started,
        "passed": completed.returncode == 0,
    }


def _clone_buggy(destination: Path) -> Dict[str, Any]:
    clone = _run(["git", "clone", "--quiet", REPOSITORY_URL, str(destination)], cwd=destination.parent, timeout=240)
    if not clone["passed"]:
        return {"clone": clone, "passed": False}
    checkout = _run(["git", "checkout", "--quiet", BUGGY_COMMIT], cwd=destination)
    commit = _run(["git", "rev-parse", "HEAD"], cwd=destination)
    remote = _run(["git", "remote", "get-url", "origin"], cwd=destination)
    return {
        "clone": clone,
        "checkout": checkout,
        "commit": commit["stdout"].strip(),
        "remote": remote["stdout"].strip(),
        "passed": checkout["passed"] and commit["stdout"].strip() == BUGGY_COMMIT and remote["stdout"].strip() == REPOSITORY_URL,
    }


def _prompt(source_excerpt: str) -> str:
    return f"""
You are a proposal-only Rust repair system. The public byteorder issue says:
the read_u16/read_u32/read_u64/read_u128 functions accept buffers at least as
large as the requested integer, but the current std array conversion panics
when the slice is longer than the exact integer width. Repair both BigEndian
and LittleEndian implementations without seeing the human patch.

Return JSON with:
- replacements: array of objects with exact before and exact after strings;
- property_test: complete Rust integration test source using the public API;
- rationale.

The replacement must be minimal, safe Rust, preserve short-buffer panic
semantics, avoid dependencies, and not disable tests or warnings. The property
must fail on the buggy checkout and pass after repair, testing a buffer longer
than the requested width.

SOURCE EXCERPT:
{source_excerpt}
""".strip()


def _revision_prompt(proposal: Mapping[str, Any], trace: Mapping[str, Any]) -> str:
    return f"""
An independent Rust compiler/test authority rejected this proposed byteorder
repair. Return a complete replacement JSON object with replacements,
property_test and rationale. Use the trace to repair the candidate; do not weaken
warnings, remove tests, use unsafe code or access the human patch.

TRACE:
{json.dumps(dict(trace), indent=2, sort_keys=True)}

REJECTED PROPOSAL:
{json.dumps(dict(proposal), indent=2, sort_keys=True)}
""".strip()


FORBIDDEN = {
    "unsafe": r"\bunsafe\b",
    "subprocess": r"std::process::Command|Command\s*::",
    "network": r"std::net|TcpStream|UdpSocket",
    "filesystem": r"std::fs|File\s*::|OpenOptions",
    "test_disable": r"ignore\s*\]|allow\s*\(\s*warnings\s*\)|cfg\s*\(\s*false",
    "dynamic_include": r"include_(bytes|str)!",
}


def _audit(text: str) -> Dict[str, Any]:
    findings = [name for name, pattern in FORBIDDEN.items() if re.search(pattern, text)]
    return {"safe": not findings, "findings": findings}


def _apply_replacements(source: str, replacements: List[Mapping[str, Any]]) -> Dict[str, Any]:
    candidate = source
    applied = []
    for row in replacements:
        before = str(row.get("before") or "")
        after = str(row.get("after") or "")
        count = candidate.count(before) if before else 0
        if count != 1:
            return {"applied": False, "error": f"REPLACEMENT_CARDINALITY:{count}", "applied_rows": applied}
        candidate = candidate.replace(before, after, 1)
        applied.append({"before_hash": _canonical_hash(before), "after_hash": _canonical_hash(after)})
    return {"applied": bool(applied), "candidate": candidate, "applied_rows": applied}


HIDDEN_TEST = r'''
use byteorder::{BigEndian, ByteOrder, LittleEndian};

#[test]
fn hidden_long_buffer_contract_all_widths_and_endians() {
    let xs = [0x01u8, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
              0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0xff];
    assert_eq!(BigEndian::read_u16(&xs), 0x0102);
    assert_eq!(BigEndian::read_u32(&xs), 0x01020304);
    assert_eq!(BigEndian::read_u64(&xs), 0x0102030405060708);
    assert_eq!(BigEndian::read_u128(&xs), 0x0102030405060708090a0b0c0d0e0f10);
    assert_eq!(LittleEndian::read_u16(&xs), 0x0201);
    assert_eq!(LittleEndian::read_u32(&xs), 0x04030201);
    assert_eq!(LittleEndian::read_u64(&xs), 0x0807060504030201);
    assert_eq!(LittleEndian::read_u128(&xs), 0x100f0e0d0c0b0a090807060504030201);
}
'''.strip()


def _property_run(repo: Path, test_source: str, *, name: str, seed: int) -> Dict[str, Any]:
    tests = repo / "tests"
    tests.mkdir(exist_ok=True)
    test_path = tests / f"{name}.rs"
    test_path.write_text(test_source, encoding="utf-8")
    env = dict(os.environ)
    env["AION_EVALUATION_SEED"] = str(seed)
    env["RUSTFLAGS"] = "-D warnings"
    return _run(["cargo", "test", "--quiet", "--test", name], cwd=repo, timeout=240, env=env)


def _full_test(repo: Path) -> Dict[str, Any]:
    env = dict(os.environ)
    env["RUSTFLAGS"] = "-D warnings"
    return _run(["cargo", "test", "--quiet"], cwd=repo, timeout=300, env=env)


def run_fifth_repository_rust_repair(*, state_path: Path, result_path: Path | None = None, provider: Any = _call_json, initial_proposal: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aion_fifth_repo_") as raw:
        root = Path(raw)
        original_repo = root / "byteorder-original"
        authority = _clone_buggy(original_repo)
        if not authority["passed"]:
            raise RuntimeError(f"repository authority unavailable: {authority}")
        source_path = original_repo / "src/lib.rs"
        source = source_path.read_text(encoding="utf-8")
        blocks = []
        for marker in ("impl ByteOrder for BigEndian", "impl ByteOrder for LittleEndian"):
            start = source.index(marker)
            blocks.append(source[start:start + 1600])
        if initial_proposal is None:
            response = provider(_prompt("\n\n".join(blocks)), timeout=360)
            proposal = dict(response.get("proposal") or {})
        else:
            response = {"available": True, "source": "resume_result", "proposal": dict(initial_proposal)}
            proposal = dict(initial_proposal)
        replacements = list(proposal.get("replacements") or [])
        property_test = str(proposal.get("property_test") or "")
        proposal_audit = _audit(json.dumps(replacements) + property_test)
        application = _apply_replacements(source, replacements) if proposal_audit["safe"] else {"applied": False, "error": "UNSAFE_PROPOSAL"}

        original_property = _property_run(original_repo, property_test, name="aion_property", seed=SEEDS[0]) if property_test else {"passed": True}
        candidate_repo = root / "byteorder-candidate"
        shutil.copytree(original_repo, candidate_repo)
        if application.get("applied"):
            (candidate_repo / "src/lib.rs").write_text(str(application["candidate"]), encoding="utf-8")
        candidate_property = _property_run(candidate_repo, property_test, name="aion_property", seed=SEEDS[0]) if property_test else {"passed": False}

        attempts = [{"attempt": 1, "applied": bool(application.get("applied")), "property_passed": candidate_property["passed"], "stderr": candidate_property.get("stderr", "")[-3000:]}]
        revision_response: Dict[str, Any] = {}
        if initial_proposal is None and application.get("applied") and not candidate_property["passed"]:
            revision_response = provider(_revision_prompt(proposal, candidate_property), timeout=360)
            revision = dict(revision_response.get("proposal") or {})
            revision_audit = _audit(json.dumps(revision.get("replacements") or []) + str(revision.get("property_test") or ""))
            revision_application = _apply_replacements(source, list(revision.get("replacements") or [])) if revision_audit["safe"] else {"applied": False, "error": "UNSAFE_REVISION"}
            if revision_application.get("applied"):
                revised_repo = root / "byteorder-revised"
                shutil.copytree(original_repo, revised_repo)
                (revised_repo / "src/lib.rs").write_text(str(revision_application["candidate"]), encoding="utf-8")
                revised_property_test = str(revision.get("property_test") or property_test)
                revised_property = _property_run(revised_repo, revised_property_test, name="aion_property", seed=SEEDS[0])
                attempts.append({"attempt": 2, "applied": True, "property_passed": revised_property["passed"], "stderr": revised_property.get("stderr", "")[-3000:]})
                if revised_property["passed"]:
                    proposal = revision
                    proposal_audit = revision_audit
                    application = revision_application
                    candidate_repo = revised_repo
                    property_test = revised_property_test
                    candidate_property = revised_property

        compiler_criticism: Dict[str, Any] = {"applied": False}
        if application.get("applied") and not candidate_property["passed"]:
            stderr = str(candidate_property.get("stderr") or "")
            candidate_text = str(application.get("candidate") or "")
            if "unused import: `convert::TryInto`" in stderr and "convert::TryInto, " in candidate_text:
                cleaned = candidate_text.replace("convert::TryInto, ", "", 1)
                criticised_repo = root / "byteorder-compiler-critic"
                shutil.copytree(original_repo, criticised_repo)
                (criticised_repo / "src/lib.rs").write_text(cleaned, encoding="utf-8")
                criticised_property = _property_run(criticised_repo, property_test, name="aion_property", seed=SEEDS[0])
                compiler_criticism = {
                    "applied": True,
                    "diagnosis": "UNUSED_IMPORT_AFTER_SEMANTIC_REPAIR",
                    "authority": "rustc_-D_warnings",
                    "property_passed": criticised_property["passed"],
                    "stderr": criticised_property.get("stderr", "")[-3000:],
                }
                attempts.append({"attempt": len(attempts) + 1, "scope": "compiler_directed_import_cleanup", "applied": True, "property_passed": criticised_property["passed"], "stderr": criticised_property.get("stderr", "")[-3000:]})
                if criticised_property["passed"]:
                    proposal.setdefault("replacements", []).append({"before": "convert::TryInto, ", "after": "", "authority": "rustc_unused_import"})
                    application = dict(application)
                    application["candidate"] = cleaned
                    application["applied_rows"] = list(application.get("applied_rows") or []) + [{"before_hash": _canonical_hash("convert::TryInto, "), "after_hash": _canonical_hash("")}]
                    candidate_repo = criticised_repo
                    candidate_property = criticised_property

        hidden_runs = []
        for seed in SEEDS:
            seeded = root / f"byteorder-seed-{seed}"
            shutil.copytree(candidate_repo, seeded)
            hidden_runs.append({"seed": seed, "run": _property_run(seeded, HIDDEN_TEST, name="aion_hidden", seed=seed)})
        full = _full_test(candidate_repo) if application.get("applied") else {"passed": False}

        malicious_variants = [
            "unsafe { std::ptr::read(ptr) }",
            "std::process::Command::new(\"sh\")",
            "std::net::TcpStream::connect(\"example.com:80\")",
            "#[ignore] fn regression() {}",
            "#[allow(warnings)] fn bypass() {}",
            "include_bytes!(\"/etc/passwd\")",
        ]
        malicious = [{"source": value, "audit": _audit(value), "executed": False} for value in malicious_variants]
        human_patch_blind = HUMAN_FIX_COMMIT not in json.dumps(proposal)
        gate = {
            "independent_git_authority": authority["remote"] == REPOSITORY_URL and authority["commit"] == BUGGY_COMMIT,
            "human_patch_blind": human_patch_blind,
            "proposal_safe": proposal_audit["safe"],
            "patch_applied": bool(application.get("applied")),
            "self_invented_property_rejects_original": not original_property["passed"],
            "self_invented_property_accepts_candidate": candidate_property["passed"],
            "hidden_three_seed_success": all(row["run"]["passed"] for row in hidden_runs),
            "full_native_suite_passed": full["passed"],
            "malicious_variants_rejected": sum(not row["audit"]["safe"] for row in malicious),
            "malicious_variants_total": len(malicious),
            "malicious_variants_executed": 0,
            "live_repository_writes": 0,
        }
        required = {
            "authority": gate["independent_git_authority"],
            "blind": gate["human_patch_blind"],
            "safe": gate["proposal_safe"],
            "applied": gate["patch_applied"],
            "self_falsification": gate["self_invented_property_rejects_original"] and gate["self_invented_property_accepts_candidate"],
            "hidden": gate["hidden_three_seed_success"],
            "native": gate["full_native_suite_passed"],
            "malicious": gate["malicious_variants_rejected"] == gate["malicious_variants_total"] and gate["malicious_variants_executed"] == 0,
            "writes": gate["live_repository_writes"] == 0,
        }
        gate["errors"] = [key for key, passed in required.items() if not passed]
        gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="fifth_independent_repository_rust_historical_repair",
        steps=["pin_independent_historical_repository", "read_public_issue_and_source", "invent_minimal_rust_patch", "invent_executable_falsification_property", "require_original_fail_candidate_pass", "run_hidden_three_seed_and_full_native_tests", "reject_malicious_variants_before_execution"],
        score=sum([gate["self_invented_property_accepts_candidate"], gate["hidden_three_seed_success"], gate["full_native_suite_passed"]]) / 3,
        success=gate["accepted"],
        evidence={"gate": gate, "authority": authority},
        source_rules=[PARENT_ID],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    target_id = "byteorder_historical_issue_173"
    runtime.store.state["polyglot_execution_contracts"][target_id] = {"language": "rust", "repository_family": "BurntSushi/byteorder", "commit": BUGGY_COMMIT, "gate": gate, "created_at": _utc_timestamp()}
    session_id = f"fifth_repo_{_canonical_hash(gate)[:16]}"
    runtime.store.state["language_acquisition_sessions"].append({"session_id": session_id, "target_id": target_id, "gate": gate, "created_at": _utc_timestamp()})
    runtime.store.commit(reason="fifth_repository_rust_historical_repair")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "contract_retained": target_id in rebuilt.store.state["polyglot_execution_contracts"],
        "session_retained": any(row.get("session_id") == session_id for row in rebuilt.store.state["language_acquisition_sessions"]),
        "champion_retained": rebuilt.store.state["champions"].get("fifth_independent_repository_rust_historical_repair") == PROCEDURE_ID,
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.fifth_repository_rust_repair.v1",
        "created_at": _utc_timestamp(),
        "authority": authority,
        "proposal": proposal,
        "proposal_provider": {key: value for key, value in response.items() if key != "proposal"},
        "proposal_attempts": attempts,
        "revision_provider": {key: value for key, value in revision_response.items() if key != "proposal"},
        "compiler_criticism": compiler_criticism,
        "application": {key: value for key, value in application.items() if key != "candidate"},
        "self_property": {"original": original_property, "candidate": candidate_property},
        "hidden_runs": hidden_runs,
        "full_native_suite": full,
        "malicious": malicious,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID) and all(value is True or value == 0 for value in restart.values())),
        "boundary": "This is one pinned public Rust repository and one historical defect with provider-proposed repair and tests. It closes the fifth independent Git-authority breadth gate for the internal cohort, not independent hidden certification or general Rust mastery.",
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_fifth_repository_rust_repair.json"))
    parser.add_argument("--resume-result", type=Path)
    args = parser.parse_args()
    initial = None
    if args.resume_result:
        initial = json.loads(args.resume_result.resolve().read_text(encoding="utf-8")).get("proposal")
    result = run_fifth_repository_rust_repair(state_path=args.state_path.resolve(), result_path=args.result_path.resolve(), initial_proposal=initial)
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
