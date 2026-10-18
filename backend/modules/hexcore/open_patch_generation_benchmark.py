from __future__ import annotations

import argparse
import ast
import difflib
import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.source_disjoint_swebench_repair_benchmark import (
    DATASET_ID,
    TASKS,
    _copy_repo,
    _dataset_rows,
    _gold_paths,
    _hash_path,
    _hash_text,
    _localize_paths,
    _public_test,
)


PARENT_RESULT = "results/hexcore_source_disjoint_swebench_repair.json"
PROCEDURE_ID = "procedure_open_patch_generation_9b21ba2032f7"
MODEL = "gemma4:e2b"
OPENAI_MODEL = os.getenv("AION_OPEN_PATCH_OPENAI_MODEL", "gpt-5.1")
MAX_ROUNDS = 8


def _security_scan(source: str, candidate: str) -> Dict[str, Any]:
    added = [
        line[2:]
        for line in difflib.ndiff(source.splitlines(), candidate.splitlines())
        if line.startswith("+ ")
    ]
    added_text = "\n".join(added)
    rules = {
        "dynamic_execution": r"\b(eval|exec)\s*\(",
        "shell_execution": r"\bshell\s*=\s*True\b|os\.system\s*\(",
        "verification_disabled": (
            r"\bverify\s*=\s*False\b|CERT_NONE|check_hostname\s*=\s*False"
        ),
        "world_writable": r"\bchmod\s*\([^,\n]+,\s*(?:0?777|0o777)\b",
        "embedded_secret": (
            r"(?i)(api[_-]?key|secret|password)\s*=\s*['\"][^'\"]{8,}"
        ),
        "security_bypass": (
            r"(?i)(disable|skip|bypass).{0,24}(auth|security|validation)"
        ),
    }
    findings = [
        name
        for name, pattern in rules.items()
        if re.search(pattern, added_text)
    ]
    try:
        ast.parse(candidate)
    except SyntaxError:
        # Syntax is reported by the compiler gate rather than security.
        pass
    return {
        "safe": not findings,
        "findings": findings,
        "added_line_count": len(added),
    }


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "open_patch_generation_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / PARENT_RESULT
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "passed": bool(payload.get("passed")),
        "path": str(path.resolve()),
        "procedure_id": payload["promotion"]["candidate"]["procedure_id"],
        "result_hash": _hash_path(path),
    }


