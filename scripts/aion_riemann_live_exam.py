#!/usr/bin/env python3
"""Run a matched, source-closed AION proof exam against Lean 4.

This is an evaluation of proof reconstruction, memory, and repair. It is not
an attempt to claim a proof of the Riemann Hypothesis.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.aion_riemann_verified_memory import (
    AionLeanRepairController,
    AionMathlibTheoremDiscovery,
    AionVerifiedMathMemory,
    render_theorem_discovery,
    render_verified_memory,
)


LAB = ROOT / "research" / "riemann_lab"
PACKET = Path(
    os.environ.get(
        "AION_RIEMANN_TASK_PACKET",
        str(LAB / "live_task_packet.json"),
    )
)
RESULTS = ROOT / "results" / "riemann_lab"
MEMORY_STATE = Path(
    os.environ.get(
        "AION_RIEMANN_MEMORY_STATE",
        str(RESULTS / "aion_verified_memory.json"),
    )
)
MODEL = os.environ.get("AION_RIEMANN_OPENAI_MODEL", "gpt-4.1")
LAKE = shutil.which("lake") or (
    "/opt/homebrew/bin/lake" if Path("/opt/homebrew/bin/lake").exists() else None
)


def _normalise_secret(value: str) -> str:
    """Recover an ASCII API key from accidental quoting or pasted formatting."""
    cleaned = value.strip()
    match = re.search(r"sk-[A-Za-z0-9_-]+", cleaned)
    if match:
        return match.group(0)
    return "".join(ch for ch in cleaned if ch.isascii() and not ch.isspace()).strip("\"'")


def load_key() -> str:
    key = _normalise_secret(os.environ.get("OPENAI_API_KEY", ""))
    if key:
        return key
    env_path = ROOT / ".env.local"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("OPENAI_API_KEY="):
                key = _normalise_secret(line.split("=", 1)[1])
                if key:
                    return key
    raise RuntimeError("OPENAI_API_KEY is unavailable")


def response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks)


class ProviderOutputError(RuntimeError):
    def __init__(self, message: str, provider: dict[str, Any]) -> None:
        super().__init__(message)
        self.provider = provider


def call_openai(key: str, prompt: str, *, max_output_tokens: int) -> tuple[str, dict[str, Any]]:
    body = {
        "model": MODEL,
        "input": [
            {
                "role": "system",
                "content": (
                    "You are completing a sealed Lean 4 proof exam using Mathlib. "
                    "Return only a JSON object containing a proof field. The proof "
                    "must be the tactic body that follows ':= by'. Never use sorry, "
                    "admit, axioms, unsafe assumptions, or numerical approximation."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_output_tokens": max_output_tokens,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "lean_proof",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"proof": {"type": "string"}},
                    "required": ["proof"],
                    "additionalProperties": False,
                },
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail[:800]}") from exc
    provider = {
        "response_id": payload.get("id"),
        "usage": payload.get("usage", {}),
        "model": payload.get("model", MODEL),
        "status": payload.get("status"),
        "incomplete_details": payload.get("incomplete_details"),
    }
    text = response_text(payload)
    try:
        parsed = json.loads(text)
        proof = str(parsed["proof"]).strip()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        provider["raw_output_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        raise ProviderOutputError("provider returned incomplete or invalid structured output", provider) from exc
    return proof, provider


def theorem_source(task: dict[str, Any], proof: str) -> str:
    declarations = {
        "zeta_at_zero": "theorem zeta_at_zero : riemannZeta 0 = -(1 : ℂ) / 2 := by",
        "trivial_zero_family": (
            "theorem trivial_zero_family (n : ℕ) : "
            "riemannZeta (-2 * ((n : ℂ) + 1)) = 0 := by"
        ),
        "zero_free_right_half_plane": (
            "theorem zero_free_right_half_plane (s : ℂ) (hs : 1 < s.re) : "
            "riemannZeta s ≠ 0 := by"
        ),
    }
    declaration = str(task.get("declaration") or declarations[task["task_id"]])
    if ":= by" not in declaration or re.search(r"\b(sorry|admit|axiom)\b", declaration, re.I):
        raise ValueError("task declaration must end in ':= by' and contain no prohibited token")
    imports = task.get("imports") or [
        "Mathlib.NumberTheory.LSeries.RiemannZeta",
        "Mathlib.NumberTheory.LSeries.Dirichlet",
    ]
    if not all(re.fullmatch(r"Mathlib\.[A-Za-z0-9_.]+", str(item)) for item in imports):
        raise ValueError("task imports must be qualified Mathlib module names")
    body = "\n".join(f"  {line}" for line in proof.splitlines())
    return (
        "".join(f"import {item}\n" for item in imports) + "\n"
        "namespace AionRiemannLiveExam\n\n"
        f"{declaration}\n{body}\n\n"
        "end AionRiemannLiveExam\n"
    )


def verify(task: dict[str, Any], proof: str) -> dict[str, Any]:
    if re.search(r"\b(sorry|admit|axiom)\b", proof, flags=re.IGNORECASE):
        return {"passed": False, "diagnostic": "prohibited proof token", "source_hash": None}
    source = theorem_source(task, proof)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    with tempfile.NamedTemporaryFile("w", suffix=".lean", dir=LAB, delete=False) as handle:
        handle.write(source)
        path = Path(handle.name)
    try:
        proc = subprocess.run(
            [str(LAKE), "env", "lean", str(path)],
            cwd=LAB,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        diagnostic = (proc.stdout + "\n" + proc.stderr).strip()
        return {
            "passed": proc.returncode == 0,
            "returncode": proc.returncode,
            "diagnostic": diagnostic[-6000:],
            "source_hash": digest,
        }
    finally:
        path.unlink(missing_ok=True)


def prompt_for(
    task: dict[str, Any],
    arm: dict[str, Any],
    attempt: int,
    prior: dict[str, Any] | None,
    memories: list[dict[str, Any]],
    repair_record: dict[str, Any] | None,
    theorem_discovery: list[dict[str, Any]],
) -> str:
    parts = [
        "Prove this theorem using the installed Mathlib library.",
        f"Task ID: {task['task_id']}",
        f"Statement: {task['statement']}",
        "Return the proof body only; do not include ':= by' or a markdown fence.",
    ]
    if arm["memory_enabled"]:
        if not memories:
            parts.append("Governed AION verified memory retrieval returned no relevant record.")
        else:
            parts.append("Governed AION verified memory records:\n" + render_verified_memory(memories))
    if attempt == 2 and prior:
        parts.append(f"Your first proof was rejected: {prior['proof']}")
        if arm["repair_enabled"]:
            if repair_record is None:
                raise RuntimeError("repair-enabled arm has no governed repair record")
            parts.append(
                f"Governed AION repair record {repair_record['repair_record_id']} "
                f"classified this as {repair_record['category']}. "
                f"Route: {repair_record['instruction']}\n"
                "Lean diagnostic:\n" + prior["verification"]["diagnostic"][-3500:]
            )
            if theorem_discovery:
                parts.append(
                    "Deterministic search results from the pinned Mathlib source tree:\n"
                    + render_theorem_discovery(theorem_discovery)
                )
        else:
            parts.append("Try a materially different proof. Compiler feedback is withheld in this arm.")
    return "\n\n".join(parts)


def validate_packet(packet: dict[str, Any], *, packet_path: Path | None = None) -> None:
    if packet.get("execution_status") != "ready":
        raise RuntimeError(
            "Live exam is fail-closed: task packet must be a new sealed packet "
            "with execution_status='ready'"
        )
    tasks = packet.get("tasks") or packet.get("source_closed_tasks") or []
    if not tasks:
        raise RuntimeError("Live exam is fail-closed: packet has no tasks")
    budgets = packet.get("budgets") or {}
    if budgets.get("max_attempts_per_task") != 2:
        raise RuntimeError("Live exam is fail-closed: exactly two attempts must be precommitted")
    output_limit = budgets.get("max_output_tokens_per_call")
    if not isinstance(output_limit, int) or not 128 <= output_limit <= 1000:
        raise RuntimeError("Live exam is fail-closed: bounded output tokens must be precommitted")
    scoring = packet.get("precommitted_scoring") or {}
    if not isinstance(scoring.get("full_aion_minimum_passed"), int):
        raise RuntimeError("Live exam is fail-closed: absolute success threshold is missing")
    for task in tasks:
        expected = task.get("statement_sha256")
        if expected is not None:
            actual = hashlib.sha256(str(task.get("statement") or "").encode("utf-8")).hexdigest()
            if actual != expected:
                raise RuntimeError(f"Live exam is fail-closed: statement hash mismatch for {task.get('id')}")
        if task.get("proof_body_disclosed") is not False:
            raise RuntimeError(f"Live exam is fail-closed: task {task.get('id')} is not source-closed")
    expected_environment = packet.get("environment_sha256")
    if expected_environment is not None:
        environment = hashlib.sha256()
        for name in ("lean-toolchain", "lake-manifest.json", "lakefile.toml"):
            environment.update(name.encode() + b"\0" + (LAB / name).read_bytes())
        if environment.hexdigest() != expected_environment:
            raise RuntimeError("Live exam is fail-closed: pinned Lean environment hash mismatch")
    manifest_path = packet.get("seal_manifest")
    if manifest_path:
        manifest_file = ROOT / str(manifest_path)
        if not manifest_file.exists():
            raise RuntimeError("Live exam is fail-closed: seal manifest is missing")
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        packet_hash = hashlib.sha256((packet_path or PACKET).read_bytes()).hexdigest()
        if manifest.get("packet", {}).get("sha256") != packet_hash:
            raise RuntimeError("Live exam is fail-closed: sealed packet hash mismatch")
        for relative, expected in (manifest.get("implementation_hashes") or {}).items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError(
                    f"Live exam is fail-closed: sealed implementation hash mismatch for {relative}"
                )


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _score_decision(result: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    scores = {arm["arm_id"]: arm["passed"] for arm in result["arms"]}
    rules = packet["precommitted_scoring"]
    full = scores.get("aion_memory_repair", 0)
    comparators = {key: value for key, value in scores.items() if key != "aion_memory_repair"}
    minimum = int(rules["full_aion_minimum_passed"])
    margin = int(rules["full_aion_minimum_margin_over_each_ablation"])
    infrastructure_failures = sum(
        1
        for arm in result["arms"]
        for task in arm["tasks"]
        for attempt in task["attempts"]
        if attempt.get("infrastructure_failure")
    )
    allowed_failures = int(rules.get("infrastructure_failures_allowed", 0))
    passed = (
        infrastructure_failures <= allowed_failures
        and full >= minimum
        and all(full - score >= margin for score in comparators.values())
    )
    return {
        "criterion_met": passed,
        "full_aion_score": full,
        "absolute_minimum": minimum,
        "required_margin": margin,
        "comparator_scores": comparators,
        "infrastructure_failures": infrastructure_failures,
        "infrastructure_failures_allowed": allowed_failures,
        "interpretation": (
            "The precommitted operational superiority criterion was met."
            if passed else
            "The precommitted operational superiority criterion was not met; no superiority claim is supported."
        ),
    }


def main() -> int:
    if not PACKET.exists():
        raise RuntimeError(f"Missing task packet: {PACKET}")
    if LAKE is None:
        raise RuntimeError("Lean lake executable is unavailable")
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    validate_packet(packet)
    packet_hash = hashlib.sha256(PACKET.read_bytes()).hexdigest()
    RESULTS.mkdir(parents=True, exist_ok=True)
    one_shot = RESULTS / f"execution_started_{packet_hash[:20]}.json"
    if one_shot.exists():
        raise RuntimeError("Live exam is fail-closed: this sealed packet already has an execution marker")
    memory = AionVerifiedMathMemory(MEMORY_STATE)
    memory_status = memory.runtime.status()
    if memory_status["active_claims"] < 1:
        raise RuntimeError("Live exam is fail-closed: verified AION memory is empty")
    repair_controller = AionLeanRepairController()
    discovery = AionMathlibTheoremDiscovery(
        LAB / ".lake" / "packages" / "mathlib" / "Mathlib" / "NumberTheory" / "LSeries"
    )
    arms = [
        {
            **arm,
            "arm_id": arm.get("arm_id") or arm["id"],
            "memory_enabled": bool(arm.get("memory_enabled", arm.get("memory", False))),
            "repair_enabled": bool(arm.get("repair_enabled", arm.get("repair", False))),
            "isolated_state": bool(arm.get("isolated_state", False)),
        }
        for arm in packet.get("arms", [])
    ]
    tasks = [
        {**task, "task_id": task.get("task_id") or task["id"]}
        for task in (packet.get("tasks") or packet.get("source_closed_tasks") or [])
    ]
    if not arms or not tasks:
        raise RuntimeError("Task packet contains no normalized arms or tasks")
    started = datetime.now(timezone.utc)
    result: dict[str, Any] = {
        "experiment": "aion_riemann_source_closed_live_exam_v1",
        "task_packet_schema": packet.get("schema"),
        "started_at": started.isoformat(),
        "model": MODEL,
        "task_packet_hash": packet_hash,
        "aion_mechanisms": {
            "memory": "HexCorePersistentLearningRuntime.knowledge.retrieve",
            "memory_state_hash": memory_status["state_hash"],
            "active_verified_claims": memory_status["active_claims"],
            "repair": "AionLeanRepairController.diagnose",
            "theorem_discovery": "AionMathlibTheoremDiscovery.search over pinned local Mathlib sources",
        },
        "claim_boundary": (
            "This evaluates formal proof reconstruction, retained operational memory, "
            "and compiler-guided repair. It does not prove RH or claim new mathematics."
        ),
        "arms": [],
    }
    _atomic_json(one_shot, {
        "packet_sha256": packet_hash,
        "started_at": started.isoformat(),
        "status": "execution_started_one_shot",
        "claim_boundary": "This marker records an attempt, not a successful experiment.",
    })
    key = load_key()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    checkpoint = RESULTS / f"live_exam_{stamp}_in_progress.json"
    max_attempts = int(packet["budgets"]["max_attempts_per_task"])
    max_output_tokens = int(packet["budgets"]["max_output_tokens_per_call"])
    for arm in arms:
        arm_result: dict[str, Any] = {**arm, "tasks": []}
        result["arms"].append(arm_result)
        for task in tasks:
            task_result: dict[str, Any] = {"task_id": task["task_id"], "attempts": []}
            memories = (
                memory.retrieve(task_id=task["task_id"], statement=task["statement"])
                if arm["memory_enabled"] and not arm["isolated_state"]
                else []
            )
            task_result["memory_retrieval"] = {
                "enabled": arm["memory_enabled"],
                "isolated_state": arm["isolated_state"],
                "claim_ids": [item["claim_id"] for item in memories],
                "capsule_ids": [cid for item in memories for cid in item["capsule_ids"]],
            }
            prior = None
            for attempt in range(1, max_attempts + 1):
                repair_record = None
                theorem_discovery = []
                if attempt == 2 and prior and arm["repair_enabled"]:
                    repair_record = repair_controller.diagnose(
                        task_id=task["task_id"],
                        diagnostic=prior["verification"]["diagnostic"],
                        attempt=1,
                    )
                    theorem_discovery = discovery.search(
                        statement=task["statement"],
                        diagnostic=prior["verification"]["diagnostic"],
                    )
                prompt = prompt_for(
                    task, arm, attempt, prior, memories, repair_record, theorem_discovery
                )
                t0 = time.monotonic()
                infrastructure_failure = False
                try:
                    proof, provider = call_openai(
                        key, prompt, max_output_tokens=max_output_tokens
                    )
                    verification = verify(task, proof)
                except ProviderOutputError as exc:
                    proof = ""
                    provider = exc.provider
                    infrastructure_failure = True
                    verification = {
                        "passed": False,
                        "returncode": None,
                        "diagnostic": str(exc),
                        "source_hash": None,
                    }
                record = {
                    "attempt": attempt,
                    "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "proof": proof,
                    "provider": provider,
                    "verification": verification,
                    "repair_record": repair_record,
                    "theorem_discovery": theorem_discovery,
                    "infrastructure_failure": infrastructure_failure,
                    "elapsed_seconds": round(time.monotonic() - t0, 3),
                }
                task_result["attempts"].append(record)
                print(
                    f"{arm['arm_id']} | {task['task_id']} | attempt {attempt} | "
                    f"{'PASS' if verification['passed'] else 'FAIL'}",
                    flush=True,
                )
                prior = record
                if verification["passed"]:
                    break
            task_result["passed"] = any(x["verification"]["passed"] for x in task_result["attempts"])
            arm_result["tasks"].append(task_result)
            _atomic_json(checkpoint, result)
        passed = sum(1 for item in arm_result["tasks"] if item["passed"])
        arm_result["passed"] = passed
        arm_result["total"] = len(arm_result["tasks"])
        arm_result["success_rate"] = passed / max(1, len(arm_result["tasks"]))
        arm_result["model_calls"] = sum(len(item["attempts"]) for item in arm_result["tasks"])
        _atomic_json(checkpoint, result)
    result["completed_at"] = datetime.now(timezone.utc).isoformat()
    result["duration_seconds"] = round((datetime.now(timezone.utc) - started).total_seconds(), 3)
    result["precommitted_decision"] = _score_decision(result, packet)
    result["all_infrastructure_checks_passed"] = (
        result["precommitted_decision"]["infrastructure_failures"] == 0
    )
    output = RESULTS / f"live_exam_{stamp}.json"
    latest = RESULTS / "live_exam_latest.json"
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    _atomic_json(output, result)
    _atomic_json(latest, result)
    _atomic_json(one_shot, {
        "packet_sha256": packet_hash,
        "started_at": started.isoformat(),
        "completed_at": result["completed_at"],
        "status": "completed",
        "result": str(output.relative_to(ROOT)),
        "result_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    })
    checkpoint.unlink(missing_ok=True)
    print(json.dumps({
        "result": str(output),
        "duration_seconds": result["duration_seconds"],
        "scores": {a["arm_id"]: f"{a['passed']}/{a['total']}" for a in result["arms"]},
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
