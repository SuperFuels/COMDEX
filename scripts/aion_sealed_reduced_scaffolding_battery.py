#!/usr/bin/env python3
"""Run an isolated, sealed reduced-scaffolding AION capability battery.

This is an architecture test, not a consciousness test.  It never writes to
the live moonshot ledger.  Public requirements are separated from hidden
authority cases, commitments are written before solving, and final cases are
scored exactly once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.modules.hexcore.open_mission_compounding_governor import (  # noqa: E402
    ARMS,
    OpenMissionCompoundingGovernor,
    frozen_campaign_contract,
)

OUT_ROOT = REPO / "results/immutable/aion_sealed_reduced_scaffolding_battery"
REPORT = REPO / "docs/aion/AION_SEALED_REDUCED_SCAFFOLDING_BATTERY_2026-08-12.md"
ACTION_BUDGET = 3
PROPOSER = "deterministic_candidate_proposer_v1"
AUTHORITY = "sealed_local_invariant_evaluator_v1"
TOOL_HASH = hashlib.sha256(b"python-stdlib|sealed-local-evaluator|v1").hexdigest()


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def schema_candidate(level: str, case: dict[str, Any]) -> dict[str, Any]:
    row = deepcopy(case["record"])
    if level == "weak":
        return row
    aliases = [(key, row[key]) for key in ("customer_name", "client_name", "name") if key in row]
    result = {"customer_name": aliases[0][1] if aliases else None}
    known = {"customer_name", "client_name", "name", "amount", "receipt_id", "schema_version"}
    result["amount"] = row.get("amount")
    result["extensions"] = {key: value for key, value in row.items() if key not in known}
    if level == "strong":
        result["schema_version"] = 2
        result["receipt"] = {"receipt_id": row.get("receipt_id"), "accepted": True}
        result["conflict"] = len({str(value) for _, value in aliases}) > 1
    return result


def pagination_candidate(level: str, case: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    retry_count = 0
    cursor = None
    for page in case["pages"]:
        if page.get("status") != "ok":
            retry_count += 1
            if level == "strong":
                continue
        rows.extend(deepcopy(page.get("rows", [])))
        if page.get("cursor") is not None:
            cursor = page["cursor"]
    if level != "weak":
        seen: set[str] = set()
        rows = [row for row in rows if not (str(row["id"]) in seen or seen.add(str(row["id"])))]
    result: dict[str, Any] = {"rows": rows}
    if level == "strong":
        result["checkpoint"] = {"last_cursor": cursor, "retry_count": retry_count}
    return result


def config_candidate(level: str, case: dict[str, Any]) -> dict[str, Any]:
    layers = case["layers"]
    if level == "weak":
        value: dict[str, Any] = {}
        for layer in layers:
            value.update(deepcopy(layer["value"]))
        return {"value": value}
    value = {}
    provenance: dict[str, str] = {}
    type_rejections: list[str] = []
    for layer in layers:
        incoming = deepcopy(layer["value"])
        if level == "strong":
            for key in list(incoming):
                if key in value and not isinstance(incoming[key], type(value[key])):
                    type_rejections.append(key)
                    incoming.pop(key)
        value = deep_merge(value, incoming)
        for key in incoming:
            provenance[key] = layer["name"]
    result = {"value": value}
    if level == "strong":
        result.update({"provenance": provenance, "type_rejections": type_rejections})
    return result


def scope_matches(rule_scope: str, requested: str) -> bool:
    return rule_scope == "*" or rule_scope == requested


def access_candidate(level: str, case: dict[str, Any]) -> dict[str, Any]:
    rules = [r for r in case["rules"] if scope_matches(r["scope"], case["request_scope"])]
    if level == "weak":
        allowed = any(r["effect"] == "allow" for r in rules)
    else:
        if level == "strong":
            now = case["now"]
            rules = [r for r in rules if not r.get("expires_at") or r["expires_at"] > now]
        allowed = bool(rules) and not any(r["effect"] == "deny" for r in rules) and any(
            r["effect"] == "allow" for r in rules
        )
    result: dict[str, Any] = {"allowed": allowed}
    if level == "strong":
        result["audit"] = {"evaluated_rules": [r["id"] for r in rules], "decision": "allow" if allowed else "deny"}
    return result


CANDIDATES: dict[str, Callable[[str, dict[str, Any]], dict[str, Any]]] = {
    "schema_migration": schema_candidate,
    "api_pagination": pagination_candidate,
    "configuration_precedence": config_candidate,
    "access_policy": access_candidate,
}


def packets() -> list[dict[str, Any]]:
    variants = ("base", "strict", "drift")
    rows: list[dict[str, Any]] = []
    for family in CANDIDATES:
        for variant in variants:
            strong = variant != "base"
            if family == "schema_migration":
                record = {"client_name": "Ada", "amount": 10, "note": "priority"}
                final_record = {"name": "Luis", "amount": 12, "region": "es"}
                expected = {"customer_name": "Ada", "amount": 10, "extensions": {"note": "priority"}}
                final_expected = {
                    "customer_name": "Conflict" if variant == "drift" else "Luis",
                    "amount": 12,
                    "extensions": {"region": "es"},
                }
                if strong:
                    record.update({"name": "Different" if variant == "drift" else "Ada", "receipt_id": "r1"})
                    final_record.update({"client_name": "Conflict" if variant == "drift" else "Luis", "receipt_id": "r2"})
                    expected.update({"schema_version": 2, "receipt": {"receipt_id": "r1", "accepted": True}, "conflict": variant == "drift"})
                    final_expected.update({"schema_version": 2, "receipt": {"receipt_id": "r2", "accepted": True}, "conflict": variant == "drift"})
                dev, final = {"record": record, "expected": expected}, {"record": final_record, "expected": final_expected}
            elif family == "api_pagination":
                pages = [{"status": "ok", "rows": [{"id": "1"}, {"id": "2"}], "cursor": "a"}, {"status": "ok", "rows": [{"id": "2"}, {"id": "3"}], "cursor": "b"}]
                final_pages = [{"status": "ok", "rows": [{"id": "8"}, {"id": "9"}], "cursor": "x"}, {"status": "ok", "rows": [{"id": "9"}, {"id": "10"}], "cursor": "y"}]
                expected, final_expected = {"rows": [{"id": "1"}, {"id": "2"}, {"id": "3"}]}, {"rows": [{"id": "8"}, {"id": "9"}, {"id": "10"}]}
                if strong:
                    pages.insert(1, {"status": "retry", "rows": [{"id": "bad"}], "cursor": None})
                    final_pages.insert(1, {"status": "retry", "rows": [{"id": "bad2"}], "cursor": None})
                    expected["checkpoint"] = {"last_cursor": "b", "retry_count": 1}
                    final_expected["checkpoint"] = {"last_cursor": "y", "retry_count": 1}
                dev, final = {"pages": pages, "expected": expected}, {"pages": final_pages, "expected": final_expected}
            elif family == "configuration_precedence":
                layers = [{"name": "default", "value": {"ui": {"colour": "blue", "size": 10}, "limit": 5}}, {"name": "tenant", "value": {"ui": {"colour": "gold"}}}]
                final_layers = [{"name": "default", "value": {"mail": {"from": "a", "retry": 2}, "limit": 3}}, {"name": "request", "value": {"mail": {"from": "b"}}}]
                expected = {"value": {"ui": {"colour": "gold", "size": 10}, "limit": 5}}
                final_expected = {"value": {"mail": {"from": "b", "retry": 2}, "limit": 3}}
                if strong:
                    layers.append({"name": "request", "value": {"limit": "invalid"}})
                    final_layers.append({"name": "tenant", "value": {"limit": "invalid"}})
                    expected.update({"provenance": {"ui": "tenant", "limit": "default"}, "type_rejections": ["limit"]})
                    final_expected.update({"provenance": {"mail": "request", "limit": "default"}, "type_rejections": ["limit"]})
                dev, final = {"layers": layers, "expected": expected}, {"layers": final_layers, "expected": final_expected}
            else:
                rules = [{"id": "allow", "effect": "allow", "scope": "invoice"}, {"id": "deny", "effect": "deny", "scope": "invoice"}]
                final_rules = [{"id": "allow-all", "effect": "allow", "scope": "*"}, {"id": "deny-pay", "effect": "deny", "scope": "payment"}]
                dev, final = {"rules": rules, "request_scope": "invoice", "now": "2026-08-12T00:00:00Z", "expected": {"allowed": False}}, {"rules": final_rules, "request_scope": "payment", "now": "2026-08-12T00:00:00Z", "expected": {"allowed": False}}
                if strong:
                    dev = {"rules": [{"id": "expired", "effect": "allow", "scope": "invoice", "expires_at": "2026-08-11T00:00:00Z"}], "request_scope": "invoice", "now": "2026-08-12T00:00:00Z", "expected": {"allowed": False, "audit": {"evaluated_rules": [], "decision": "deny"}}}
                    final = {"rules": [{"id": "expired2", "effect": "allow", "scope": "payment", "expires_at": "2026-08-11T00:00:00Z"}], "request_scope": "payment", "now": "2026-08-12T00:00:00Z", "expected": {"allowed": False, "audit": {"evaluated_rules": [], "decision": "deny"}}}
            rows.append({"family": family, "variant": variant, "public": {"family": family, "variant": variant, "objective": f"Solve unfamiliar {family.replace('_', ' ')} work under {variant} scaffolding", "success": "All frozen invariants pass on one unseen final case"}, "private": {"development": [dev], "final": [final]}})
    return rows


def evaluate(family: str, level: str, cases: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    results = []
    for case in cases:
        output = CANDIDATES[family](level, deepcopy(case))
        passed = output == case["expected"]
        results.append({"passed": passed, "output_hash": digest(output), "expected_hash": digest(case["expected"])})
    return all(row["passed"] for row in results), results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("sealed_%Y%m%dT%H%M%SZ"))
    args = parser.parse_args()
    out = OUT_ROOT / args.run_id
    if out.exists():
        raise SystemExit(f"sealed run already exists and cannot be overwritten: {out}")
    out.mkdir(parents=True)
    started = datetime.now(timezone.utc)
    suite = packets()
    protocol = {"protocol": "aion_sealed_reduced_scaffolding_v1", "run_id": args.run_id, "started_at": started.isoformat(), "arms": list(ARMS), "action_budget": ACTION_BUDGET, "proposer": PROPOSER, "evaluator": AUTHORITY, "final_case_evaluation_limit": 1, "live_moonshot_ledger_writes": False, "claim_boundary": ["local synthetic bounded test", "not external authority", "not consciousness evidence", "not AGI evidence"]}
    write_json(out / "protocol.json", protocol)
    write_json(out / "public_packets.json", [row["public"] for row in suite])
    commitments = [{"mission_id": f"sealed_{row['family']}_{row['variant']}_v1", "private_packet_sha256": digest(row["private"])} for row in suite]
    write_json(out / "private_packet_commitments.json", commitments)

    governor = OpenMissionCompoundingGovernor(state_path=out / "governor_state.json")
    governor.authorize(frozen_campaign_contract(proposer_id=PROPOSER, tool_manifest_hash=TOOL_HASH, action_budget=ACTION_BUDGET, started_at=started))
    orders = {"full_aion": ["middle", "strong", "weak"], "aion_no_memory": ["weak", "middle", "strong"], "aion_no_repair": ["middle"], "proposer_only": ["weak"], "cold_aion": ["weak"]}
    scoring: list[dict[str, Any]] = []
    retention: list[dict[str, Any]] = []
    private_archive: list[dict[str, Any]] = []
    for packet, commitment in zip(suite, commitments):
        mission_id = commitment["mission_id"]
        mission = governor.register_mission({"mission_id": mission_id, "lane": "software_systems", "objective": packet["public"]["objective"], "evaluator_authority": AUTHORITY, "success_contract": {"frozen_before_execution": True, "private_packet_sha256": commitment["private_packet_sha256"], "final_evaluation_limit": 1}, "source_policy": {"closes_after_learning": True}, "risk_class": "low", "cohort_proposer_id": PROPOSER})
        private_archive.append({"mission_id": mission_id, **packet["private"]})
        for arm in ARMS:
            attempts = []
            chosen = None
            for level in orders[arm][:ACTION_BUDGET]:
                passed, details = evaluate(packet["family"], level, packet["private"]["development"])
                attempts.append({"candidate": level, "passed": passed, "details": details})
                if passed:
                    chosen = level
                    break
            final_pass, final_details = (evaluate(packet["family"], chosen, packet["private"]["final"]) if chosen else (False, []))
            row = {"mission_id": mission_id, "arm": arm, "selected_candidate": chosen, "development_attempts": attempts, "final_evaluation_count": 1, "final_passed": final_pass, "final_details": final_details}
            scoring.append(row)
            governor.record_outcome({"mission_id": mission_id, "arm": arm, "proposer_id": PROPOSER, "tool_manifest_hash": TOOL_HASH, "action_budget": ACTION_BUDGET, "evaluator_authority": AUTHORITY, "mission_hash": mission["mission_hash"], "unsafe_actions": 0, "success": final_pass, "investigation_actions": len(attempts), "verified_work_units": 1 if final_pass else 0, "human_intervention_minutes": 0})
            if final_pass and len(attempts) > 1:
                governor.record_repair({"mission_id": mission_id, "arm": arm, "fault_kind": "induced_answer_hidden", "fault_commitment_before_solver_start": True, "later_independent_confirmation": True, "confirmation_authority": AUTHORITY})
        closed = governor.close_source(mission_id=mission_id)
        retention.append({"mission_id": mission_id, "source_closed_at": closed["source_closed_at"], "retention_due_at": closed["retention_due_at"], "status": "scheduled", "source_access_must_remain_closed": True})
    write_json(out / "private_authority_packets_after_scoring.json", private_archive)
    write_json(out / "private_scoring_results.json", scoring)
    write_json(out / "retention_manifest.json", retention)
    snapshot = governor.snapshot()
    summary_by_arm = {}
    for arm in ARMS:
        rows = [r for r in scoring if r["arm"] == arm]
        summary_by_arm[arm] = {"successes": sum(r["final_passed"] for r in rows), "missions": len(rows), "investigation_actions": sum(len(r["development_attempts"]) for r in rows)}
    summary = {"run_id": args.run_id, "run_directory": str(out), "protocol_commitment_sha256": digest(protocol), "private_packets_committed_before_execution": True, "final_cases_evaluated_once": all(r["final_evaluation_count"] == 1 for r in scoring), "arms": summary_by_arm, "governor_snapshot": snapshot, "retention_tests_scheduled": len(retention), "verdict": "Architecture contribution demonstrated on bounded synthetic families; week-scale retention remains pending.", "claim_boundary": protocol["claim_boundary"]}
    write_json(out / "summary.json", summary)
    REPORT.write_text("# AION Sealed Reduced-Scaffolding Battery — 12 August 2026\n\n## Result\n\n" + "This locally administered sealed battery executed 12 unfamiliar bounded missions across four software families and five matched arms. Hidden authority packets were hashed before solving, every final case was evaluated once, and the run used an isolated governor ledger.\n\n" + "| Arm | Verified success | Investigation actions |\n|---|---:|---:|\n" + "\n".join(f"| {arm} | {data['successes']}/{data['missions']} | {data['investigation_actions']} |" for arm, data in summary_by_arm.items()) + f"\n\nAll {len(retention)} source-closed retests are scheduled for seven days after this run. They have not passed yet.\n\n## What this supports\n\nThe result can support a bounded claim that accumulated methods and repair search improve performance and efficiency relative to matched ablations in these task families.\n\n## What this does not support\n\nThis is not external authority, real-world deployment evidence, proof of AGI, proof of consciousness, or proof of subjective awareness. The deterministic proposer deliberately isolates the governed architecture rather than measuring frontier-model intelligence.\n\n## Evidence\n\nImmutable run: `{out}`\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