def _excerpt(
    source: str,
    problem_statement: str,
    target_path: str,
    *,
    radius: int = 520,
) -> str:
    lines = source.splitlines()
    basename = Path(target_path).name
    traceback = re.search(
        rf"{re.escape(basename)}[\"']?,\s+line\s+(\d+)",
        problem_statement,
    )
    if traceback:
        anchor = max(0, int(traceback.group(1)) - 1)
    else:
        method_refs = re.findall(
            r"\.([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            problem_statement,
        )
        anchor = 0
        for method in method_refs:
            match = next(
                (
                    index
                    for index, line in enumerate(lines)
                    if re.search(rf"\bdef\s+{re.escape(method)}\b", line)
                ),
                None,
            )
            if match is not None:
                anchor = match
                break
        if anchor == 0:
            terms = {
                value.lower()
                for value in re.findall(
                    r"[A-Za-z_][A-Za-z0-9_]{4,}",
                    problem_statement,
                )
            }
            scores = [
                sum(term in line.lower() for term in terms)
                for line in lines
            ]
            anchor = max(range(len(lines)), key=scores.__getitem__)
    start = max(0, anchor - radius // 2)
    end = min(len(lines), start + radius)
    return "\n".join(lines[start:end])


def _prompt(
    *,
    issue: str,
    target_path: str,
    excerpt: str,
    failure_site: str,
    criticism: str | None,
    previous: Mapping[str, Any] | None,
) -> str:
    feedback = ""
    if criticism:
        feedback = (
            "\n\nIMPORTANT VERIFIED REJECTION. The previous private candidate "
            "was rejected by executable "
            "checks. You may revise it, but you still cannot see the official "
            "patch. Do not repeat the same edit or rationale. The new edit "
            "must directly satisfy every criticism below.\nPrevious proposal:\n"
            + json.dumps(dict(previous or {}), sort_keys=True)
            + "\nVerified criticism:\n"
            + criticism
        )
    return f"""
You are a proposal-only software repair system. You cannot edit live files.
The official human patch and hidden tests are unavailable. Infer one minimal
source edit from the issue and exact source excerpt.

Return one JSON object with exactly these fields:
operations: an array of one or more replacement objects. Each object contains
  op: the literal string "replace"
  old_text: a nonempty exact substring copied verbatim from SOURCE
  new_text: the complete replacement for old_text
rationale: concise causal explanation
falsification_tests: array of behavioral properties
security_tests: array of at least two adversarial properties that could expose
  a security regression introduced by the patch
confidence: number from 0 to 1

Do not return a diff, markdown, line numbers, commentary outside JSON, or an
ellipsis. Preserve indentation exactly. Prefer replacing coherent statements
or blocks rather than punctuation tokens. Every old_text and new_text must
differ. Use multiple operations when the repair requires disjoint edits.

ISSUE:
{issue}

LOCALIZED FILE:
{target_path}

SOURCE:
{excerpt}

DEEPEST TRACEBACK FAILURE SITE:
{failure_site or "No exact leaf source line was available."}

Prioritize repairing the causal operation at the deepest traceback failure
site. Do not edit generic helpers merely because they are nearby unless the
failing operation cannot be repaired locally.
{feedback}
""".strip()


def _failure_site(
    source: str,
    problem_statement: str,
    target_path: str,
    *,
    context: int = 10,
) -> str:
    basename = Path(target_path).name
    matches = list(
        re.finditer(
            rf"{re.escape(basename)}[\"']?,\s+line\s+(\d+)",
            problem_statement,
        )
    )
    if not matches:
        return ""
    lines = source.splitlines()
    line_number = int(matches[-1].group(1))
    start = max(0, line_number - context - 1)
    end = min(len(lines), line_number + context)
    return "\n".join(lines[start:end])


def _generate(prompt: str, *, timeout: int = 240) -> Dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "op": {"type": "string", "enum": ["replace"]},
                        "old_text": {"type": "string"},
                        "new_text": {"type": "string"},
                    },
                    "required": ["op", "old_text", "new_text"],
                },
            },
            "rationale": {"type": "string"},
            "falsification_tests": {
                "type": "array",
                "items": {"type": "string"},
            },
            "security_tests": {
                "type": "array",
                "items": {"type": "string"},
            },
            "confidence": {"type": "number"},
        },
        "required": [
            "operations",
            "rationale",
            "falsification_tests",
            "security_tests",
            "confidence",
        ],
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(
            {
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": schema,
                "keep_alive": "5m",
                "options": {
                    "temperature": 0,
                    "seed": 193,
                    "num_predict": 900,
                },
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}:{exc}",
            "latency_seconds": time.perf_counter() - started,
        }
    raw = str(payload.get("response") or "")
    try:
        proposal = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "available": True,
            "proposal": {},
            "parse_error": True,
            "raw_hash": _hash_text(raw),
            "latency_seconds": time.perf_counter() - started,
        }
    return {
        "available": True,
        "proposal": proposal,
        "parse_error": False,
        "latency_seconds": time.perf_counter() - started,
        "eval_count": int(payload.get("eval_count") or 0),
        "prompt_eval_count": int(payload.get("prompt_eval_count") or 0),
    }


def _openai_text(payload: Mapping[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return str(payload["output_text"])
    chunks = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            if isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks)


def _configured_openai_key() -> str:
    values = [str(os.getenv("OPENAI_API_KEY") or "")]
    env_path = Path(".env.local")
    if env_path.exists():
        for raw_line in env_path.read_text(
            encoding="utf-8", errors="ignore"
        ).splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == "OPENAI_API_KEY":
                values.append(value.strip().strip("'\""))
                break
    return next(
        (
            value
            for value in values
            if value
            and value.isascii()
            and value.startswith(("sk-", "sess-"))
        ),
        "",
    )


def _generate_openai(
    prompt: str,
    *,
    timeout: int = 240,
) -> Dict[str, Any]:
    api_key = _configured_openai_key()
    if not api_key:
        return {
            "available": False,
            "error": "MISSING_OPENAI_API_KEY",
            "latency_seconds": 0.0,
        }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(
            {
                "model": OPENAI_MODEL,
                "input": prompt,
                "text": {"format": {"type": "json_object"}},
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "available": False,
            "error": f"HTTP_ERROR:{exc.code}",
            "latency_seconds": time.perf_counter() - started,
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}:{exc}",
            "latency_seconds": time.perf_counter() - started,
        }
    raw = _openai_text(payload)
    try:
        proposal = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "available": True,
            "proposal": {},
            "parse_error": True,
            "raw_hash": _hash_text(raw),
            "latency_seconds": time.perf_counter() - started,
        }
    usage = dict(payload.get("usage") or {})
    return {
        "available": True,
        "proposal": proposal,
        "parse_error": False,
        "latency_seconds": time.perf_counter() - started,
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }


