#!/usr/bin/env python3
"""Run the unpaid local RH authority audit and seed verified AION memory."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import aion_riemann_live_exam as live
from scripts.aion_riemann_verified_memory import (
    AionLeanRepairController,
    AionVerifiedMathMemory,
)


LAB = ROOT / "research" / "riemann_lab"
RESULTS = ROOT / "results" / "riemann_lab"
MEMORY_STATE = RESULTS / "aion_verified_memory.json"

CATALOG: tuple[dict[str, Any], ...] = (
    {
        "task_id": "zeta_at_zero",
        "statement": "riemannZeta 0 = -(1 : ℂ) / 2",
        "proof": "exact riemannZeta_zero",
        "theorem_signature": "riemannZeta_zero : riemannZeta 0 = -(1 : ℂ) / 2",
        "method_pattern": "Rewrite with the verified zeta special value, then normalize scalar arithmetic.",
        "imports": ["Mathlib.NumberTheory.LSeries.RiemannZeta"],
    },
    {
        "task_id": "trivial_zero_family",
        "statement": "For n : ℕ, riemannZeta (-2 * ((n : ℂ) + 1)) = 0",
        "proof": "exact riemannZeta_neg_two_mul_nat_add_one n",
        "theorem_signature": (
            "riemannZeta_neg_two_mul_nat_add_one (n : ℕ) : "
            "riemannZeta (-2 * ((n : ℂ) + 1)) = 0"
        ),
        "method_pattern": "Specialize the verified indexed trivial-zero family, then normalize the complex argument.",
        "imports": ["Mathlib.NumberTheory.LSeries.RiemannZeta"],
    },
    {
        "task_id": "zero_free_right_half_plane",
        "statement": "For s : ℂ with 1 < s.re, riemannZeta s ≠ 0",
        "proof": "exact riemannZeta_ne_zero_of_one_lt_re hs",
        "theorem_signature": (
            "riemannZeta_ne_zero_of_one_lt_re {s : ℂ} (hs : 1 < s.re) : "
            "riemannZeta s ≠ 0"
        ),
        "method_pattern": "Use the verified right-half-plane nonvanishing theorem or its order-theoretic contrapositive.",
        "imports": ["Mathlib.NumberTheory.LSeries.Dirichlet"],
    },
    {
        "task_id": "catalog_differentiable_away_from_one",
        "statement": "For s : ℂ with s ≠ 1, riemannZeta is differentiable at s",
        "declaration": "theorem catalog_differentiable_away_from_one {s : ℂ} (hs : s ≠ 1) : DifferentiableAt ℂ riemannZeta s := by",
        "proof": "exact differentiableAt_riemannZeta hs",
        "theorem_signature": (
            "differentiableAt_riemannZeta {s : ℂ} (hs : s ≠ 1) : "
            "DifferentiableAt ℂ riemannZeta s"
        ),
        "method_pattern": "Apply the verified pointwise differentiability theorem with the exclusion of the pole.",
        "imports": ["Mathlib.NumberTheory.LSeries.RiemannZeta"],
    },
    {
        "task_id": "catalog_real_part_positive",
        "statement": "For x : ℝ with 1 < x, 0 < (riemannZeta x).re",
        "declaration": "theorem catalog_real_part_positive {x : ℝ} (hx : 1 < x) : 0 < (riemannZeta x).re := by",
        "proof": "exact riemannZeta_re_pos_of_one_lt hx",
        "theorem_signature": (
            "riemannZeta_re_pos_of_one_lt {x : ℝ} (hx : 1 < x) : "
            "0 < (riemannZeta x).re"
        ),
        "method_pattern": "Apply the verified real-axis positivity theorem under the strict right-half-plane hypothesis.",
        "imports": ["Mathlib.NumberTheory.LSeries.Dirichlet"],
    },
    {
        "task_id": "catalog_compact_zero_set_finite",
        "statement": "Every compact S : Set ℂ has finite intersection with riemannZetaZeros",
        "declaration": "theorem catalog_compact_zero_set_finite {S : Set ℂ} (hS : IsCompact S) : (S ∩ riemannZetaZeros).Finite := by",
        "proof": "exact hS.inter_riemannZetaZeros_finite",
        "theorem_signature": (
            "IsCompact.inter_riemannZetaZeros_finite {S : Set ℂ} (hS : IsCompact S) : "
            "(S ∩ riemannZetaZeros).Finite"
        ),
        "method_pattern": "Apply the verified compact-intersection finiteness theorem for the zeta zero set.",
        "imports": ["Mathlib.NumberTheory.LSeries.ZetaZeros"],
    },
)

V2_PROOFS = {
    "scaled_zeta_at_zero": "rw [riemannZeta_zero]\nnorm_num",
    "trivial_zero_at_neg_six": (
        "convert riemannZeta_neg_two_mul_nat_add_one 2 using 1 <;> norm_num"
    ),
    "zero_implies_re_le_one": (
        "by_contra hs\nexact (riemannZeta_ne_zero_of_one_lt_re (not_le.mp hs)) hz"
    ),
    "zeta_differentiable_away_from_one": "exact differentiableAt_riemannZeta hs",
    "zeta_real_part_positive": "exact riemannZeta_re_pos_of_one_lt hx",
    "compact_has_finitely_many_zeta_zeros": "exact hS.inter_riemannZetaZeros_finite",
}

RETENTION_PROOFS = {
    "retained_shifted_zero_value": "rw [riemannZeta_zero]\nring",
    "retained_trivial_zero_neg_eight": (
        "convert riemannZeta_neg_two_mul_nat_add_one 3 using 1 <;> norm_num"
    ),
    "retained_zero_strict_upper_boundary": (
        "by_contra h\nexact riemannZeta_ne_zero_of_one_le_re (le_of_not_gt h) hz"
    ),
    "retained_zeta_analytic": "exact analyticOn_riemannZeta",
    "retained_zeta_real_axis": "exact riemannZeta_im_eq_zero_of_one_lt hx",
    "retained_zeta_zero_set_closed": "exact isClosed_riemannZetaZeros",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compile_file(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [str(live.LAKE), "env", "lean", str(path)],
        cwd=LAB,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": _sha256(path),
        "passed": proc.returncode == 0,
        "returncode": proc.returncode,
        "diagnostic": (proc.stdout + proc.stderr).strip()[-4000:],
    }


def _verify_batch(cases: list[tuple[dict[str, Any], str]]) -> list[dict[str, Any]]:
    imports = sorted(
        {
            str(module)
            for task, _proof in cases
            for module in (
                task.get("imports")
                or [
                    "Mathlib.NumberTheory.LSeries.RiemannZeta",
                    "Mathlib.NumberTheory.LSeries.Dirichlet",
                ]
            )
        }
    )
    declarations = []
    for task, proof in cases:
        standalone = live.theorem_source(task, proof)
        declarations.append(
            standalone.split("namespace AionRiemannLiveExam\n\n", 1)[1].rsplit(
                "\nend AionRiemannLiveExam", 1
            )[0]
        )
    source = (
        "".join(f"import {module}\n" for module in imports)
        + "\nnamespace AionRiemannLocalVerification\n\n"
        + "\n\n".join(declarations)
        + "\n\nend AionRiemannLocalVerification\n"
    )
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    with tempfile.NamedTemporaryFile("w", suffix=".lean", dir=LAB, delete=False) as handle:
        handle.write(source)
        path = Path(handle.name)
    try:
        proc = subprocess.run(
            [str(live.LAKE), "env", "lean", str(path)],
            cwd=LAB,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    finally:
        path.unlink(missing_ok=True)
    diagnostic = (proc.stdout + proc.stderr).strip()[-4000:]
    return [
        {
            "passed": proc.returncode == 0,
            "returncode": proc.returncode,
            "diagnostic": diagnostic,
            "source_hash": source_hash,
            "batch_verified": True,
        }
        for _case in cases
    ]


def main() -> int:
    if live.LAKE is None:
        raise RuntimeError("Lean lake executable is unavailable")
    RESULTS.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    immutable_paid = RESULTS / "live_exam_20260814T213917Z.json"
    packet = LAB / "live_task_packet.json"
    packet_data = json.loads(packet.read_text(encoding="utf-8"))
    packet_v2 = LAB / "live_task_packet_v2.json"
    packet_v2_data = json.loads(packet_v2.read_text(encoding="utf-8"))
    v2_tasks = packet_v2_data["source_closed_tasks"]
    retention_packet = LAB / "retention_task_packet_v1.json"
    retention_data = json.loads(retention_packet.read_text(encoding="utf-8"))
    acquisition_cases = [
        ({**item, "task_id": item["task_id"]}, item["proof"])
        for item in CATALOG
    ]
    v2_cases = [
        ({**task, "task_id": task["id"]}, V2_PROOFS[task["id"]])
        for task in v2_tasks
    ]
    retention_cases = [
        ({**task, "task_id": task["id"]}, RETENTION_PROOFS[task["id"]])
        for task in retention_data["source_closed_tasks"]
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        baseline_future = pool.submit(
            _compile_file, LAB / "RiemannLab" / "Tasks" / "EstablishedZeta.lean"
        )
        catalogue_future = pool.submit(_compile_file, LAB / "CatalogProbe.lean")
        foundation_future = pool.submit(
            _compile_file, LAB / "RiemannLab" / "Tasks" / "CriticalStripFoundation.lean"
        )
        verified_batch_future = pool.submit(
            _verify_batch, acquisition_cases + v2_cases + retention_cases
        )
        rejected_future = pool.submit(
            live.verify, {"task_id": "zeta_at_zero"}, "exact riemannZeta_zer0"
        )
        baseline = baseline_future.result()
        catalogue = catalogue_future.result()
        foundation = foundation_future.result()
        verified_batch = verified_batch_future.result()
        catalog_verifications = verified_batch[: len(acquisition_cases)]
        v2_verifications = verified_batch[
            len(acquisition_cases) : len(acquisition_cases) + len(v2_cases)
        ]
        retention_verifications = verified_batch[
            len(acquisition_cases) + len(v2_cases) :
        ]
        rejected = rejected_future.result()
    retention_templates = [
        {
            "task_id": task["id"],
            "family": task["family"],
            "passed": verification["passed"],
            "returncode": verification["returncode"],
            "statement_sha256": task["statement_sha256"],
            "proof_body_disclosed": task["proof_body_disclosed"],
        }
        for task, verification in zip(
            retention_data["source_closed_tasks"], retention_verifications, strict=True
        )
    ]
    memory_build = RESULTS / ".aion_verified_memory.build.json"
    memory_build.unlink(missing_ok=True)
    memory = AionVerifiedMathMemory(memory_build)
    templates = []
    for item, verification in zip(CATALOG, catalog_verifications, strict=True):
        promotion = None
        retrieval = []
        if verification["passed"]:
            promotion = memory.ingest_compiler_verified_method(
                task_id=item["task_id"],
                statement=item["statement"],
                theorem_signature=item["theorem_signature"],
                method_pattern=item["method_pattern"],
                required_imports=item["imports"],
                verification=verification,
                source_uri=f"scripts/aion_riemann_local_verify.py#CATALOG/{item['task_id']}",
            )
            retrieval = memory.retrieve(task_id=item["task_id"], statement=item["statement"])
        templates.append(
            {
                "task_id": item["task_id"],
                "passed": verification["passed"],
                "returncode": verification.get("returncode"),
                "source_sha256": verification.get("source_hash"),
                "diagnostic": verification.get("diagnostic"),
                "memory_promotion": promotion,
                "retrieved_claim_ids": [row["claim_id"] for row in retrieval],
                "proof_body_retained_in_memory": False,
            }
        )
    repair = AionLeanRepairController().diagnose(
        task_id="zeta_at_zero",
        diagnostic=rejected["diagnostic"],
        attempt=1,
    )
    v2_templates = []
    for task, verification in zip(v2_tasks, v2_verifications, strict=True):
        v2_templates.append(
            {
                "task_id": task["id"],
                "family": task["family"],
                "statement_sha256": task["statement_sha256"],
                "passed": verification["passed"],
                "returncode": verification.get("returncode"),
                "source_sha256": verification.get("source_hash"),
                "diagnostic": verification.get("diagnostic"),
            }
        )
    report = {
        "schema": "aion.riemann_local_verification.v1",
        "started_at": started.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "paid_api_calls": 0,
        "baseline": baseline,
        "catalogue": catalogue,
        "critical_strip_foundation": foundation,
        "live_templates": templates,
        "v2_held_out_templates": v2_templates,
        "retention_templates": retention_templates,
        "v2_packet": {
            "path": str(packet_v2.relative_to(ROOT)),
            "sha256": _sha256(packet_v2),
            "execution_status": packet_v2_data["execution_status"],
            "task_families": sorted({row["family"] for row in v2_templates}),
        },
        "repair_routing": {
            "invalid_candidate_rejected": rejected["passed"] is False,
            "record": repair,
        },
        "state_reconciliation": {
            "packet_execution_status": packet_data.get("execution_status"),
            "packet_sha256": _sha256(packet),
            "immutable_paid_result_sha256": _sha256(immutable_paid),
            "recorded_paid_result_sha256": packet_data["execution_history"][0]["result_sha256"],
            "immutable_paid_result_unchanged": (
                _sha256(immutable_paid) == packet_data["execution_history"][0]["result_sha256"]
            ),
        },
        "aion_memory": memory.runtime.status(),
        "claim_boundary": {
            "rh_solved": False,
            "new_mathematics": False,
            "aion_advantage_established": False,
        },
    }
    report["passed"] = bool(
        baseline["passed"]
        and catalogue["passed"]
        and foundation["passed"]
        and all(row["passed"] and row["retrieved_claim_ids"] for row in templates)
        and all(row["passed"] for row in v2_templates)
        and all(row["passed"] for row in retention_templates)
        and packet_v2_data["execution_status"] == "ready"
        and report["repair_routing"]["invalid_candidate_rejected"]
        and report["state_reconciliation"]["immutable_paid_result_unchanged"]
        and report["paid_api_calls"] == 0
    )
    if report["passed"]:
        os.replace(memory_build, MEMORY_STATE)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = RESULTS / f"local_verification_{stamp}.json"
    target.write_text(rendered, encoding="utf-8")
    (RESULTS / "local_verification_latest.json").write_text(rendered, encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "result": str(target)}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
