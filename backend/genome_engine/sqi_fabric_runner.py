from __future__ import annotations

from typing import Any, Dict, List
import hashlib

from .stable_json import stable_stringify, stable_hash
from .sqi_fabric_contract import SqiPlan, SqiResult


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _kg_writes_jsonl(kg_writes: List[Dict[str, Any]]) -> str:
    """
    Deterministic JSONL payload for SQI_KG_WRITES.jsonl:
    - stable sort
    - stable stringify per line
    - trailing newline if non-empty
    """
    writes_sorted = sorted(
        list(kg_writes or []),
        key=lambda w: (str(w.get("id", "")), str(w.get("kind", "")), str(w.get("payload_digest", ""))),
    )
    lines = [stable_stringify(w) for w in writes_sorted]
    return "\n".join(lines) + ("\n" if lines else "")


def build_sqi_fabric_plan(
    *,
    run_id: str,  # accepted for call-site compatibility; NOT used in digest/ids
    seed: int,
    scope: str,
    scenario_summaries: Dict[str, Any],
    max_jobs: int = 0,  # 0 = unlimited
) -> SqiPlan:
    """
    Deterministic GX1-local SQI fabric plan.
    NOTE: run_id is intentionally NOT used to avoid trace_digest changes when output_root/run_id differ.
    """
    scope_s = str(scope or "run")
    max_jobs_i = int(max_jobs) if int(max_jobs) >= 0 else 0

    scenario_ids = sorted([str(k) for k in (scenario_summaries or {}).keys()])

    # Deterministic inputs digest: stable, contract-relevant surfaces only (NO output_root/run_id)
    inputs_digest = stable_hash(
        {
            "seed": int(seed),
            "scope": scope_s,
            "scenario_ids": scenario_ids,
        }
    )

    jobs: List[Dict[str, Any]] = []
    # one “container job” per scenario for v0 (expand later)
    for sid in scenario_ids:
        jobs.append(
            {
                # Do NOT include run_id. Anchor to inputs_digest + sid.
                "container_id": f"gx1:sqi:{inputs_digest[:12]}:{sid}:job0",
                "op": "sqi_fabric_v0_qscore_stats",
                "inputs_ref": stable_hash({"scenario_id": sid}),
                "scenario_id": sid,
            }
        )

    # Deterministic cap (prefix truncation after stable sort)
    if max_jobs_i and len(jobs) > max_jobs_i:
        jobs = jobs[:max_jobs_i]

    # plan_id is a deterministic digest of the plan surface
    plan_id = _sha256(
        stable_stringify(
            {
                "schemaVersion": "GX1_SQI_PLAN_V0",
                "seed": int(seed),
                "scope": scope_s,
                "inputs_digest": inputs_digest,
                "jobs": jobs,
            }
        )
    )

    return {
        "schemaVersion": "GX1_SQI_PLAN_V0",
        "plan_id": plan_id,
        "seed": int(seed),
        "scope": scope_s,  # "run" | "scenario"
        "inputs_digest": inputs_digest,
        "jobs": jobs,
    }


def run_sqi_fabric_plan_local(
    *,
    plan: SqiPlan,
    scenario_summaries: Dict[str, Any],
    kg_write: bool = False,  # accepted for call-site compatibility; execution is optional
) -> SqiResult:
    """
    Deterministic local executor (V0):
    - uses already-derived deterministic series (rho_trace / qscore window)
    - produces stable-sorted results and KG write intents (digests only)

    kg_write is intentionally a no-op here (keep tests server-free);
    a later stage can execute KG writes behind an explicit interface.
    """
    _ = kg_write  # explicit no-op

    rows: List[Dict[str, Any]] = []
    kg_writes: List[Dict[str, Any]] = []

    jobs_sorted = sorted(
        list(plan.get("jobs") or []),
        key=lambda j: (str(j.get("scenario_id", "")), str(j.get("container_id", "")), str(j.get("op", ""))),
    )

    for job in jobs_sorted:
        sid = str(job.get("scenario_id", ""))
        s = (scenario_summaries or {}).get(sid, {}) if sid else {}

        series = list(s.get("rho_trace") or s.get("qscore_eval_window") or [])

        # Deterministic stats
        if series:
            xs = [float(x) for x in series]
            out = {
                "n": int(len(xs)),
                "mean": float(sum(xs) / len(xs)),
                "min": float(min(xs)),
                "max": float(max(xs)),
            }
        else:
            out = {"n": 0, "mean": 0.0, "min": 0.0, "max": 0.0}

        row = {
            "container_id": str(job.get("container_id", "")),
            "op": str(job.get("op", "")),
            "scenario_id": sid,
            "outputs": out,
            "metrics": {"outputs_digest": stable_hash(out)},
        }
        rows.append(row)

        # KG write INTENT (digest-only; actual KG write is a later optional stage)
        payload_digest = stable_hash({"plan_id": plan.get("plan_id", ""), "row": row})
        kg_writes.append(
            {
                "id": f"kg:{plan.get('plan_id','')}:{sid}",
                "kind": "node",
                "payload_digest": payload_digest,
            }
        )

    # Final stable sort (belt + suspenders)
    rows = sorted(rows, key=lambda r: (r.get("scenario_id", ""), r.get("container_id", ""), r.get("op", "")))
    kg_writes = sorted(kg_writes, key=lambda w: (w.get("id", ""), w.get("kind", "")))

    # ✅ export surfaces for replay bundle + tests
    kg_writes_jsonl = _kg_writes_jsonl(kg_writes)
    kg_writes_digest = _sha256(kg_writes_jsonl)

    return {
        "schemaVersion": "GX1_SQI_RESULT_V0",
        "plan_id": str(plan.get("plan_id", "")),
        "seed": int(plan.get("seed", 0)),
        "results": rows,
        "kg_writes": kg_writes,
        "kg_writes_count": int(len(kg_writes)),
        "kg_writes_digest": str(kg_writes_digest),
    }