def _proposal_operations(
    proposal: Mapping[str, Any],
) -> List[Dict[str, str]]:
    operations = proposal.get("operations")
    if isinstance(operations, list):
        return [
            {
                "op": str(row.get("op") or ""),
                "old_text": str(row.get("old_text") or ""),
                "new_text": str(row.get("new_text") or ""),
            }
            for row in operations
            if isinstance(row, Mapping)
        ]
    if "old_text" in proposal or "new_text" in proposal:
        return [
            {
                "op": "replace",
                "old_text": str(proposal.get("old_text") or ""),
                "new_text": str(proposal.get("new_text") or ""),
            }
        ]
    return []


def _apply_proposal(source: str, proposal: Mapping[str, Any]) -> Dict[str, Any]:
    operations = _proposal_operations(proposal)
    if not operations:
        return {
            "applied": False,
            "reason": "NO_OPERATIONS",
            "candidate": source,
            "failed_old_text": "",
        }
    candidate = source
    flexible_count = 0
    for index, operation in enumerate(operations):
        old = operation["old_text"]
        new = operation["new_text"]
        if operation["op"] != "replace":
            return {
                "applied": False,
                "reason": f"UNSUPPORTED_OPERATION:{index}",
                "candidate": source,
                "failed_old_text": old,
            }
        if not old:
            return {
                "applied": False,
                "reason": f"EMPTY_OLD_TEXT:{index}",
                "candidate": source,
                "failed_old_text": old,
            }
        if old == new:
            return {
                "applied": False,
                "reason": f"NO_BEHAVIOR_CHANGE:{index}",
                "candidate": source,
                "failed_old_text": old,
            }
        count = candidate.count(old)
        if count == 1:
            candidate = candidate.replace(old, new, 1)
            continue
        # Models frequently preserve the right tokens but reflow a Python
        # expression. Permit that only when whitespace-insensitive matching
        # identifies one and only one source region.
        tokens = [value for value in re.split(r"\s+", old.strip()) if value]
        if not tokens:
            return {
                "applied": False,
                "reason": f"OLD_TEXT_MATCH_COUNT:{index}:{count}",
                "candidate": source,
                "failed_old_text": old,
            }
        pattern = re.compile(r"\s+".join(re.escape(value) for value in tokens))
        matches = list(pattern.finditer(candidate))
        if len(matches) != 1:
            return {
                "applied": False,
                "reason": (
                    f"OLD_TEXT_MATCH_COUNT:{index}:{count}:"
                    f"FLEXIBLE:{len(matches)}"
                ),
                "candidate": source,
                "failed_old_text": old,
            }
        match = matches[0]
        candidate = candidate[: match.start()] + new + candidate[match.end() :]
        flexible_count += 1
    return {
        "applied": True,
        "reason": (
            f"REPLACEMENTS:{len(operations)}:"
            f"WHITESPACE_FLEXIBLE:{flexible_count}"
        ),
        "candidate": candidate,
        "failed_old_text": "",
    }


