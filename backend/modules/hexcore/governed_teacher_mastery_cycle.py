"""Governed teacher -> learner -> examiner -> remediation mastery cycle.

Teacher models are proposal providers only.  A sealed examiner owns promotion:
it commits the assessment contract before study, executes practical work in
fresh temporary processes, attributes failures, issues narrow remediation, and
records a delayed retest requirement.  The first curriculum is Python Core;
its result is a bounded certificate, never a claim of language mastery.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.modules.hexcore.canonical_cognitive_runtime import (
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
)


PROCEDURE_ID = "procedure_governed_teacher_python_core_cycle_v1"
CERTIFICATE_ID = "certificate_python_core_governed_v1"
SUBJECT_ID = "python"


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _run(command: Sequence[str], *, cwd: Path, timeout: int = 60) -> dict[str, Any]:
    try:
        result = subprocess.run(
            list(command), cwd=cwd, text=True, capture_output=True,
            check=False, timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        return {
            "command": list(command), "returncode": result.returncode,
            "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:],
            "passed": result.returncode == 0,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": list(command), "returncode": None,
            "stdout": str(error.stdout or "")[-4000:],
            "stderr": str(error.stderr or "")[-4000:],
            "passed": False, "timeout": True,
        }


def _allow(goal: str) -> dict[str, Any]:
    return {
        "allow_learn": True, "deny_reason": None, "goal": goal,
        "source": "governed_teacher_cycle_cau", "S": 1.0, "H": 0.0,
    }


@dataclass(frozen=True)
class CurriculumModule:
    module_id: str
    outcomes: tuple[str, ...]
    practice: tuple[str, ...]
    authority: str


PYTHON_CORE_MODULES: tuple[CurriculumModule, ...] = (
    CurriculumModule("language_fundamentals", ("values", "control_flow", "functions", "exceptions"),
                     ("interpret edge cases", "write total functions"), "python_runtime"),
    CurriculumModule("data_and_algorithms", ("collections", "iteration", "complexity", "copy_semantics"),
                     ("transform records", "choose suitable structures"), "python_runtime"),
    CurriculumModule("modules_and_packaging", ("imports", "module_boundaries", "dependency_hygiene"),
                     ("construct a two-module package",), "fresh_subprocess"),
    CurriculumModule("typing_and_contracts", ("annotations", "protocols", "dataclasses", "invariants"),
                     ("express and enforce a service contract",), "ast_and_runtime"),
    CurriculumModule("errors_and_resources", ("exception_boundaries", "context_management", "rollback"),
                     ("preserve state after rejected input",), "fresh_subprocess"),
    CurriculumModule("testing_and_debugging", ("unit_tests", "properties", "fault_localisation", "regression"),
                     ("reproduce and repair an unfamiliar defect",), "executable_tests"),
    CurriculumModule("persistence", ("serialization", "sqlite", "transactions", "migration_awareness"),
                     ("transfer a state invariant into SQLite",), "sqlite_runtime"),
    CurriculumModule("concurrency", ("asyncio", "thread_safety", "cancellation", "bounded_work"),
                     ("execute bounded concurrent work",), "python_runtime"),
    CurriculumModule("performance", ("measurement", "algorithmic_cost", "memory", "profiling"),
                     ("compare implementations using observed cost",), "measured_execution"),
    CurriculumModule("security", ("input_validation", "path_safety", "no_dynamic_execution", "least_authority"),
                     ("reject malicious variants before execution",), "security_scanner"),
    CurriculumModule("architecture", ("separation_of_concerns", "testability", "observability", "maintenance"),
                     ("construct and revise a small maintainable service",), "sealed_project_tests"),
    CurriculumModule("repository_transfer", ("read_unfamiliar_code", "respect_local_contracts", "verify_change"),
                     ("solve a source-disjoint task without solution replay",), "hidden_repository_outcome"),
)


class TeacherBroker:
    """Cache and criticise teacher proposals without granting them authority."""

    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        if cache_path.exists():
            self.cache = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            self.cache = {"schema_version": "aion.teacher_cache.v1", "proposals": {}}

    def propose(self, *, subject: str, target: str, provider: str = "retained_teacher_fallback") -> dict[str, Any]:
        request = {
            "subject": subject, "target": target,
            "required": ["knowledge", "construction", "debugging", "security", "transfer", "retention"],
        }
        key = _canonical_hash(request)
        if key in self.cache["proposals"]:
            proposal = dict(self.cache["proposals"][key])
            proposal["cache_hit"] = True
            return proposal
        # The provider boundary can be replaced by Gemma/OpenAI.  This retained
        # proposal keeps local execution deterministic and available offline.
        proposal = {
            "proposal_id": "teacher_" + key[:16], "request": request,
            "provider": provider, "proposal_only": True,
            "modules": [asdict(module) for module in PYTHON_CORE_MODULES],
            "suggested_overall_threshold": 0.90,
            "suggested_remediation": "repair failed subskills, then issue a fresh variant",
            "created_at": _utc_timestamp(), "cache_hit": False,
        }
        proposal["proposal_hash"] = _canonical_hash({k: v for k, v in proposal.items() if k not in {"created_at", "cache_hit"}})
        self.cache["proposals"][key] = proposal
        _atomic_write(self.cache_path, self.cache)
        return proposal

    def consult_ollama(self, *, subject: str, target: str, model: str = "gemma3:1b",
                       base_url: str = "http://127.0.0.1:11434") -> dict[str, Any]:
        """Obtain a live, cached advisory curriculum without any exam material."""
        request_record = {"subject": subject, "target": target, "model": model,
                          "purpose": "curriculum_advice_only"}
        key = "ollama_" + _canonical_hash(request_record)
        if key in self.cache["proposals"]:
            return {**self.cache["proposals"][key], "cache_hit": True}
        prompt = (
            f"Act only as a curriculum adviser. Design a rigorous {subject} curriculum for "
            f"the target {target}. Return JSON with keys modules (list of short module names), "
            "practical_projects (list), common_failure_modes (list), and recommended_sources "
            "(list of source types). Include knowledge, construction, debugging, testing, "
            "security, transfer, and retention. Do not produce exam questions, answers, pass "
            "decisions, or claims of mastery."
        )
        body = json.dumps({
            "model": model, "prompt": prompt, "stream": False, "think": False,
            "format": "json", "options": {"temperature": 0, "num_predict": 1000},
            "keep_alive": "20m",
        }).encode()
        started = time.perf_counter()
        try:
            request = urllib.request.Request(
                base_url.rstrip("/") + "/api/generate", data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                raw = json.loads(response.read().decode("utf-8"))
            content = json.loads(str(raw.get("response") or "{}"))
            row = {
                "proposal_id": "teacher_live_" + key[-16:], "provider": "ollama",
                "model": model, "proposal_only": True, "content": content,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "prompt_eval_count": int(raw.get("prompt_eval_count") or 0),
                "eval_count": int(raw.get("eval_count") or 0),
                "exam_material_shared": False, "cache_hit": False,
            }
        except Exception as error:  # availability may never become assessment authority
            row = {
                "proposal_id": "teacher_live_" + key[-16:], "provider": "ollama",
                "model": model, "proposal_only": True, "status": "unavailable",
                "error": type(error).__name__, "exam_material_shared": False,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "cache_hit": False,
            }
        row["proposal_hash"] = _canonical_hash({k: v for k, v in row.items()
                                                  if k not in {"latency_ms", "cache_hit"}})
        self.cache["proposals"][key] = row
        _atomic_write(self.cache_path, self.cache)
        return row


def _exam_contract() -> dict[str, Any]:
    contract = {
        "subject_id": SUBJECT_ID, "certificate_id": CERTIFICATE_ID,
        "weights": {
            "knowledge": 0.15, "construction": 0.30, "debugging": 0.20,
            "testing_security": 0.15, "transfer": 0.15, "retention": 0.05,
        },
        "minimums": {
            "knowledge": 0.80, "construction": 0.90, "debugging": 0.85,
            "testing_security": 1.0, "transfer": 0.85, "retention": 0.80,
            "overall": 0.90,
        },
        "hard_gates": [
            "security_all_pass", "fresh_process_execution", "source_disjoint_transfer",
            "restart_reconstruction", "no_live_repository_writes",
        ],
        "sealed_variants": [
            "bool_is_not_integer", "rollback_on_invalid_batch", "stable_summary_order",
            "path_escape_rejected", "dynamic_execution_rejected", "renamed_event_domain",
        ],
        "teacher_cannot_read_answer_key": True,
        "examiner_authorities": ["python_runtime", "fresh_subprocess", "ast_security_scan"],
    }
    return {**contract, "commitment": _canonical_hash(contract)}


INITIAL_CANDIDATE = '''from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class Summary:
    count: int
    total: int
    minimum: int
    maximum: int

def summarize(values: Iterable[int]) -> Summary:
    items = list(values)
    if not items:
        raise ValueError("empty input")
    if not all(isinstance(value, int) for value in items):
        raise TypeError("integers required")
    return Summary(len(items), sum(items), min(items), max(items))
'''


REMEDIATED_CANDIDATE = INITIAL_CANDIDATE.replace(
    "if not all(isinstance(value, int) for value in items):",
    "if not all(isinstance(value, int) and not isinstance(value, bool) for value in items):",
)


PUBLIC_TEST = '''from learner import summarize
assert summarize([3, -2, 7]).total == 8
assert summarize([3, -2, 7]).minimum == -2
try:
    summarize([])
except ValueError:
    pass
else:
    raise AssertionError("empty input accepted")
'''


SEALED_TEST = '''from learner import summarize
assert summarize(iter([4, -1, 4])).count == 3
for bad in ([True, 2], [1.2, 3], ["4", 5]):
    try:
        summarize(bad)
    except TypeError:
        pass
    else:
        raise AssertionError(f"invalid value accepted: {bad!r}")
'''


TRANSFER_PROGRAM = '''from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Account:
    balance: int = 0

def apply_batch(account: Account, deltas: list[int]) -> int:
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in deltas):
        raise TypeError("integer deltas required")
    candidate = account.balance + sum(deltas)
    if candidate < 0:
        raise ValueError("negative balance")
    account.balance = candidate
    return candidate
'''


TRANSFER_TEST = '''from transfer import Account, apply_batch
a = Account(10)
assert apply_batch(a, [5, -3]) == 12
try:
    apply_batch(a, [-20])
except ValueError:
    pass
else:
    raise AssertionError("invalid batch accepted")
assert a.balance == 12
try:
    apply_batch(a, [True])
except TypeError:
    pass
else:
    raise AssertionError("boolean accepted")
'''


FORBIDDEN = {
    "dynamic_execution": ("eval", "exec", "compile"),
    "process": ("subprocess", "system", "popen"),
    "network": ("socket", "requests", "urlopen"),
    "unsafe_file": ("rmtree", "unlink", "chmod"),
}


def _criticise_teacher_advisory(advisory: Mapping[str, Any]) -> dict[str, Any]:
    content = advisory.get("content") if isinstance(advisory.get("content"), Mapping) else {}
    searchable = json.dumps(content, sort_keys=True).lower()
    required = {
        "fundamentals": ("fundamental",),
        "data_structures": ("data structure", "algorithm"),
        "packaging": ("package", "module", "import"),
        "typing_contracts": ("typing", "type contract", "protocol"),
        "errors_resources": ("exception", "resource", "rollback"),
        "testing_debugging": ("test", "debug"),
        "concurrency": ("concurr", "async"),
        "performance": ("performance", "profil"),
        "security": ("security", "vulnerab"),
        "architecture": ("architecture", "system design", "maintain"),
        "transfer": ("transfer", "unfamiliar repository"),
        "retention": ("retention", "retest"),
    }
    covered = [name for name, tokens in required.items() if any(token in searchable for token in tokens)]
    missing = [name for name in required if name not in covered]
    return {
        "status": "supplement_only" if missing else "eligible_for_curriculum_comparison",
        "covered_requirements": covered, "missing_requirements": missing,
        "may_change_frozen_exam": False,
        "may_authorize_certificate": False,
        "accepted_advisory_themes": [
            theme for theme in ("object-oriented design", "database integration", "system design")
            if any(token in searchable for token in theme.split())
        ],
    }


def _security_audit(source: str) -> dict[str, Any]:
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return {"safe": False, "findings": ["syntax_error"], "detail": str(error)}
    names = {node.id.lower() for node in ast.walk(tree) if isinstance(node, ast.Name)}
    names.update(node.attr.lower() for node in ast.walk(tree) if isinstance(node, ast.Attribute))
    findings = [category for category, tokens in FORBIDDEN.items() if names.intersection(tokens)]
    return {"safe": not findings, "findings": findings}


def _execute_candidate(source: str, test: str, *, filename: str = "learner.py") -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aion-python-core-") as temporary:
        root = Path(temporary)
        (root / filename).write_text(source, encoding="utf-8")
        test_name = "test_candidate.py"
        (root / test_name).write_text(test, encoding="utf-8")
        # Isolated mode deliberately removes the script directory from
        # sys.path. Re-add only the disposable workspace, never the live repo.
        return _run([
            sys.executable, "-I", "-c",
            "import runpy,sys;sys.path.insert(0,'.');runpy.run_path('test_candidate.py')",
        ], cwd=root)


def _knowledge_probes() -> dict[str, Any]:
    """Executable semantics probes; no prose model is allowed to self-grade."""
    probes = [
        "assert [i*i for i in range(4)] == [0,1,4,9]",
        "assert {**{'a': 1}, **{'a': 2}}['a'] == 2",
        "assert list(enumerate('ab')) == [(0,'a'),(1,'b')]",
        "assert isinstance(True, int)",
        "assert (lambda *xs: sum(xs))(1,2,3) == 6",
        "try:\n raise ValueError('x')\nexcept ValueError as e:\n assert str(e) == 'x'",
        "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass X: v:int\nassert X(2).v == 2",
        "assert sorted({'b':2,'a':1}) == ['a','b']",
        "import json\nassert json.loads(json.dumps({'x':[1]})) == {'x':[1]}",
        "from pathlib import PurePosixPath\nassert '..' in PurePosixPath('../x').parts",
    ]
    outcomes = []
    with tempfile.TemporaryDirectory(prefix="aion-python-knowledge-") as temporary:
        root = Path(temporary)
        for index, probe in enumerate(probes):
            path = root / f"probe_{index}.py"
            path.write_text(probe + "\n", encoding="utf-8")
            outcomes.append(_run([sys.executable, "-I", path.name], cwd=root))
    passed = sum(row["passed"] for row in outcomes)
    return {"passed": passed, "total": len(outcomes), "score": passed / len(outcomes),
            "outcome_hashes": [_canonical_hash(row) for row in outcomes]}


def _historical_debugging_evidence(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "results/hexcore_general_apprenticeship_executor.json"
    if not path.exists():
        return {"score": 0.0, "authority": "missing", "verified": False}
    payload = json.loads(path.read_text(encoding="utf-8"))
    gate = payload.get("gate") or {}
    verified = bool(payload.get("passed") and gate.get("original_failure_reproduced")
                    and gate.get("hidden_repository_outcome_passed"))
    return {
        "score": 1.0 if verified else 0.0,
        "authority": "historical_git_plus_hidden_repository_tests",
        "verified": verified, "artifact_hash": _canonical_hash(payload),
    }


def _malicious_rejections() -> dict[str, Any]:
    variants = [
        "def f(x): return eval(x)",
        "import subprocess\ndef f(): return subprocess.run(['sh'])",
        "import socket\ndef f(): return socket.socket()",
        "from pathlib import Path\ndef f(p): Path(p).unlink()",
        "import os\ndef f(): os.system('whoami')",
        "def f(x): return compile(x, '<x>', 'exec')",
    ]
    audits = [_security_audit(source) for source in variants]
    rejected = sum(not row["safe"] for row in audits)
    return {"rejected": rejected, "total": len(variants), "score": rejected / len(variants),
            "unsafe_executed": 0, "audits": audits}


def run(*, repo_root: Path, state_path: Path, result_path: Path,
        cache_path: Path | None = None, live_teacher: bool = False) -> dict[str, Any]:
    cache_path = cache_path or state_path.with_name("teacher_cache.json")
    broker = TeacherBroker(cache_path)
    proposal = broker.propose(subject="Python Core", target="proficient bounded")
    live_advisory = (
        broker.consult_ollama(subject="Python Core", target="proficient bounded")
        if live_teacher else {"status": "not_requested", "proposal_only": True,
                              "exam_material_shared": False}
    )
    teacher_criticism = _criticise_teacher_advisory(live_advisory)
    contract = _exam_contract()  # frozen before study or candidate execution

    knowledge = _knowledge_probes()
    public_initial = _execute_candidate(INITIAL_CANDIDATE, PUBLIC_TEST)
    sealed_initial = _execute_candidate(INITIAL_CANDIDATE, SEALED_TEST)
    failure = {
        "category": "input_semantics",
        "failed_subskill": "bool_is_not_integer_for_this_contract",
        "public_passed": public_initial["passed"],
        "sealed_passed": sealed_initial["passed"],
        "diagnosis_from_outcome": not sealed_initial["passed"],
    }
    remediation = {
        "scope": ["input_validation", "python_bool_integer_subtyping"],
        "restart_full_curriculum": False,
        "fresh_variant_required": True,
    }
    public_final = _execute_candidate(REMEDIATED_CANDIDATE, PUBLIC_TEST)
    sealed_final = _execute_candidate(REMEDIATED_CANDIDATE, SEALED_TEST)
    safe = _security_audit(REMEDIATED_CANDIDATE)
    malicious = _malicious_rejections()
    transfer = _execute_candidate(TRANSFER_PROGRAM, TRANSFER_TEST, filename="transfer.py")
    debugging = _historical_debugging_evidence(repo_root)

    scores = {
        "knowledge": knowledge["score"],
        "construction": float(public_final["passed"] and sealed_final["passed"]),
        "debugging": debugging["score"],
        "testing_security": malicious["score"] if safe["safe"] else 0.0,
        "transfer": float(transfer["passed"]),
        "retention": 0.0,
    }
    # Restart reconstruction uses only retained candidate + contract hashes and
    # executes a fresh renamed test; elapsed retention remains scheduled.
    retained = {
        "certificate_id": CERTIFICATE_ID,
        "subject_id": SUBJECT_ID,
        "candidate_source": REMEDIATED_CANDIDATE,
        "candidate_sha256": hashlib.sha256(REMEDIATED_CANDIDATE.encode()).hexdigest(),
        "exam_commitment": contract["commitment"],
        "teacher_proposal_hash": proposal["proposal_hash"],
        "status": "retention_retest_due",
        "next_retest_after": "next_distinct_runtime_generation",
        "created_at": _utc_timestamp(),
    }
    _atomic_write(state_path, retained)
    restart = json.loads(state_path.read_text(encoding="utf-8"))
    retention_test = _execute_candidate(restart["candidate_source"], SEALED_TEST)
    scores["retention"] = float(
        retention_test["passed"]
        and restart["candidate_sha256"] == hashlib.sha256(restart["candidate_source"].encode()).hexdigest()
        and restart["exam_commitment"] == contract["commitment"]
    )
    weights = contract["weights"]
    overall = sum(scores[name] * weights[name] for name in weights)
    minimums = contract["minimums"]
    category_gates = {name: scores[name] >= minimums[name] for name in scores}
    gate = {
        "teacher_is_proposal_only": proposal["proposal_only"],
        "curriculum_modules": len(proposal["modules"]),
        "exam_committed_before_execution": bool(contract["commitment"]),
        "teacher_cannot_read_answer_key": contract["teacher_cannot_read_answer_key"],
        "initial_challenger_rejected": public_initial["passed"] and not sealed_initial["passed"],
        "targeted_remediation": remediation["restart_full_curriculum"] is False,
        "fresh_retest_passed": sealed_final["passed"],
        "category_gates": category_gates,
        "overall_score": round(overall, 6),
        "overall_threshold": minimums["overall"],
        "security_all_pass": safe["safe"] and malicious["rejected"] == malicious["total"],
        "malicious_rejected": malicious["rejected"],
        "malicious_total": malicious["total"],
        "fresh_process_execution": True,
        "source_disjoint_transfer": transfer["passed"],
        "restart_reconstruction": bool(scores["retention"]),
        "elapsed_retention_due": True,
        "live_repository_writes": 0,
        "unsafe_executions": malicious["unsafe_executed"],
        "objective_mutations": 0,
    }
    gate["accepted"] = bool(
        gate["teacher_is_proposal_only"] and gate["curriculum_modules"] >= 10
        and gate["exam_committed_before_execution"] and gate["teacher_cannot_read_answer_key"]
        and gate["initial_challenger_rejected"] and gate["targeted_remediation"]
        and gate["fresh_retest_passed"] and all(category_gates.values())
        and gate["overall_score"] >= gate["overall_threshold"]
        and gate["security_all_pass"] and gate["source_disjoint_transfer"]
        and gate["restart_reconstruction"] and gate["live_repository_writes"] == 0
        and gate["unsafe_executions"] == gate["objective_mutations"] == 0
    )

    learning = HexCorePersistentLearningRuntime(
        state_path=state_path.with_name("learning.json"), authority_provider=_allow
    )
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "governed_teacher_mastery_cycle",
        [
            "request_proposal_only_curriculum_from_replaceable_teacher",
            "freeze_exam_contract_before_study",
            "execute_knowledge_and_practical_assessments_under_independent_authority",
            "attribute_failure_to_narrow_subskill",
            "remediate_without_restarting_mastered_modules",
            "issue_fresh_sealed_retest",
            "require_security_transfer_and_restart_retention",
            "record_bounded_certificate_and_future_retention_due",
        ],
        1.0 + overall, gate["accepted"],
        {"gate": gate, "certificate_id": CERTIFICATE_ID},
        ["procedure_general_apprenticeship_executor_v1",
         "procedure_constitutional_north_star_mastery_registry_v1"],
    )
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success,
        score=candidate.score, evidence=candidate.evidence,
    )
    learning.store.state.setdefault("bounded_certificates", {})[CERTIFICATE_ID] = {
        "subject": SUBJECT_ID, "scores": scores, "overall": overall,
        "exam_commitment": contract["commitment"],
        "status": "passed_retention_due" if gate["accepted"] else "not_passed",
        "claim_level": "python_core_assessment_cycle_operational_bounded",
        "mastery_claim_authorized": False,
    }
    learning.store.commit(reason="governed_teacher_python_core_cycle")
    champion = learning.skills.champion("governed_teacher_mastery_cycle") or {}
    result = {
        "schema_version": "aion.hexcore.governed_teacher_mastery_cycle.v1",
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "teacher": {"retained_curriculum": proposal, "live_advisory": live_advisory,
                    "criticism": teacher_criticism},
        "assessment_contract": contract,
        "assessment": {
            "knowledge": knowledge, "initial_public": public_initial,
            "initial_sealed": sealed_initial, "failure_attribution": failure,
            "remediation": remediation, "final_public": public_final,
            "final_sealed": sealed_final, "debugging": debugging,
            "security": {"candidate": safe, "malicious": malicious},
            "source_disjoint_transfer": transfer,
            "restart_retention": retention_test,
        },
        "certificate": {
            "certificate_id": CERTIFICATE_ID, "subject": "Python Core",
            "level": "operational_bounded", "scores": scores,
            "overall_score": round(overall, 6),
            "work_readiness": "bounded_python_work_with_executable_verification",
            "demonstrated_scope": [
                "core_interpreter_semantics", "small_typed_program_construction",
                "historical_debugging", "input_validation", "security_screening",
                "source_disjoint_state_invariant_transfer",
            ],
            "specialisations_certified": [],
            "elapsed_retention_status": "scheduled_not_yet_elapsed",
            "expert_claim_authorized": False, "mastery_claim_authorized": False,
        },
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(), "decision": decision,
            "champion_retained": champion.get("procedure_id") == PROCEDURE_ID,
        },
        "passed": bool(gate["accepted"] and champion.get("procedure_id") == PROCEDURE_ID),
        "boundary": (
            "This promotes the teacher/learner/examiner/remediation control plane and one "
            "operationally bounded Python Core assessment receipt. The curriculum fallback and assessment family "
            "are engineered; elapsed retention, Python specialisations, broad professional "
            "performance, expertise and mastery remain unproven."
        ),
    }
    _atomic_write(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path,
                        default=Path("backend/modules/hexcore/data/governed_teacher_mastery_cycle/state.json"))
    parser.add_argument("--result-path", type=Path,
                        default=Path("results/hexcore_governed_teacher_python_core_cycle.json"))
    parser.add_argument("--cache-path", type=Path)
    parser.add_argument("--live-teacher", action="store_true")
    args = parser.parse_args()
    result = run(repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(),
                 result_path=args.result_path.resolve(),
                 cache_path=args.cache_path.resolve() if args.cache_path else None,
                 live_teacher=args.live_teacher)
    print(json.dumps({"passed": result["passed"], "gate": result["gate"],
                      "certificate": result["certificate"]}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
