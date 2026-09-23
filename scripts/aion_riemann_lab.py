#!/usr/bin/env python3
"""Minimal, fail-closed AION research harness for formal zeta mathematics."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
LAB = REPO / "research" / "riemann_lab"
RESULTS = REPO / "results" / "riemann_lab"
LIVE_PACKET = LAB / "live_task_packet.json"
BANNED = re.compile(r"(?m)^\s*(axiom|sorry|admit)\b")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def lake_binary() -> str | None:
    found = shutil.which("lake")
    if found:
        return found
    candidate = Path.home() / ".elan" / "bin" / "lake"
    return str(candidate) if candidate.exists() else None


def compile_lean(lake: str, source: str, name: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="aion-rh-") as temp:
        path = Path(temp) / f"{name}.lean"
        path.write_text(source, encoding="utf-8")
        completed = subprocess.run(
            [lake, "env", "lean", str(path)],
            cwd=LAB,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
    output = (completed.stdout + completed.stderr).strip()
    return {
        "accepted": completed.returncode == 0,
        "return_code": completed.returncode,
        "source_sha256": digest(source),
        "compiler_output": output[-4000:],
    }


def candidate(theorem_name: str, proof: str) -> str:
    return f"""import Mathlib.NumberTheory.LSeries.RiemannZeta

namespace RiemannLabExperiment
theorem {theorem_name} : riemannZeta 0 = -(1 : ℂ) / 2 := by
  {proof}
end RiemannLabExperiment
"""


def proof_policy() -> dict:
    # Audit only AION-authored laboratory sources.  The Lake workspace also
    # contains pinned Mathlib dependencies under .lake/packages; scanning those
    # would incorrectly reject the lab for declarations inside trusted upstream
    # packages that are not part of AION's submitted proof.
    inspected = [LAB / "RiemannLab.lean"]
    inspected.extend(sorted((LAB / "RiemannLab").rglob("*.lean")))
    inspected = [path for path in inspected if path.is_file()]
    violations: list[dict] = []
    for path in inspected:
        for match in BANNED.finditer(path.read_text(encoding="utf-8")):
            violations.append({"file": str(path.relative_to(LAB)), "token": match.group(1)})
    return {
        "accepted": not violations,
        "trusted_base": "Pinned Lean kernel and Mathlib",
        "project_declared_incompleteness": violations,
        "files_inspected": [str(path.relative_to(LAB)) for path in inspected],
    }


def main() -> int:
    lake = lake_binary()
    RESULTS.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    live_packet = (
        json.loads(LIVE_PACKET.read_text(encoding="utf-8"))
        if LIVE_PACKET.exists()
        else {"execution_status": "missing"}
    )
    result = {
        "schema": "aion.riemann_trusted_lab.v1",
        "created_at": now.isoformat(),
        "claim_boundary": {
            "rh_solved": False,
            "new_mathematics": False,
            "evidence_class": "trusted_formal_lab_smoke_test",
        },
        "candidate_generation": {
            "mode": "fixed_fixture",
            "live_aion_invoked": False,
            "live_proposer_invoked": False,
            "purpose": "Trusted Lean gate and experiment-mechanics smoke test only.",
        },
        "interpretation": {
            "fixture_only": True,
            "statement": (
                "Fixed proof strings validate the Lean gate and arm plumbing; "
                "they do not measure AION, proposer, memory, repair, retention, "
                "or progress on the Riemann Hypothesis."
            ),
            "live_exam_packet": str(LIVE_PACKET),
            "live_exam_execution_status": live_packet.get("execution_status", "unknown"),
        },
        "proof_policy": proof_policy(),
        "toolchain": {"lake": lake, "available": bool(lake)},
        "baseline": {},
        "experiments": {},
    }
    if not lake or not result["proof_policy"]["accepted"]:
        result["status"] = "BLOCKED_FAIL_CLOSED"
    else:
        baseline_path = LAB / "RiemannLab" / "Tasks" / "EstablishedZeta.lean"
        baseline = subprocess.run(
            [lake, "env", "lean", str(baseline_path)],
            cwd=LAB,
            text=True,
            capture_output=True,
            timeout=300,
            check=False,
        )
        result["baseline"] = {
            "accepted": baseline.returncode == 0,
            "return_code": baseline.returncode,
            "source_sha256": digest(baseline_path.read_text(encoding="utf-8")),
            "compiler_output": (baseline.stdout + baseline.stderr).strip()[-4000:],
        }

        retention_proofs = {
            "proposer_alone": "rfl",
            "aion_memory_repair": "exact riemannZeta_zero",
            "aion_no_memory": "rfl",
            "aion_no_repair": "exact riemannZeta_zero",
        }
        result["experiments"]["source_closed_retention"] = {
            "fixture_only": True,
            "arms": {
                arm: compile_lean(lake, candidate(f"retention_{arm}", proof), f"retention_{arm}")
                | {
                    "memory_available": arm in {"aion_memory_repair", "aion_no_repair"},
                    "repair_available": arm in {"aion_memory_repair", "aion_no_memory"},
                }
                for arm, proof in retention_proofs.items()
            },
        }

        initial = "exact riemannZeta_zer0"
        repair_proofs = {
            "proposer_alone": initial,
            "aion_memory_repair": "exact riemannZeta_zero",
            "aion_no_memory": initial,
            "aion_no_repair": initial,
        }
        result["experiments"]["compiler_guided_repair"] = {
            "fixture_only": True,
            "arms": {
                arm: compile_lean(lake, candidate(f"repair_{arm}", proof), f"repair_{arm}")
                | {
                    "common_initial_candidate_sha256": digest(candidate("repair_common", initial)),
                    "repair_applied": arm == "aion_memory_repair",
                    "verified_memory_used": arm == "aion_memory_repair",
                }
                for arm, proof in repair_proofs.items()
            },
        }
        result["status"] = (
            "PASS_TRUSTED_LAB_SMOKE_TEST"
            if result["baseline"]["accepted"]
            and result["experiments"]["source_closed_retention"]["arms"]["aion_memory_repair"]["accepted"]
            and result["experiments"]["compiler_guided_repair"]["arms"]["aion_memory_repair"]["accepted"]
            else "FAIL"
        )

    target = RESULTS / f"riemann_lab_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest = RESULTS / "latest.json"
    latest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "result": str(target)}, indent=2))
    return 0 if result["status"] == "PASS_TRUSTED_LAB_SMOKE_TEST" else 1


if __name__ == "__main__":
    raise SystemExit(main())