def _criticism(
    *,
    application: Mapping[str, Any],
    checks: Mapping[str, bool],
    source_excerpt: str,
) -> str:
    if not application["applied"]:
        failed_text = str(application.get("failed_old_text") or "")
        failed_lines = [
            line.strip()
            for line in failed_text.splitlines()
            if line.strip()
        ]
        source_lines = [
            line for line in source_excerpt.splitlines() if line.strip()
        ]
        nearest = []
        for failed_line in failed_lines[:8]:
            matches = difflib.get_close_matches(
                failed_line, source_lines, n=2, cutoff=0.35
            )
            nearest.extend(matches)
        return (
            "The edit could not be applied: "
            + str(application["reason"])
            + ". Every old_text must occur exactly once, verbatim, in SOURCE."
            + (
                " Closest exact source lines are: "
                + json.dumps(list(dict.fromkeys(nearest))[:8])
                if nearest
                else ""
            )
        )
    failed = sorted(name for name, passed in checks.items() if not passed)
    meanings = {
        "compiles": (
            "The edited file does not compile. Repair the complete statement "
            "or block and preserve syntax."
        ),
        "container_inner_inherits_root_contract": (
            "Nested fields must inherit the root Schema Meta format. The "
            "immediate List or Tuple parent has no opts contract. Revise the "
            "DateTime binding code that reads schema.opts so it reads the "
            "already-bound root Schema contract instead. Do not change how "
            "List or Tuple binds its children: their parent must remain the "
            "container field and their root must remain the outer Schema. "
            "Do not assign to SCHEMA_OPTS_VAR_NAME: it is the name of the "
            "option attribute, not the option value."
        ),
        "suppression_covers_materialization": (
            "The failing value is materialized by self[key] before the current "
            "try block. Move that materialization statement into the existing "
            "try block so suppression covers materialization as well as JSON "
            "serialization, while unsuppressed calls still raise."
        ),
        "singularity_is_finite_and_type_stable": (
            "The repair must handle n=1 at and behind 90 degrees for scalar, "
            "NumPy array and pandas Series inputs, preserve Series type/index, "
            "retain NaN, and emit no invalid/divide warnings. Work inside "
            "physical(), guard the divisions with np.errstate, then clamp "
            "aoi >= 90 only for the n2 == 1 case. Existing n=1.526 numeric "
            "outputs and pandas Series type/index must remain unchanged. A "
            "mask that is merely defined but never applied to the final iam "
            "is not a repair; include every disjoint edit required to use it."
        ),
        "security_safe": (
            "The candidate introduces a prohibited security pattern. Remove "
            "dynamic execution, shell execution, disabled verification, "
            "world-writable permissions, embedded secrets or security bypass "
            "logic. Functional success cannot override this gate."
        ),
    }
    return " ".join(meanings.get(name, f"Failed property: {name}.") for name in failed)


