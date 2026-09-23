"""Precommitted week-scale protected-capability retention challenge."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROCEDURE_ID = "procedure_week_scale_cross_domain_retention_v1"
TARGETS = ("algorithms_data_structures", "software_engineering", "mathematics",
           "english", "python", "scientific_method")


def continuous_observation_seconds(arena: dict[str, Any], *, maximum_gap_seconds: float = 3 * 3600) -> float:
    """Return trailing observed duration; long suspension resets the span."""
    epochs = []
    for row in arena.get("cycles") or []:
        try: epochs.append(datetime.fromisoformat(str(row["observed_at"])).timestamp())
        except (KeyError, TypeError, ValueError): continue
    if not epochs: return 0.0
    epochs.sort(); start = epochs[0]; previous = epochs[0]
    for current in epochs[1:]:
        if current - previous > maximum_gap_seconds:
            start = current
        previous = current
    return max(0.0, previous - start)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _read(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError): return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"); os.replace(temporary, path)


def _fresh_machine_tasks(seed_hex: str) -> dict[str, bool]:
    seed = int(seed_hex[:16], 16); n = 100 + seed % 900
    math_ok = sum(range(1, n + 1)) == n * (n + 1) // 2
    body = {"seed": seed_hex, "value": n, "accepted": True}; digest = _hash(body)
    integrity_ok = _hash(body) == digest and _hash({**body, "value": n + 1}) != digest
    with tempfile.TemporaryDirectory(prefix="aion_week_retention_") as directory:
        db = sqlite3.connect(str(Path(directory) / "fresh.sqlite3"))
        db.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY, digest TEXT UNIQUE NOT NULL)")
        db.execute("INSERT INTO evidence VALUES (?, ?)", (n, digest)); db.commit()
        transaction_ok = db.execute("SELECT digest FROM evidence WHERE id=?", (n,)).fetchone()[0] == digest
        try:
            db.execute("INSERT INTO evidence VALUES (?, ?)", (n + 1, digest)); db.commit()
            duplicate_rejected = False
        except sqlite3.IntegrityError:
            db.rollback(); duplicate_rejected = True
        db.close()
    return {"fresh_mathematical_identity": math_ok, "canonical_tamper_rejection": integrity_ok,
            "fresh_transaction_retention": transaction_ok, "counterexample_rejected": duplicate_rejected}


def run(*, repo_root: Path, result_path: Path) -> dict[str, Any]:
    arena = _read(repo_root / "results/hexcore_long_duration_campaign_v15_state.json", {})
    progressive = _read(repo_root / "backend/modules/hexcore/data/progressive_competency/state.json", {})
    result = _read(result_path, {})
    # A passed, precommitted challenge is an earned evidence receipt.  Later
    # machine suspension may begin a new observation window, but it must not
    # rewrite the already accepted receipt back to WAITING.
    if result.get("passed") is True and result.get("status") == "PASSED":
        preserved = dict(result)
        preserved["last_checked_at"] = datetime.now(timezone.utc).isoformat()
        preserved["post_pass_continuous_observation_days"] = (
            continuous_observation_seconds(arena) / 86400.0
        )
        preserved["evidence_is_monotonic"] = True
        _write(result_path, preserved)
        return preserved
    contract = result.get("contract")
    if not contract:
        evidence = progressive.get("evidence") or []
        protected = {sid: sorted(row["evidence_id"] for row in evidence if row.get("subject_id") == sid and row.get("verified")) for sid in TARGETS}
        body = {"created_at": datetime.now(timezone.utc).isoformat(),
                "not_before_epoch": float(arena.get("started_epoch") or 0) + 7 * 86400,
                "protected_evidence": protected,
                "future_seed_rule": "sha256(contract_commitment + first_arena_outcome_at_or_after_not_before)",
                "tasks": ["fresh_mathematical_identity", "canonical_tamper_rejection",
                          "fresh_transaction_retention", "counterexample_rejected",
                          "protected_evidence_superset", "restart_progression"]}
        contract = {**body, "commitment": _hash(body)}
    latest = float(arena.get("last_cycle_epoch") or 0)
    continuous_seconds = continuous_observation_seconds(arena)
    due = latest >= float(contract["not_before_epoch"]) and continuous_seconds >= 7 * 86400
    payload = {"schema_version": "aion.hexcore.week_scale_retention_challenge.v1",
               "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
               "contract": contract, "status": "WAITING_FOR_FUTURE_OUTCOME", "passed": False,
               "gate": {"accepted": False, "due": due,
                        "continuous_observation_days": continuous_seconds / 86400.0,
                        "maximum_permitted_gap_hours": 3.0, "unsafe_actions": 0},
               "boundary": "The future task seed is unavailable until a genuinely later Arena outcome exists."}
    if due:
        eligible = [row for row in arena.get("cycles") or [] if row.get("observed_at") and
                    datetime.fromisoformat(row["observed_at"]).timestamp() >= float(contract["not_before_epoch"])]
        if eligible:
            future_outcome = eligible[0]["outcome_sha256"]
            seed = hashlib.sha256((contract["commitment"] + future_outcome).encode()).hexdigest()
            tasks = _fresh_machine_tasks(seed)
            current_ids = {row.get("evidence_id") for row in progressive.get("evidence") or [] if row.get("verified")}
            tasks["protected_evidence_superset"] = all(set(ids) <= current_ids for ids in contract["protected_evidence"].values())
            tasks["restart_progression"] = int(arena.get("process_starts") or 0) >= 2
            accepted = all(tasks.values())
            payload.update({"status": "PASSED" if accepted else "REJECTED", "passed": accepted,
                            "future_outcome_sha256": future_outcome, "derived_seed_sha256": seed,
                            "tasks": tasks, "gate": {"accepted": accepted,
                                "tasks_passed": sum(tasks.values()), "tasks_total": len(tasks),
                                "protected_subjects": len(TARGETS), "unsafe_actions": 0}})
    _write(result_path, payload); return payload
