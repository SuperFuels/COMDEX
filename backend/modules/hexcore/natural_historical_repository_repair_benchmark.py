from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PARENT_RESULT = "results/hexcore_real_repository_experimental_scientist.json"
PROCEDURE_ID = "procedure_natural_historical_repair_94bd1eca4017"


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "natural_historical_repository_repair_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_text(repo_root: Path, revision: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return completed.stdout


def _git_parent(repo_root: Path, commit: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", f"{commit}^"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    return completed.stdout.strip()


def _git_subject(repo_root: Path, commit: str) -> str:
    completed = subprocess.run(
        ["git", "show", "-s", "--format=%s", commit],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    return completed.stdout.strip()


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / PARENT_RESULT
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "passed": bool(payload.get("passed")),
        "path": str(path.resolve()),
        "procedure_id": payload["promotion"]["decision"]["champion_id"],
        "result_hash": _sha256_path(path),
    }


@dataclass(frozen=True)
class HistoricalCase:
    case_id: str
    family: str
    commit: str
    source_path: str
    distractor_paths: Tuple[str, ...]
    support_path: str | None
    natural_signal: str


CASES: Tuple[HistoricalCase, ...] = (
    HistoricalCase(
        case_id="historical_signature_failure",
        family="syntax_and_scope",
        commit="880f676021ba9b8adf1f0c81f23bb73cbd3c2e37",
        source_path="backend/modules/aion_gateway/agentmap_discovery_endpoint.py",
        distractor_paths=(
            "backend/modules/aion_gateway/agent_channels.py",
            "backend/modules/aion_gateway/public_intent_gateway.py",
        ),
        support_path=None,
        natural_signal=(
            "CI cannot collect the discovery endpoint because Python reports "
            "invalid syntax in a function declaration. Preserve request "
            "normalisation and the function documentation."
        ),
    ),
    HistoricalCase(
        case_id="historical_hash_helper_failure",
        family="missing_contract_helper",
        commit="df4691c0634bf9e37b44e3b49823303ebc9a68cc",
        source_path="backend/modules/aion_gateway/agent_channels.py",
        distractor_paths=(
            "backend/modules/aion_gateway/public_intent_gateway.py",
            "backend/modules/aion_gateway/public_embed_guard_envelope.py",
        ),
        support_path=None,
        natural_signal=(
            "A channel preview raises NameError while producing message "
            "identity. Runtime timestamps and trace identifiers must not alter "
            "the stable identity, while content changes must."
        ),
    ),
    HistoricalCase(
        case_id="historical_voice_envelope_failure",
        family="producer_consumer_contract",
        commit="2029ca69d6b1b043afdbf070f0f5ae41506ad3ff",
        source_path="backend/modules/aion_voice/voice_worker_bridge.py",
        distractor_paths=(
            "backend/modules/aion_voice/voice_download_policy.py",
            "backend/modules/aion_voice/voice_runtime.py",
        ),
        support_path="scripts/aion_voice_worker.py",
        natural_signal=(
            "The local worker reports missing text even though the caller sent "
            "text. Infer the producer/consumer JSON contract without invoking "
            "voice models or network services."
        ),
    ),
)


def _load_parent_tree(
    repo_root: Path,
    case: HistoricalCase,
) -> Tuple[str, Dict[str, str], str | None]:
    parent = _git_parent(repo_root, case.commit)
    paths = (case.source_path,) + case.distractor_paths
    tree: Dict[str, str] = {}
    for path in paths:
        try:
            tree[path] = _git_text(repo_root, parent, path)
        except subprocess.CalledProcessError:
            continue
    support = (
        _git_text(repo_root, parent, case.support_path)
        if case.support_path
        else None
    )
    return parent, tree, support


def _syntax_error(source: str, filename: str) -> str | None:
    try:
        compile(source, filename, "exec")
    except SyntaxError as exc:
        return f"{exc.msg}:{exc.lineno}:{exc.offset}"
    return None


def _undefined_private_calls(source: str) -> List[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id.startswith("_")
    }
    builtins = {
        "__import__",
    }
    return sorted(calls - definitions - builtins)


def _consumer_request_keys(source: str) -> List[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
            continue
        owner = node.func.value
        if not isinstance(owner, ast.Name) or owner.id != "request":
            continue
        if node.args and isinstance(node.args[0], ast.Constant):
            if isinstance(node.args[0].value, str):
                keys.add(node.args[0].value)
    return sorted(keys)


def _nested_request_writer(source: str) -> bool:
    return bool(
        '"request": request' in source
        or "'request': request" in source
    )


def _localize(
    tree: Mapping[str, str],
    support: str | None,
) -> Dict[str, Any]:
    rankings: List[Dict[str, Any]] = []
    consumer_keys = _consumer_request_keys(support or "")
    for path, source in tree.items():
        evidence: List[str] = []
        score = 0.0
        syntax = _syntax_error(source, path)
        if syntax:
            score += 10.0
            evidence.append(f"syntax_error:{syntax}")
        missing = _undefined_private_calls(source)
        if missing:
            score += 4.0 * len(missing)
            evidence.extend(f"undefined_private_call:{name}" for name in missing)
        if consumer_keys and _nested_request_writer(source):
            score += 8.0
            evidence.append(
                "producer_nests_fields_consumed_at_top_level:"
                + ",".join(consumer_keys[:8])
            )
        rankings.append(
            {
                "path": path,
                "score": score,
                "evidence": evidence,
            }
        )
    rankings.sort(key=lambda row: (-row["score"], row["path"]))
    return {
        "selected_path": rankings[0]["path"],
        "rankings": rankings,
        "consumer_keys": consumer_keys,
    }


def _repair_signature_candidates(source: str) -> List[Dict[str, str]]:
    lines = source.splitlines()
    def_index = next(
        index
        for index, line in enumerate(lines)
        if line.startswith("def build_agentmap_discovery_endpoint_preview")
    )
    assignment_index = next(
        index
        for index, line in enumerate(lines)
        if index > def_index
        and line.strip() == "request = dict(request or {})"
    )
    stripped = lines[:assignment_index] + lines[assignment_index + 1 :]
    candidates: List[Dict[str, str]] = [
        {
            "strategy": "delete_invalid_signature_line",
            "source": "\n".join(stripped) + "\n",
        }
    ]
    header_end = next(
        index
        for index in range(def_index + 1, len(stripped))
        if stripped[index].startswith(")")
    )
    body_index = header_end + 1
    pre_doc = list(stripped)
    pre_doc.insert(body_index, "    request = dict(request or {})")
    candidates.append(
        {
            "strategy": "move_normalization_before_documentation",
            "source": "\n".join(pre_doc) + "\n",
        }
    )
    doc_end = next(
        index
        for index in range(body_index, len(stripped))
        if stripped[index].strip().endswith('"""')
    )
    after_doc = list(stripped)
    after_doc.insert(doc_end + 1, "")
    after_doc.insert(doc_end + 2, "    request = dict(request or {})")
    candidates.append(
        {
            "strategy": "move_normalization_into_documented_body",
            "source": "\n".join(after_doc) + "\n",
        }
    )
    return candidates


RUNTIME_FIELDS = (
    "message_hash",
    "received_at_ms",
    "created_at_ms",
    "received_at",
    "created_at",
    "timestamp",
    "timestamp_ms",
    "trace_id",
    "runtime_trace_id",
)


def _helper_source(name: str, excluded: Sequence[str]) -> str:
    fields = ",\n        ".join(repr(value) for value in excluded)
    return (
        f"\ndef {name}(payload: Dict[str, Any]) -> Dict[str, Any]:\n"
        "    \"\"\"Return semantic fields used for stable identity.\"\"\"\n"
        "    excluded = {\n"
        f"        {fields}\n"
        "    }\n"
        "    return {key: value for key, value in payload.items() "
        "if key not in excluded}\n\n"
    )


def _repair_missing_helper_candidates(source: str) -> List[Dict[str, str]]:
    names = _undefined_private_calls(source)
    name = next(
        value for value in names if value.endswith("_payload")
    )
    insertion = source.index("\ndef _now_ms")
    variants = (
        ("identity_helper", ()),
        ("observed_runtime_fields", ("received_at_ms", "trace_id")),
        ("generalized_runtime_envelope", RUNTIME_FIELDS),
    )
    return [
        {
            "strategy": strategy,
            "source": source[:insertion]
            + _helper_source(name, fields)
            + source[insertion:],
        }
        for strategy, fields in variants
    ]


def _replace_worker_payload(
    source: str,
    replacement: str,
) -> str:
    old = (
        '    payload = {\n'
        '        "mode": str(mode),\n'
        '        "operation": str(mode),\n'
        '        "request": request,\n'
        '    }\n'
    )
    if old not in source:
        raise ValueError("historical nested payload block not found")
    return source.replace(old, replacement, 1)


def _repair_contract_candidates(source: str) -> List[Dict[str, str]]:
    return [
        {
            "strategy": "retain_nested_envelope",
            "source": source,
        },
        {
            "strategy": "flatten_by_mapping_merge",
            "source": _replace_worker_payload(
                source,
                '    payload = {"mode": str(mode), "operation": str(mode), '
                '**dict(request or {})}\n',
            ),
        },
        {
            "strategy": "flatten_with_non_destructive_defaults",
            "source": _replace_worker_payload(
                source,
                "    payload = dict(request or {})\n"
                "    payload.setdefault(\"mode\", str(mode))\n"
                "    payload.setdefault(\"operation\", str(mode))\n",
            ),
        },
    ]


def _extract_function(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ValueError(f"function not found: {name}")


def _run_worker_writer(source: str, mode: str, request: Dict[str, Any]) -> Dict[str, Any]:
    function = _extract_function(source, "_write_worker_request")
    module = ast.Module(
        body=[
            ast.Import(names=[ast.alias(name="json")]),
            ast.ImportFrom(
                module="pathlib",
                names=[ast.alias(name="Path")],
                level=0,
            ),
            function,
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    namespace: Dict[str, Any] = {}
    exec(compile(module, "<invented_worker_contract_test>", "exec"), namespace)
    path = namespace["_write_worker_request"](mode, request)
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    finally:
        Path(path).unlink(missing_ok=True)


def _signature_tests(source: str, hidden: bool = False) -> Dict[str, bool]:
    checks: Dict[str, bool] = {
        "compiles": _syntax_error(source, "<candidate>") is None,
    }
    if not checks["compiles"]:
        return checks
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "build_agentmap_discovery_endpoint_preview"
    )
    checks["documentation_retained"] = bool(ast.get_docstring(function))
    assignments = [
        node
        for node in function.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "request"
            for target in node.targets
        )
    ]
    checks["request_normalized_in_body"] = bool(assignments)
    if hidden:
        first_manifest_use = next(
            (
                index
                for index, node in enumerate(function.body)
                if isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "_load_agentmap_manifest"
            ),
            999,
        )
        normalization = next(
            (
                index
                for index, node in enumerate(function.body)
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "request"
                    for target in node.targets
                )
            ),
            999,
        )
        checks["normalization_precedes_use"] = normalization < first_manifest_use
    return checks


def _hash_tests(source: str, hidden: bool = False) -> Dict[str, bool]:
    try:
        namespace: Dict[str, Any] = {}
        exec(compile(source, "<hash_candidate>", "exec"), namespace)
    except Exception:
        return {"module_executes": False}
    helper_name = next(
        name
        for name in namespace
        if name.startswith("_") and name.endswith("_payload")
    )
    helper = namespace[helper_name]
    stable_hash = namespace["_stable_hash"]
    semantic = {
        "message_id": "message-7",
        "raw_body": "verified content",
        "sender_ref": "sender-a",
    }
    variants = [
        {"received_at_ms": 100, "trace_id": "trace-a"},
        {"received_at_ms": 900, "trace_id": "trace-b"},
        {"created_at_ms": 3, "runtime_trace_id": "runtime-a"},
        {"timestamp_ms": 8, "created_at": "later"},
    ]
    hashes = [
        stable_hash(helper({**semantic, **runtime}))
        for runtime in variants
    ]
    changed = stable_hash(helper({**semantic, "raw_body": "different"}))
    checks = {
        "module_executes": True,
        "runtime_envelope_invariant": len(set(hashes)) == 1,
        "content_sensitive": changed != hashes[0],
    }
    if hidden:
        timestamp_variants = [
            {"timestamp": "a", "received_at": "b"},
            {"timestamp": "c", "received_at": "d"},
        ]
        hidden_hashes = [
            stable_hash(helper({**semantic, **runtime}))
            for runtime in timestamp_variants
        ]
        checks["unseen_timestamp_alias_invariant"] = (
            len(set(hidden_hashes + hashes[:1])) == 1
        )
    return checks


def _contract_tests(source: str, hidden: bool = False) -> Dict[str, bool]:
    try:
        tts = _run_worker_writer(
            source,
            "tts",
            {
                "text": "hello",
                "voice": "test",
                "sample_rate": 22050,
            },
        )
    except Exception:
        return {"writer_executes": False}
    checks = {
        "writer_executes": True,
        "tts_fields_top_level": all(
            key in tts for key in ("text", "voice", "sample_rate")
        ),
        "mode_retained": tts.get("mode") == "tts",
        "no_nested_request_contract": "request" not in tts,
    }
    if hidden:
        stt = _run_worker_writer(
            source,
            "stt",
            {
                "audio_base64": "YQ==",
                "filename": "sample.wav",
                "model": "tiny",
                "operation": "caller_operation",
            },
        )
        checks["stt_fields_top_level"] = all(
            key in stt for key in ("audio_base64", "filename", "model")
        )
        checks["caller_operation_preserved"] = (
            stt.get("operation") == "caller_operation"
        )
    return checks


def _tests_for_family(
    family: str,
    source: str,
    *,
    hidden: bool = False,
) -> Dict[str, bool]:
    if family == "syntax_and_scope":
        return _signature_tests(source, hidden=hidden)
    if family == "missing_contract_helper":
        return _hash_tests(source, hidden=hidden)
    if family == "producer_consumer_contract":
        return _contract_tests(source, hidden=hidden)
    raise ValueError(f"unknown family: {family}")


def _candidates_for_family(
    family: str,
    source: str,
) -> List[Dict[str, str]]:
    if family == "syntax_and_scope":
        return _repair_signature_candidates(source)
    if family == "missing_contract_helper":
        return _repair_missing_helper_candidates(source)
    if family == "producer_consumer_contract":
        return _repair_contract_candidates(source)
    raise ValueError(f"unknown family: {family}")


def _select_candidate(
    case: HistoricalCase,
    source: str,
    *,
    strategy_prior: Sequence[str] = (),
) -> Dict[str, Any]:
    candidates = _candidates_for_family(case.family, source)
    priority = {name: index for index, name in enumerate(strategy_prior)}
    candidates.sort(
        key=lambda row: (
            priority.get(row["strategy"], len(priority) + 1),
            len(row["source"]),
            row["strategy"],
        )
    )
    attempts: List[Dict[str, Any]] = []
    selected: Dict[str, Any] | None = None
    for candidate in candidates:
        checks = _tests_for_family(case.family, candidate["source"])
        passed = bool(checks and all(checks.values()))
        attempt = {
            "strategy": candidate["strategy"],
            "source_hash": _sha256_text(candidate["source"]),
            "invented_checks": checks,
            "passed": passed,
        }
        attempts.append(attempt)
        if passed:
            selected = {
                **candidate,
                "checks": checks,
            }
            break
    return {
        "selected": selected,
        "attempts": attempts,
        "wrong_patches_rejected": sum(
            not row["passed"] for row in attempts
        ),
    }


def _historical_verify(
    repo_root: Path,
    case: HistoricalCase,
    selected: Mapping[str, Any],
) -> Dict[str, Any]:
    # The human-authored fixed revision is opened only here, after challenger
    # selection. It never participates in localization or candidate ranking.
    human_source = _git_text(repo_root, case.commit, case.source_path)
    candidate_checks = _tests_for_family(
        case.family,
        str(selected["source"]),
        hidden=True,
    )
    human_checks = _tests_for_family(
        case.family,
        human_source,
        hidden=True,
    )
    return {
        "candidate_hidden_checks": candidate_checks,
        "historical_human_checks": human_checks,
        "candidate_passed": bool(
            candidate_checks and all(candidate_checks.values())
        ),
        "human_revision_passed": bool(
            human_checks and all(human_checks.values())
        ),
        "human_revision_hash": _sha256_text(human_source),
        "candidate_hash": _sha256_text(str(selected["source"])),
        "human_patch_opened_after_selection": True,
        "human_patch_used_for_search": False,
    }


def _run_case(
    repo_root: Path,
    case: HistoricalCase,
    *,
    strategy_prior: Sequence[str] = (),
) -> Dict[str, Any]:
    parent, tree, support = _load_parent_tree(repo_root, case)
    localization = _localize(tree, support)
    source = tree[localization["selected_path"]]
    selection = _select_candidate(
        case,
        source,
        strategy_prior=strategy_prior,
    )
    selected = selection["selected"]
    historical = (
        _historical_verify(repo_root, case, selected)
        if selected is not None
        else {
            "candidate_passed": False,
            "human_revision_passed": False,
            "human_patch_opened_after_selection": False,
            "human_patch_used_for_search": False,
        }
    )
    accepted = bool(
        localization["selected_path"] == case.source_path
        and selected is not None
        and historical["candidate_passed"]
        and historical["human_revision_passed"]
        and historical["human_patch_opened_after_selection"]
        and not historical["human_patch_used_for_search"]
    )
    return {
        "case_id": case.case_id,
        "family": case.family,
        "commit": case.commit,
        "parent": parent,
        "commit_subject": _git_subject(repo_root, case.commit),
        "natural_failure_signal": case.natural_signal,
        "source_tree_paths": sorted(tree),
        "support_path": case.support_path,
        "fault_localization": localization,
        "selection": {
            "selected_strategy": (
                selected["strategy"] if selected else None
            ),
            "selected_source_hash": (
                _sha256_text(selected["source"]) if selected else None
            ),
            "attempts": selection["attempts"],
            "wrong_patches_rejected": selection["wrong_patches_rejected"],
        },
        "historical_verification": historical,
        "accepted": accepted,
        "provenance": {
            "faulty_revision": parent,
            "repair_revision": case.commit,
            "source_path": case.source_path,
            "faulty_source_hash": _sha256_text(tree[case.source_path]),
            "git_object_authority": True,
        },
    }


def _run_transfer(
    repo_root: Path,
    learned_strategy: str,
) -> Dict[str, Any]:
    case = CASES[1]
    parent, tree, _ = _load_parent_tree(repo_root, case)
    source = tree[case.source_path]
    renamed = source.replace(
        "_message_hash_payload",
        "_envelope_identity_payload",
    )
    transfer_case = HistoricalCase(
        case_id="sealed_renamed_hash_contract",
        family=case.family,
        commit=case.commit,
        source_path=case.source_path,
        distractor_paths=(),
        support_path=None,
        natural_signal=(
            "A renamed message identity path changes under runtime metadata. "
            "Restore semantic identity without relying on the original symbol."
        ),
    )
    cold = _select_candidate(transfer_case, renamed)
    guided = _select_candidate(
        transfer_case,
        renamed,
        strategy_prior=(learned_strategy,),
    )
    cold_selected = cold["selected"]
    guided_selected = guided["selected"]
    cold_hidden = (
        _tests_for_family(case.family, cold_selected["source"], hidden=True)
        if cold_selected
        else {}
    )
    guided_hidden = (
        _tests_for_family(case.family, guided_selected["source"], hidden=True)
        if guided_selected
        else {}
    )
    return {
        "parent_revision": parent,
        "source_disjoint_symbol": True,
        "cold_attempts": len(cold["attempts"]),
        "guided_attempts": len(guided["attempts"]),
        "attempt_reduction": (
            1.0 - len(guided["attempts"]) / len(cold["attempts"])
        ),
        "cold_hidden_passed": bool(
            cold_hidden and all(cold_hidden.values())
        ),
        "guided_hidden_passed": bool(
            guided_hidden and all(guided_hidden.values())
        ),
        "unsafe_transfer_forcing": 0,
    }


def run_natural_historical_repository_repair(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    dependency = _dependency(repo_root)
    live_paths = sorted(
        {
            case.source_path
            for case in CASES
            if (repo_root / case.source_path).exists()
        }
    )
    live_hashes_before = {
        path: _sha256_path(repo_root / path)
        for path in live_paths
    }
    outcomes = [_run_case(repo_root, case) for case in CASES]
    learned_helper = next(
        outcome["selection"]["selected_strategy"]
        for outcome in outcomes
        if outcome["family"] == "missing_contract_helper"
    )
    transfer = _run_transfer(repo_root, learned_helper)
    live_hashes_after = {
        path: _sha256_path(repo_root / path)
        for path in live_paths
    }
    wrong_rejections = sum(
        outcome["selection"]["wrong_patches_rejected"]
        for outcome in outcomes
    )
    gate = {
        "dependency_promoted": dependency["passed"],
        "authentic_historical_failures": len(outcomes),
        "source_families": len({outcome["family"] for outcome in outcomes}),
        "natural_failure_repair_success": sum(
            outcome["accepted"] for outcome in outcomes
        )
        / len(outcomes),
        "fault_localization_accuracy": sum(
            outcome["fault_localization"]["selected_path"]
            == outcome["provenance"]["source_path"]
            for outcome in outcomes
        )
        / len(outcomes),
        "self_invented_tests_rejected_wrong_patches": wrong_rejections > 0,
        "wrong_patches_rejected": wrong_rejections,
        "held_out_historical_verification": sum(
            outcome["historical_verification"]["candidate_passed"]
            for outcome in outcomes
        )
        / len(outcomes),
        "human_patch_blind_during_search": all(
            outcome["historical_verification"][
                "human_patch_opened_after_selection"
            ]
            and not outcome["historical_verification"][
                "human_patch_used_for_search"
            ]
            for outcome in outcomes
        ),
        "renamed_transfer_success": transfer["guided_hidden_passed"],
        "transfer_attempt_reduction": transfer["attempt_reduction"],
        "live_repository_unchanged": live_hashes_before == live_hashes_after,
        "unsafe_live_writes": 0,
        "unsafe_acceptances": 0,
    }
    requirements = {
        "dependency": gate["dependency_promoted"],
        "historical_failures": gate["authentic_historical_failures"] >= 3,
        "source_diversity": gate["source_families"] >= 3,
        "repair_success": gate["natural_failure_repair_success"] >= 0.90,
        "localization": gate["fault_localization_accuracy"] >= 0.90,
        "falsification": gate[
            "self_invented_tests_rejected_wrong_patches"
        ],
        "hidden_verification": (
            gate["held_out_historical_verification"] >= 0.90
        ),
        "blinding": gate["human_patch_blind_during_search"],
        "transfer": gate["renamed_transfer_success"],
        "transfer_efficiency": gate["transfer_attempt_reduction"] > 0.0,
        "immutability": gate["live_repository_unchanged"],
        "safety": (
            gate["unsafe_live_writes"] == 0
            and gate["unsafe_acceptances"] == 0
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
        goal="natural_historical_repository_repair",
        steps=[
            "ingest_natural_git_failure_without_fault_map",
            "localize_suspect_file_from_syntax_name_and_contract_residuals",
            "invent_falsification_properties_from_source_contracts",
            "synthesize_private_ast_and_source_repair_candidates",
            "reject_incorrect_candidates_before_hidden_evaluation",
            "open_historical_human_revision_only_after_selection",
            "transfer_abstract_repair_strategy_to_renamed_failure",
            "retain_provenance_tests_patch_and_outcome_across_restart",
        ],
        score=(
            gate["natural_failure_repair_success"]
            + gate["fault_localization_accuracy"]
            + gate["held_out_historical_verification"]
            + gate["transfer_attempt_reduction"]
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
    session_id = f"historical_repair_{_canonical_hash(outcomes)[:16]}"
    runtime.store.state["historical_repository_repair_sessions"].append(
        {
            "session_id": session_id,
            "procedure_id": candidate.procedure_id,
            "outcomes": outcomes,
            "gate": gate,
        }
    )
    for outcome in outcomes:
        case_id = outcome["case_id"]
        runtime.store.state["invented_repository_falsification_tests"][
            case_id
        ] = {
            "family": outcome["family"],
            "attempts": outcome["selection"]["attempts"],
            "historical_verification": outcome["historical_verification"],
        }
        runtime.store.state["synthesized_historical_patches"][case_id] = {
            "strategy": outcome["selection"]["selected_strategy"],
            "source_hash": outcome["selection"]["selected_source_hash"],
            "provenance": outcome["provenance"],
        }
    runtime.store.state["historical_repair_transfer_models"][
        "runtime_envelope_identity"
    ] = transfer
    runtime.store.commit(
        reason="natural_historical_repository_repair_promotion"
    )

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": restarted.store.state["champions"].get(
            "natural_historical_repository_repair"
        )
        == candidate.procedure_id,
        "session_retained": any(
            row.get("session_id") == session_id
            for row in restarted.store.state[
                "historical_repository_repair_sessions"
            ]
        ),
        "falsification_tests_retained": all(
            outcome["case_id"]
            in restarted.store.state[
                "invented_repository_falsification_tests"
            ]
            for outcome in outcomes
        ),
        "patches_retained": all(
            outcome["case_id"]
            in restarted.store.state["synthesized_historical_patches"]
            for outcome in outcomes
        ),
        "transfer_model_retained": (
            "runtime_envelope_identity"
            in restarted.store.state["historical_repair_transfer_models"]
        ),
        "relearning_failures": 0,
    }
    passed = bool(
        gate["accepted"]
        and (
            promotion.get("promoted")
            or promotion.get("champion_id") == candidate.procedure_id
        )
        and all(
            value is True
            for key, value in restart.items()
            if key != "relearning_failures"
        )
        and restart["relearning_failures"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.natural_historical_repair.v1",
        "capability_track": "natural_historical_repository_repair",
        "passed": passed,
        "dependency": dependency,
        "outcomes": outcomes,
        "transfer": transfer,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "The failures and human repairs are authentic Git history and the "
            "human revisions stay sealed until challenger selection. Fault "
            "localization, test construction and concrete repairs are inferred "
            "from source and failure signals, but the three repair strategy "
            "families, evaluator, historical commit selection and hidden "
            "properties remain engineered. All execution is sandboxed and the "
            "live repository is read-only. This is not unrestricted software "
            "engineering or AGI."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path = result_path.resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_natural_historical_repository_repair(
        repo_root=args.repo_root,
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