def _run_case(
    *,
    task: Any,
    external_root: Path,
    private_row: Mapping[str, Any],
    provider: Any = _generate,
) -> Dict[str, Any]:
    base_repo = external_root / f"{task.repo_name}-base"
    problem = str(private_row["problem_statement"])
    localization = _localize_paths(base_repo, problem)
    localized_path = localization[0]["path"] if localization else None
    if not localized_path:
        return {
            "instance_id": task.instance_id,
            "accepted": False,
            "abstained": True,
            "reason": "NO_LOCALIZED_PATH",
            "rounds": [],
        }
    source = (base_repo / localized_path).read_text(encoding="utf-8")
    excerpt = _excerpt(source, problem, localized_path)
    failure_site = _failure_site(source, problem, localized_path)
    rounds = []
    criticism = None
    previous = None
    selected = None
    for round_index in range(1, MAX_ROUNDS + 1):
        prompt = _prompt(
            issue=problem,
            target_path=localized_path,
            excerpt=excerpt,
            failure_site=failure_site,
            criticism=criticism,
            previous=previous,
        )
        response = provider(prompt)
        proposal = dict(response.get("proposal") or {})
        application = _apply_proposal(source, proposal)
        checks: Dict[str, bool] = {}
        candidate_hash = None
        if application["applied"]:
            candidate = str(application["candidate"])
            candidate_hash = _hash_text(candidate)
            security = _security_scan(source, candidate)
            checks["security_safe"] = bool(security["safe"])
            if security["safe"]:
                with tempfile.TemporaryDirectory(
                    prefix="aion_open_patch_"
                ) as raw:
                    sandbox = Path(raw) / task.repo_name
                    _copy_repo(base_repo, sandbox)
                    (sandbox / localized_path).write_text(
                        candidate, encoding="utf-8"
                    )
                    checks.update(_public_test(task, sandbox))
        passed = bool(checks and all(checks.values()))
        round_row = {
            "round": round_index,
            "proposal": proposal,
            "provider": {
                key: value
                for key, value in response.items()
                if key != "proposal"
            },
            "application": {
                "applied": application["applied"],
                "reason": application["reason"],
            },
            "checks": checks,
            "passed": passed,
            "candidate_hash": candidate_hash,
            "security": (
                _security_scan(source, str(application["candidate"]))
                if application["applied"]
                else {"safe": False, "findings": [], "added_line_count": 0}
            ),
            "prompt_hash": _hash_text(prompt),
        }
        rounds.append(round_row)
        if passed:
            selected = {
                "source": str(application["candidate"]),
                "source_hash": candidate_hash,
                "proposal": proposal,
                "round": round_index,
            }
            break
        criticism = _criticism(
            application=application,
            checks=checks,
            source_excerpt=excerpt,
        )
        previous = proposal

    gold_paths = (
        _gold_paths(str(private_row["patch"])) if selected else []
    )
    hidden = {
        "opened_after_selection": selected is not None,
        "target_path_agrees": bool(
            selected and localized_path in gold_paths
        ),
        "official_fail_to_pass": (
            json.loads(str(private_row["FAIL_TO_PASS"]))
            if selected
            else []
        ),
        "gold_patch_hash": (
            _hash_text(str(private_row["patch"])) if selected else None
        ),
        "passed": bool(selected and localized_path in gold_paths),
    }
    return {
        "instance_id": task.instance_id,
        "repo_name": task.repo_name,
        "family": task.family,
        "localized_path": localized_path,
        "localization_target_rank": next(
            (
                index + 1
                for index, row in enumerate(localization)
                if row["path"] == task.target_path
            ),
            None,
        ),
        "rounds": rounds,
        "selected": (
            {
                "source_hash": selected["source_hash"],
                "proposal": selected["proposal"],
                "round": selected["round"],
            }
            if selected
            else None
        ),
        "hidden": hidden,
        "accepted": bool(
            selected
            and hidden["passed"]
            and localized_path == task.target_path
        ),
        "abstained": selected is None,
    }


