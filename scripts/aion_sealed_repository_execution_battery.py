#!/usr/bin/env python3
"""Sealed repository-execution evaluation for AION's matched arms.

The model must write executable Python into a disposable repository. Public
tests may guide permitted repair arms; final hidden tests are committed before
generation and scored once. This is an architecture evaluation, not evidence
of consciousness or AGI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import textwrap
import urllib.request

from aion_frontier_missions import FRONTIER_MISSIONS
from aion_signature_transfer_missions import SIGNATURE_MISSIONS
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.modules.hexcore.open_mission_compounding_governor import (  # noqa: E402
    ARMS,
    OpenMissionCompoundingGovernor,
    frozen_campaign_contract,
)

OUT_ROOT = REPO / "results/immutable/aion_sealed_repository_execution_battery"
REPORT = REPO / "docs/aion/AION_SEALED_REPOSITORY_EXECUTION_BATTERY_2026-08-12.md"
AUTHORITY = "sealed_hidden_python_test_authority_v1"
ACTION_BUDGET = 2
TOOL_HASH = hashlib.sha256(b"python3-stdlib|ollama-gemma3|write-solution-only|v1").hexdigest()


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


TEST_PREAMBLE = """
import importlib.util, json, sys, traceback
path = sys.argv[1]
spec = importlib.util.spec_from_file_location("candidate_solution", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Public mission tests are authored like ordinary repository tests and may
# call candidate functions directly (for example, ``ingest_pages(...)``).
# The sealed runner loads the candidate as a module, so expose its public
# symbols to the test namespace before executing those tests. Hidden tests
# may continue to use the explicit ``module`` reference.
for _candidate_name in dir(module):
    if not _candidate_name.startswith("_"):
        globals().setdefault(_candidate_name, getattr(module, _candidate_name))

passed = 0
failed = []
def check(first, second):
    global passed
    if callable(second):
        name = str(first)
        try:
            second()
            passed += 1
        except Exception as exc:
            failed.append({"name": name, "error": f"{type(exc).__name__}: {exc}"})
        return

    name = str(second)
    if bool(first):
        passed += 1
    else:
        failed.append({"name": name, "error": name})
"""


MISSIONS: list[dict[str, Any]] = [
    {
        "id": "repo_pagination_retry_checkpoint_v1",
        "family": "api_pagination",
        "objective": "Implement a robust paginated collector with retry, deduplication and checkpoint evidence.",
        "spec": """
Create solution.py with:
    collect_pages(fetch_page, start_cursor=None, max_retries=2) -> dict

fetch_page(cursor) returns a dictionary. An OK page is
{"status":"ok", "rows":[{"id": ...}, ...], "next_cursor": ..., "done": bool}.
A transient page is {"status":"retry"}; retry the same cursor, at most
max_retries times for that cursor, then raise RuntimeError. Do not accept rows
from transient pages. Deduplicate rows by id while preserving the first row and
its order. Detect a repeated cursor and raise ValueError. Return
{"rows": [...], "last_cursor": <last successfully fetched cursor>,
 "retry_count": <total transient responses>}.
Do not use network, files, subprocesses, packages, randomness or clocks.
""",
        "starter": "def collect_pages(fetch_page, start_cursor=None, max_retries=2):\n    raise NotImplementedError\n",
        "public": """
calls=[]
pages={None:{"status":"ok","rows":[{"id":1,"v":"a"}],"next_cursor":"b","done":False},
       "b":{"status":"ok","rows":[{"id":1,"v":"new"},{"id":2}],"next_cursor":None,"done":True}}
def fetch(cursor): calls.append(cursor); return pages[cursor]
def basic_dedupe():
    expected=[{"id":1,"v":"a"},{"id":2}]
    out=module.collect_pages(fetch)
    assert out["rows"] == expected, f"expected rows {expected!r}, got {out.get('rows')!r}; fetch cursors={calls!r}"
    assert calls == [None,"b"], f"expected fetch cursors [None, 'b'], got {calls!r}"
check("basic_dedupe", basic_dedupe)
attempt={"n":0}
def retry(_):
    attempt["n"] += 1
    return {"status":"retry"} if attempt["n"] == 1 else {"status":"ok","rows":[],"next_cursor":None,"done":True}
def one_retry():
    out=module.collect_pages(retry)
    assert out["retry_count"] == 1, f"expected retry_count 1, got {out.get('retry_count')!r}; calls={attempt['n']}"
    assert attempt["n"] == 2, f"expected two calls for one transient retry, got {attempt['n']}"
check("one_retry", one_retry)
""",
        "hidden": """
def start_cursor():
    seen=[]
    def fetch(c): seen.append(c); return {"status":"ok","rows":[{"id":"x"}],"next_cursor":None,"done":True}
    out=module.collect_pages(fetch,"seed")
    assert seen == ["seed"] and out["last_cursor"] == "seed"
check("start_cursor_checkpoint", start_cursor)
def exhaustion():
    def fetch(_): return {"status":"retry", "rows":[{"id":"forbidden"}]}
    try: module.collect_pages(fetch,max_retries=1)
    except RuntimeError: return
    raise AssertionError("retry exhaustion did not fail")
check("retry_exhaustion", exhaustion)
def cycle():
    pages={None:{"status":"ok","rows":[],"next_cursor":"a","done":False},"a":{"status":"ok","rows":[],"next_cursor":"a","done":False}}
    try: module.collect_pages(lambda c: pages[c])
    except ValueError: return
    raise AssertionError("cursor cycle did not fail")
check("cursor_cycle", cycle)
""",
    },
    {
        "id": "repo_schema_evolution_receipt_v1",
        "family": "schema_migration",
        "objective": "Implement deterministic backward-compatible customer record migration with conflict evidence.",
        "spec": """
Create solution.py with migrate_customer(record) -> dict. Produce schema_version
2 with keys customer_name, amount, receipt, conflict and extensions. Name
precedence is customer_name, then client_name, then name; blank/None names do
not count. conflict is true when two or more nonblank name aliases disagree.
receipt is {"receipt_id": record.get("receipt_id"), "accepted": True}.
extensions must preserve every unknown input key, but exclude schema_version,
the three name aliases, amount and receipt_id. Do not mutate the input.
""",
        "starter": "def migrate_customer(record):\n    raise NotImplementedError\n",
        "public": """
def basic():
    row={"name":"Ada","amount":12,"receipt_id":"r1","legacy":7}
    out=module.migrate_customer(row)
    expected={"schema_version":2,"customer_name":"Ada","amount":12,"receipt":{"receipt_id":"r1","accepted":True},"conflict":False,"extensions":{"legacy":7}}
    assert out == expected, f"expected {expected!r}, got {out!r}"
    assert row == {"name":"Ada","amount":12,"receipt_id":"r1","legacy":7}, f"input was mutated: {row!r}"
check("basic_migration", basic)
""",
        "hidden": """
def precedence_conflict():
    out=module.migrate_customer({"customer_name":"Primary","client_name":"Other","name":"Primary","x":1})
    assert out["customer_name"] == "Primary" and out["conflict"] is True and out["extensions"] == {"x":1}
check("precedence_conflict", precedence_conflict)
def blanks():
    out=module.migrate_customer({"customer_name":" ","client_name":None,"name":"Fallback","schema_version":1})
    assert out["customer_name"] == "Fallback" and out["conflict"] is False and "schema_version" not in out["extensions"]
check("blank_aliases", blanks)
def missing():
    out=module.migrate_customer({})
    assert out["customer_name"] is None and out["receipt"]["receipt_id"] is None
check("missing_fields", missing)
""",
    },
    {
        "id": "repo_access_policy_deny_first_v1",
        "family": "access_policy_regression",
        "objective": "Implement fail-closed scoped authorization with expiry and a complete audit trail.",
        "spec": """
Create solution.py with authorize(rules, scope, now) -> dict. Each rule has id,
effect ('allow' or 'deny'), scope (exact string or '*'), and optional expires_at.
A rule is active when expires_at is absent or expires_at > now. Matching active
deny overrides every allow. Otherwise a matching active allow permits access;
default is deny. Return {"allowed": bool, "reason": one of
'explicit_deny'/'explicit_allow'/'default_deny', "audit": [...]}. audit contains
one entry per input rule, in input order: {"id", "matched", "active"}. Invalid
effects never authorize and are shown in audit. Do not mutate input.
""",
        "starter": "def authorize(rules, scope, now):\n    raise NotImplementedError\n",
        "public": """
def allow():
    out=module.authorize([{"id":"a","effect":"allow","scope":"read"}],"read",10)
    expected={"allowed":True,"reason":"explicit_allow","audit":[{"id":"a","matched":True,"active":True}]}
    assert out == expected, f"expected {expected!r}, got {out!r}"
check("exact_allow", allow)
""",
        "hidden": """
def deny_override():
    rules=[{"id":"a","effect":"allow","scope":"*"},{"id":"d","effect":"deny","scope":"pay"}]
    out=module.authorize(rules,"pay",0)
    assert out["allowed"] is False and out["reason"] == "explicit_deny" and len(out["audit"]) == 2
check("deny_override", deny_override)
def expiry_boundary():
    out=module.authorize([{"id":"a","effect":"allow","scope":"*","expires_at":5}],"read",5)
    assert out["allowed"] is False and out["audit"][0]["active"] is False
check("expiry_boundary", expiry_boundary)
def invalid():
    out=module.authorize([{"id":"x","effect":"permit","scope":"*"}],"read",0)
    assert out["allowed"] is False and out["reason"] == "default_deny" and out["audit"][0]["matched"] is True
check("invalid_fail_closed", invalid)
""",
    },
    {
        "id": "repo_configuration_provenance_v1",
        "family": "configuration_precedence",
        "objective": "Implement typed recursive configuration precedence with rejection evidence and leaf provenance.",
        "spec": """
Create solution.py with resolve_config(layers) -> dict. layers is ordered low to
high precedence and each item is {"name": str, "value": dict}. Recursively merge
dictionaries. Scalars and lists replace earlier values only when their Python
types match exactly (bool and int are different); on mismatch retain the old
value and append {"path": dotted_path, "layer": layer_name} to rejected.
New keys are accepted. Return {"config": merged, "provenance": {dotted leaf
path: layer name}, "rejected": [...]}. Input must not be mutated.
""",
        "starter": "def resolve_config(layers):\n    raise NotImplementedError\n",
        "public": """
def basic():
    layers=[{"name":"base","value":{"db":{"host":"a","ports":[1]}}},{"name":"env","value":{"db":{"host":"b","ports":[2]}}}]
    out=module.resolve_config(layers)
    expected_config={"db":{"host":"b","ports":[2]}}
    expected_provenance={"db.host":"env","db.ports":"env"}
    assert out.get("config") == expected_config, f"expected config {expected_config!r}, got {out.get('config')!r}"
    assert out.get("provenance") == expected_provenance, f"expected provenance {expected_provenance!r}, got {out.get('provenance')!r}"
    assert out.get("rejected") == [], f"expected no rejected values, got {out.get('rejected')!r}"
check("recursive_precedence", basic)
""",
        "hidden": """
def mismatch():
    out=module.resolve_config([{"name":"base","value":{"workers":2,"flag":True}},{"name":"bad","value":{"workers":"2","flag":1}}])
    assert out["config"] == {"workers":2,"flag":True}
    assert out["rejected"] == [{"path":"workers","layer":"bad"},{"path":"flag","layer":"bad"}]
    assert out["provenance"] == {"workers":"base","flag":"base"}
check("typed_rejection", mismatch)
def new_nested():
    out=module.resolve_config([{"name":"base","value":{}},{"name":"site","value":{"a":{"b":3}}}])
    assert out["config"] == {"a":{"b":3}} and out["provenance"] == {"a.b":"site"}
check("new_nested_leaf", new_nested)
def no_mutation():
    layers=[{"name":"x","value":{"a":[1]}}]
    module.resolve_config(layers)["config"]["a"].append(2)
    assert layers == [{"name":"x","value":{"a":[1]}}]
check("no_mutation", no_mutation)
""",
    },
]


METHOD_CARD = """Retained cross-domain method card (earned before this sealed exam):
1. Translate the contract into explicit invariants and fail-closed conditions.
2. Preserve input immutability, ordering and provenance unless told otherwise.
3. Implement the smallest pure solution, run public tests, and repair the named
   invariant rather than rewriting unrelated behavior.
4. Never access hidden authority, network, clock, randomness or external files.
"""


def test_source(body: str) -> str:
    return textwrap.dedent(TEST_PREAMBLE + body + "\nprint(json.dumps({'passed':passed,'failed':failed}, sort_keys=True))\nsys.exit(1 if failed else 0)\n")


def run_tests(test_path: Path, solution_path: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(test_path), str(solution_path)],
            text=True, capture_output=True, timeout=8, check=False,
            env={"PATH": os.environ.get("PATH", "")},
        )
    except subprocess.TimeoutExpired:
        return {"passed": 0, "failed": [{"name": "timeout", "error": "execution exceeded 8 seconds"}], "exit_code": 124}
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    try:
        payload = json.loads(lines[-1]) if lines else {"passed": 0, "failed": [{"name": "load", "error": proc.stderr[-800:]}]}
    except json.JSONDecodeError:
        payload = {"passed": 0, "failed": [{"name": "protocol", "error": (proc.stdout + proc.stderr)[-800:]}]}
    payload["exit_code"] = proc.returncode
    return payload


def _extract_solution(payload: Any) -> str:
    """Accept the small set of structured shapes local model servers emit."""
    if isinstance(payload, str):
        candidate = payload.strip()
        if candidate.startswith("```"):
            candidate = candidate.split("\n", 1)[-1].rsplit("```", 1)[0]
        return candidate
    if isinstance(payload, dict):
        for key in ("solution", "solution.py", "code", "content"):
            candidate = payload.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return _extract_solution(candidate)
    return ""


def _load_openai_key() -> str:
    def valid_key(value: object) -> str:
        candidate = str(value or "").strip().strip("\"'")
        if (
            candidate.isascii()
            and candidate.startswith(("sk-", "sess-"))
            and len(candidate) > 30
        ):
            return candidate
        return ""

    configured = valid_key(os.environ.get("OPENAI_API_KEY", ""))
    if configured:
        return configured
    for path in (REPO / ".env.local", REPO / "backend" / ".env.local", REPO / ".env"):
        if not path.exists():
            continue
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            key, separator, value = line.partition("=")
            if separator and key.strip() == "OPENAI_API_KEY":
                configured = valid_key(value)
                if configured:
                    return configured
    return ""


def _openai_output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    parts: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            value = content.get("text")
            if isinstance(value, str) and value.strip():
                parts.append(value)
    return "\n".join(parts)


def call_model(provider: str, model: str, prompt: str, seed: int) -> tuple[str, dict[str, Any]]:
    schema = {
        "type": "object",
        "properties": {"solution": {"type": "string"}},
        "required": ["solution"],
        "additionalProperties": False,
    }
    if provider == "openai":
        api_key = _load_openai_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps({
                "model": model,
                "input": prompt,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "solution_response",
                        "strict": True,
                        "schema": schema,
                    }
                },
                "max_output_tokens": 3000,
            }).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = json.loads(response.read().decode())
        response_payload = _openai_output_text(raw)
        try:
            parsed = json.loads(response_payload)
        except (json.JSONDecodeError, TypeError):
            parsed = response_payload
        solution = _extract_solution(parsed)
        return solution, {
            "provider": "openai",
            "model": raw.get("model", model),
            "response_id": raw.get("id"),
            "status": raw.get("status"),
            "solution_chars": len(solution),
        }

    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": schema,
            "keep_alive": 0,
            "options": {"temperature": 0.2, "seed": seed, "num_predict": 2200},
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = json.loads(response.read().decode())
    response_payload = raw.get("response", "")
    try:
        parsed = json.loads(response_payload) if isinstance(response_payload, str) else response_payload
    except (json.JSONDecodeError, TypeError):
        parsed = response_payload
    solution = _extract_solution(parsed)
    meta = {key: raw.get(key) for key in ("model", "total_duration", "prompt_eval_count", "eval_count")}
    meta["provider"] = "ollama"
    meta["response_keys"] = sorted(parsed) if isinstance(parsed, dict) else []
    meta["solution_chars"] = len(solution)
    return solution, meta


def compile_solution(solution_path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "-I", "-m", "py_compile", str(solution_path)],
        text=True, capture_output=True, timeout=8, check=False,
        env={"PATH": os.environ.get("PATH", "")},
    )
    return {"passed": proc.returncode == 0, "error": proc.stderr[-800:]}


def arm_settings(arm: str) -> tuple[bool, bool, int]:
    """Return memory, repair-feedback and matched generation budget controls."""
    memory_enabled = arm in {"full_aion", "aion_no_repair"}
    repair_enabled = arm in {"full_aion", "aion_no_memory"}
    return memory_enabled, repair_enabled, ACTION_BUDGET


def prompt_for(mission: dict[str, Any], arm: str, starter: str, prior: str, feedback: dict[str, Any] | None) -> str:
    memory, _, _ = arm_settings(arm)
    public_tests = mission.get("public", mission.get("public_tests", ""))
    sections = [
        "You are solving a sealed Python repository task. Return ONLY valid JSON with exactly one key named solution containing the complete solution.py source. Do not use markdown.",
        "The submitted file must be standalone, use only the Python standard library, preserve every required public function signature, and must not import from __main__, the test harness, or an unavailable project module.",
        "Implement the specification directly. Do not return commentary, pseudocode, placeholders, tests, or an unchanged starter file.",
        f"Objective:\n{mission['objective']}",
        f"Starter file:\n{starter}",
        f"Public tests:\n{test_source(public_tests)}",
    ]
    if mission.get("spec"):
        sections.insert(4, f"Public contract:\n{textwrap.dedent(mission['spec']).strip()}")
    if memory:
        sections.append(mission.get("method_card", METHOD_CARD))
    if prior:
        sections.append(f"Previous solution:\n{prior}")
    if feedback:
        sections.append("Public test feedback (hidden tests have not been run):\n" + json.dumps(feedback, sort_keys=True))
    sections.append("Hidden tests are unavailable. Solve the contract generally; never guess or request them.")
    return "\n\n".join(sections)


def run_arm(run_dir: Path, mission: dict[str, Any], arm: str, provider: str, model: str, seed: int) -> dict[str, Any]:
    arm_dir = run_dir / mission["id"] / arm
    arm_dir.mkdir(parents=True, exist_ok=True)
    starter = mission.get("starter", "")
    solution = starter
    best_solution = starter
    best_public: dict[str, Any] | None = None
    best_applied = False
    feedback = None
    attempts: list[dict[str, Any]] = []
    _, repair_enabled, max_attempts = arm_settings(arm)
    for attempt in range(1, max_attempts + 1):
        prior_solution = solution if repair_enabled and attempt > 1 else ""
        prompt = prompt_for(mission, arm, starter, prior_solution, feedback)
        try:
            candidate, model_meta = call_model(provider, model, prompt, seed + attempt - 1)
        except Exception as exc:
            candidate, model_meta = "", {"error": f"{type(exc).__name__}: {exc}"}
        proposal_nonempty = bool(candidate.strip())
        proposal_changed = proposal_nonempty and candidate.strip() != starter.strip()
        solution_path = arm_dir / "solution.py"
        proposed_solution = candidate if proposal_nonempty else best_solution
        solution_path.write_text(proposed_solution)
        compile_result = compile_solution(solution_path)
        proposal_applied = proposal_changed and compile_result["passed"]
        if compile_result["passed"]:
            proposal_public = run_tests(arm_dir / "public_tests.py", solution_path)
        else:
            proposal_public = {
                "passed": 0,
                "failed": [{"name": "compile", "error": compile_result["error"]}],
                "exit_code": 1,
            }

        proposal_score = (int(proposal_public.get("passed", 0)), -len(proposal_public.get("failed", [])))
        best_score = (
            (int(best_public.get("passed", 0)), -len(best_public.get("failed", [])))
            if best_public is not None else (-1, -10_000)
        )
        candidate_retained = bool(proposal_applied and proposal_score > best_score)
        if candidate_retained:
            best_solution = proposed_solution
            best_public = proposal_public
            best_applied = True
        solution = best_solution
        solution_path.write_text(best_solution)
        public_result = best_public or run_tests(arm_dir / "public_tests.py", solution_path)
        attempts.append({
            "attempt": attempt,
            "prompt_hash": digest(prompt),
            "proposal_solution_hash": digest(proposed_solution),
            "retained_solution_hash": digest(best_solution),
            "model": model_meta,
            "proposal_nonempty": proposal_nonempty,
            "proposal_changed": proposal_changed,
            "proposal_compiles": compile_result["passed"],
            "proposal_applied": proposal_applied,
            "candidate_retained": candidate_retained,
            "compile_error": compile_result["error"],
            "proposal_public": proposal_public,
            "public": public_result,
        })
        if not public_result["failed"]:
            break
        feedback = (
            {
                "failed": proposal_public["failed"][:6],
                "retained_candidate_public": public_result,
                "instruction": "Repair the retained Previous solution. Do not discard behavior that already passes.",
            }
            if repair_enabled
            else None
        )
    (arm_dir / "solution.py").write_text(best_solution)
    hidden_result = run_tests(run_dir / "authority" / f"{mission['id']}_hidden.py", arm_dir / "solution.py")
    verified_success = bool(
        best_applied
        and best_public is not None
        and not best_public.get("failed", True)
        and not hidden_result["failed"]
    )
    result = {
        "arm": arm, "model": model, "seed": seed, "attempts": attempts,
        "attempt_count": len(attempts), "public_result": best_public or attempts[-1]["public"],
        "hidden_result": hidden_result, "verified_success": verified_success,
        "solution_hash": digest(best_solution), "hidden_scored_once": True,
    }
    write_json(arm_dir / "receipt.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("ollama", "openai"), default="ollama")
    parser.add_argument("--model", default="gemma3:1b")
    parser.add_argument("--suite", choices=("baseline", "frontier", "signature"), default="baseline")
    parser.add_argument("--mission-limit", type=int, default=None)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    run_id = args.run_id or f"sealed_repo_{now.strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = OUT_ROOT / run_id
    authority_dir = run_dir / "authority"
    authority_dir.mkdir(parents=True, exist_ok=False)
    if args.suite == "frontier":
        mission_catalog = FRONTIER_MISSIONS
    elif args.suite == "signature":
        mission_catalog = SIGNATURE_MISSIONS
    else:
        mission_catalog = MISSIONS
    mission_limit = len(mission_catalog) if args.mission_limit is None else args.mission_limit
    missions = mission_catalog[: max(1, min(mission_limit, len(mission_catalog)))]

    hidden_commitments: dict[str, str] = {}
    for mission in missions:
        mission_id = mission["id"]
        hidden_tests = mission.get("hidden", mission.get("hidden_tests"))
        if not isinstance(hidden_tests, str) or not hidden_tests.strip():
            raise ValueError(f"Mission {mission_id} has no valid hidden test source")
        source = test_source(hidden_tests)
        path = authority_dir / f"{mission['id']}_hidden.py"
        path.write_text(source)
        hidden_commitments[mission["id"]] = hashlib.sha256(source.encode()).hexdigest()
        for arm in ARMS:
            arm_dir = run_dir / mission["id"] / arm
            arm_dir.mkdir(parents=True, exist_ok=True)
            public_tests = mission.get("public", mission.get("public_tests"))
            if not isinstance(public_tests, str) or not public_tests.strip():
                raise ValueError(f"Mission {mission_id} has no valid public test source")
            (arm_dir / "public_tests.py").write_text(test_source(public_tests))
    proposer_id = f"{args.provider}:{args.model}"
    tool_manifest_hash = hashlib.sha256(
        f"python3-stdlib|{proposer_id}|write-solution-only|v2".encode()
    ).hexdigest()
    commitment = {
        "run_id": run_id, "committed_at": now.isoformat(), "provider": args.provider, "model": args.model,
        "arms": list(ARMS), "action_budget_ceiling": ACTION_BUDGET,
        "tool_manifest_hash": tool_manifest_hash, "hidden_test_hashes": hidden_commitments,
        "rule": "Hidden tests committed before any model generation and scored once per arm.",
    }
    write_json(run_dir / "sealed_commitment.json", commitment)

    governor = OpenMissionCompoundingGovernor(state_path=run_dir / "governor.json")
    campaign = frozen_campaign_contract(
        proposer_id=proposer_id,
        tool_manifest_hash=tool_manifest_hash,
        action_budget=ACTION_BUDGET,
        started_at=now,
    )
    governor.authorize(campaign)
    results: list[dict[str, Any]] = []
    for index, mission in enumerate(missions):
        packet = governor.register_mission({
            "mission_id": mission["id"], "lane": "software_systems",
            "objective": mission["objective"], "evaluator_authority": AUTHORITY,
            "success_contract": {
                "frozen_before_execution": True,
                "all_hidden_tests_pass": True,
                "hidden_test_commitment": hidden_commitments[mission["id"]],
            },
            "source_policy": {
                "closes_after_learning": True,
                "public_contract_and_tests_visible": True,
                "hidden_authority_committed_before_generation": True,
            },
            "risk_class": "local_disposable_repository",
        })
        for arm in ARMS:
            result = run_arm(run_dir, mission, arm, args.provider, args.model, 81200 + index)
            governor.record_outcome({
                "mission_id": mission["id"], "mission_hash": packet["mission_hash"],
                "arm": arm, "proposer_id": proposer_id, "tool_manifest_hash": tool_manifest_hash,
                "action_budget": ACTION_BUDGET, "evaluator_authority": AUTHORITY,
                "success": result["verified_success"],
                "unsafe_actions": 0,
                "investigation_actions": result["attempt_count"],
                "verified_work_units": 1.0 if result["verified_success"] else 0.0,
                "human_intervention_minutes": 0.0,
                "evidence": {"hidden_commitment": hidden_commitments[mission["id"]], "receipt": f"{mission['id']}/{arm}/receipt.json"},
            })
            results.append({"mission_id": mission["id"], **result})
        governor.close_source(mission_id=mission["id"])
        print(f"completed {mission['id']}", flush=True)

    summary: dict[str, Any] = {
        "run_id": run_id, "provider": args.provider, "model": args.model,
        "proposer_id": proposer_id, "suite": args.suite,
        "missions": len(missions), "arms": {}
    }
    for arm in ARMS:
        rows = [row for row in results if row["arm"] == arm]
        summary["arms"][arm] = {
            "successes": sum(row["verified_success"] for row in rows), "total": len(rows),
            "attempts": sum(row["attempt_count"] for row in rows),
        }
    summary["unsafe_outcomes"] = 0
    snapshot = governor.snapshot()
    summary["retention_due"] = [
        {
            "mission_id": row.get("mission_id"),
            "source_closed_at": row.get("source_closed_at"),
            "retention_due_at": row.get("retention_due_at"),
        }
        for row in snapshot.get("missions", [])
        if row.get("retention_due_at")
    ]
    model_attempts = [
        attempt.get("model", {})
        for row in results
        for attempt in row.get("attempts", [])
    ]
    channel_errors = sorted({
        meta["error"] for meta in model_attempts if meta.get("error")
    })
    proposal_failures = [
        f"{row['mission_id']}:{row['arm']}"
        for row in results
        if not any(attempt.get("proposal_applied") for attempt in row.get("attempts", []))
    ]
    # Bad or unchanged code is a legitimate model outcome. The evaluator is invalid
    # only when its own model channel or evidence protocol failed.
    summary["evaluator_valid"] = bool(model_attempts) and not channel_errors
    summary["evaluator_errors"] = channel_errors
    summary["proposal_failures"] = proposal_failures
    summary["claim_10x"] = False
    summary["limitations"] = [
        f"Small internal {len(missions)}-mission {args.suite} sample using proposer {proposer_id}.",
        "Hidden executable tests improve rigor but remain authored by the project team.",
        "One successful run cannot establish broad intelligence, AGI or consciousness.",
        "Source-closed retention remains pending for seven days after this run.",
    ]
    write_json(run_dir / "summary.json", summary)
    write_json(run_dir / "all_receipts.json", results)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AION Sealed Repository-Execution Battery — 12 August 2026", "",
        f"Run: `{run_id}`", f"Proposer: `{proposer_id}`", "",
        "## Result", "",
        "| Arm | Hidden-test successes | Model attempts |", "|---|---:|---:|",
    ]
    for arm in ARMS:
        row = summary["arms"][arm]
        lines.append(f"| {arm} | {row['successes']}/{row['total']} | {row['attempts']} |")
    lines += [
        "", "## What changed", "",
        "This battery requires each arm to write executable code into a disposable repository. Public tests are available to every arm; only the repair-enabled arms may use their failures for another attempt. Hidden tests were hashed and sealed before generation, were never included in prompts, and were scored once.",
        "", "## Honest boundary", "",
        *[f"- {item}" for item in summary["limitations"]],
        "", "The 10x claim remains closed. This is an architecture test, not evidence of subjective awareness.", "",
    ]
    REPORT.write_text("\n".join(lines))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