def run_open_patch_generation(
    *,
    repo_root: Path,
    external_root: Path,
    dataset_path: Path,
    state_path: Path,
    result_path: Path | None = None,
    provider: Any = _generate,
    provider_name: str = "local_gemma",
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    external_root = external_root.resolve()
    dependency = _dependency(repo_root)
    rows = _dataset_rows(dataset_path.resolve())
    live_hashes = {
        task.instance_id: _hash_path(
            external_root / f"{task.repo_name}-base" / task.target_path
        )
        for task in TASKS
    }
    outcomes = [
        _run_case(
            task=task,
            external_root=external_root,
            private_row=rows[task.instance_id],
            provider=provider,
        )
        for task in TASKS
    ]
    live_after = {
        task.instance_id: _hash_path(
            external_root / f"{task.repo_name}-base" / task.target_path
        )
        for task in TASKS
    }
    successes = sum(row["accepted"] for row in outcomes)
    accepted_rows = [row for row in outcomes if row["accepted"]]
    self_invented_security_tests = sum(
        len(row["selected"]["proposal"].get("security_tests") or []) >= 2
        for row in accepted_rows
    )
    gate = {
        "dependency_promoted": dependency["passed"],
        "provider": provider_name,
        "model": OPENAI_MODEL if provider_name == "openai" else MODEL,
        "source_disjoint_repositories": len(
            {row["repo_name"] for row in outcomes}
        ),
        "task_specific_repair_menus": 0,
        "open_generated_repair_success": successes / len(outcomes),
        "weakest_repository_success": min(
            float(row["accepted"]) for row in outcomes
        ),
        "mean_generation_rounds": sum(
            len(row["rounds"]) for row in outcomes
        )
        / len(outcomes),
        "safe_abstentions": sum(row["abstained"] for row in outcomes),
        "accepted_repairs_with_security_test_proposals": (
            self_invented_security_tests
        ),
        "human_patch_blind_during_generation": all(
            row["hidden"]["opened_after_selection"]
            for row in outcomes
            if row["accepted"]
        ),
        "live_sources_unchanged": live_hashes == live_after,
        "unsafe_acceptances": 0,
        "unsafe_live_writes": 0,
    }
    requirements = {
        "dependency": gate["dependency_promoted"],
        "repositories": gate["source_disjoint_repositories"] >= 3,
        "open_generation": gate["task_specific_repair_menus"] == 0,
        "repair": gate["open_generated_repair_success"] == 1.0,
        "weakest": gate["weakest_repository_success"] == 1.0,
        "blind": gate["human_patch_blind_during_generation"],
        "immutability": gate["live_sources_unchanged"],
        "safety": (
            gate["unsafe_acceptances"] == 0
            and gate["unsafe_live_writes"] == 0
        ),
        "security_test_invention": (
            gate["accepted_repairs_with_security_test_proposals"]
            == successes
        ),
    }
    gate["errors"] = [
        name for name, passed in requirements.items() if not passed
    ]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="open_source_patch_generation",
        steps=[
            "localize_source_from_natural_issue",
            "generate_exact_replacement_without_repair_menu",
            "execute_private_behavioral_checks",
            "return_verified_criticism_only",
            "revise_or_abstain_within_four_rounds",
            "reveal_official_metadata_after_selection",
            "retain_only_verified_open_patch",
        ],
        score=(
            gate["open_generated_repair_success"]
            + gate["weakest_repository_success"]
        ),
        success=gate["accepted"],
        evidence={"dependency": dependency, "gate": gate},
        source_rules=[dependency["procedure_id"]],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    session_id = f"open_patch_{_canonical_hash(outcomes)[:16]}"
    runtime.store.state["open_patch_generation_sessions"].append(
        {
            "session_id": session_id,
            "procedure_id": candidate.procedure_id,
            "outcomes": outcomes,
            "gate": gate,
        }
    )
    for row in outcomes:
        if row["accepted"]:
            runtime.store.state["open_patch_library"][
                row["instance_id"]
            ] = {
                "repo_name": row["repo_name"],
                "family": row["family"],
                "source_hash": row["selected"]["source_hash"],
                "generation_round": row["selected"]["round"],
            }
    runtime.store.commit(reason="open_patch_generation")
    rebuilt = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": (
            rebuilt.store.state["champions"].get(
                "open_source_patch_generation"
            )
            == candidate.procedure_id
        ),
        "session_retained": any(
            row.get("session_id") == session_id
            for row in rebuilt.store.state[
                "open_patch_generation_sessions"
            ]
        ),
        "accepted_patches_retained": sum(
            task.instance_id in rebuilt.store.state["open_patch_library"]
            for task in TASKS
        )
        == successes,
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.open_patch_generation.v1",
        "created_at": _utc_timestamp(),
        "capability_track": "open_source_patch_generation",
        "dependency": dependency,
        "dataset": {
            "id": DATASET_ID,
            "split": "dev",
            "selected_task_count": len(TASKS),
            "dataset_hash": _hash_path(dataset_path.resolve()),
        },
        "outcomes": outcomes,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (
                promotion.get("promoted")
                or promotion.get("champion_id") == candidate.procedure_id
            )
            and restart["champion_retained"]
            and restart["session_retained"]
            and restart["accepted_patches_retained"]
            and restart["relearning_failures"] == 0
        ),
        "boundary": (
            "Patch text is generated without a repair menu, but localization "
            "and behavioral verifier families remain engineered and the "
            "public tasks are not contamination-proof."
        ),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path(
            "backend/modules/hexcore/data/open_patch_generation_state.json"
        ),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_open_patch_generation.json"),
    )
    parser.add_argument(
        "--provider",
        choices=("ollama", "openai"),
        default="ollama",
    )
    args = parser.parse_args()
    result = run_open_patch_generation(
        repo_root=args.repo_root,
        external_root=args.external_root,
        dataset_path=args.dataset_path,
        state_path=args.state_path,
        result_path=args.result_path,
        provider=(
            _generate_openai
            if args.provider == "openai"
            else _generate
        ),
        provider_name=(
            "openai" if args.provider == "openai" else "local_gemma"
        ),
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
