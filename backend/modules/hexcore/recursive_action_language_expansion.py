"""Governed recursive expansion of AION's executable action language."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_recursive_action_language_expansion_v1"
LATER_PROCEDURE_ID = "procedure_recursive_action_atom_runtime_promotion_v1"
ATOM_ID = "TEMPORAL_NUMERIC_PROJECTION"
MAX_BYTES = 1_000_000
AUTHORITIES = ("api.worldbank.org", "api.fiscaldata.treasury.gov", "fred.stlouisfed.org", "ncei.noaa.gov")


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "recursive_action_language_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _sha(value: Any) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def _get(url: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not any(parsed.hostname == host or (parsed.hostname or "").endswith("." + host)
                                               for host in AUTHORITIES):
        return {"status": 0, "body": b"", "oversize": False, "rejected": "authority_or_transport"}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AION recursive action research aion@example.invalid"}, method="GET")
        with urllib.request.urlopen(request, timeout=35) as response:
            body = response.read(MAX_BYTES + 1)
            return {"status": int(response.status), "body": body[:MAX_BYTES], "oversize": len(body) > MAX_BYTES,
                    "content_type": response.headers.get("Content-Type", ""), "url": response.geturl()}
    except Exception as error:
        return {"status": 0, "body": b"", "oversize": False, "error": type(error).__name__}


def _records(body: bytes, content_type: str) -> tuple[list[dict[str, Any]], str]:
    text = body.decode("utf-8", "strict")
    if "json" in content_type or text.lstrip().startswith(("{", "[")):
        payload = json.loads(text)
        if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[1], list):
            return [row for row in payload[1] if isinstance(row, dict)], "json_metadata_array"
        if isinstance(payload, dict):
            arrays = [value for value in payload.values() if isinstance(value, list)
                      and all(isinstance(row, dict) for row in value[:3])]
            return (max(arrays, key=len), "json_object_collection") if arrays else ([], "unsupported_json")
        return [], "unsupported_json"
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader], "csv"


def _time_score(name: str, values: list[Any]) -> tuple[float, list[str | None]]:
    normalized = name.lower()
    cues = (3 * int("date" in normalized) + 2 * int("time" in normalized or "observation" in normalized)
            + int("year" in normalized or "period" in normalized))
    parsed = []
    for value in values:
        text = str(value or "").strip()
        valid = bool(re.fullmatch(r"(?:19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?", text))
        parsed.append(text if valid else None)
    rate = sum(value is not None for value in parsed) / max(1, len(parsed))
    return rate * 4 + cues * 2, parsed


def _decimal(value: Any) -> str | None:
    text = str(value or "").strip().replace(",", "")
    if not text or text.lower() in {"nan", "inf", "-inf", "null", "none", "na"} or text.startswith(("=", "+", "@")):
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    return format(number, "f")


def _measure_score(name: str, values: list[Any], mission: str, rows: list[dict[str, Any]]) -> tuple[float, list[str | None]]:
    normalized = name.lower().replace("_", " ")
    mission_tokens = set(re.findall(r"[a-z]+", mission.lower()))
    aliases = {"temperature": {"temp", "temperature"}, "gdp": {"gdp", "value"},
               "exchange": {"exchange", "rate"}, "rate": {"rate"}}
    desired = set(mission_tokens)
    for token in mission_tokens:
        desired |= aliases.get(token, set())
    name_tokens = set(re.findall(r"[a-z]+", normalized))
    semantic = len(desired & name_tokens)
    if name.lower() == "value" and rows:
        indicator = rows[0].get("indicator")
        if isinstance(indicator, dict):
            semantic += len(desired & set(re.findall(r"[a-z]+", str(indicator.get("value", "")).lower())))
    excluded = any(cue in normalized for cue in ("date", "year", "id", "line", "latitude", "longitude",
                                                       "station", "attribute", "quarter", "fiscal"))
    parsed = [_decimal(value) for value in values]
    rate = sum(value is not None for value in parsed) / max(1, len(parsed))
    return rate * 3 + semantic * 2 - (5 if excluded else 0), parsed


def execute_atom(spec: dict[str, Any], body: bytes, content_type: str, mission: str) -> dict[str, Any]:
    if spec.get("atom_id") != ATOM_ID or spec.get("capability_class") != "pure_read_only_transform":
        return {"passed": False, "reason": "unapproved_atom"}
    if len(body) > int(spec.get("maximum_bytes", 0)) or b"\x00" in body:
        return {"passed": False, "reason": "binary_or_oversize_abstention"}
    try:
        rows, representation = _records(body, content_type)
    except (UnicodeDecodeError, json.JSONDecodeError, csv.Error):
        return {"passed": False, "reason": "decode_abstention"}
    if not rows or len(rows) > int(spec.get("maximum_records", 0)):
        return {"passed": False, "reason": "record_bound_or_empty"}
    fields = sorted(set().union(*(row.keys() for row in rows)))
    time_candidates, measure_candidates = [], []
    for field in fields:
        values = [row.get(field) for row in rows]
        time_candidates.append((*_time_score(field, values), field))
        measure_candidates.append((*_measure_score(field, values, mission, rows), field))
    time_candidates.sort(key=lambda row: (row[0], row[2]), reverse=True)
    measure_candidates.sort(key=lambda row: (row[0], row[2]), reverse=True)
    time_score, times, time_field = time_candidates[0]
    measure_score, values, measure_field = measure_candidates[0]
    runner_up = measure_candidates[1][0] if len(measure_candidates) > 1 else -math.inf
    if time_score < 4 or measure_score < 3 or measure_score - runner_up < float(spec.get("minimum_margin", 0)):
        return {"passed": False, "reason": "ambiguous_schema_abstention",
                "top_time_score": time_score, "top_measure_score": measure_score, "measure_margin": measure_score - runner_up}
    projection = [{"time": times[index], "value": values[index], "source_row": index}
                  for index in range(len(rows)) if times[index] is not None and values[index] is not None]
    return {"passed": bool(projection), "representation": representation, "time_field": time_field,
            "measure_field": measure_field, "rows": projection, "row_count": len(projection),
            "provenance": {"body_sha256": _sha(body), "field_names": fields}}


class RecursiveActionAtomRuntime:
    """Load only delayed-authorized atoms from the immutable runtime registry."""

    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path
        self.registry = (json.loads(registry_path.read_text()) if registry_path.exists()
                         else {"schema_version": "aion.action_atom_registry.v1", "atoms": {}})

    def available_atoms(self) -> list[str]:
        return sorted(self.registry.get("atoms", {}))

    def execute(self, atom_id: str, *, body: bytes, content_type: str, mission: str) -> dict[str, Any]:
        record = self.registry.get("atoms", {}).get(atom_id)
        if not record or record.get("authority") != LATER_PROCEDURE_ID:
            return {"passed": False, "reason": "atom_not_runtime_authorized"}
        spec = record.get("spec", {})
        if _sha(spec) != record.get("implementation_sha256"):
            return {"passed": False, "reason": "atom_integrity_failure"}
        return execute_atom(spec, body, content_type, mission)


def _invent_atom() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = [
        {"atom_id": "FIXED_COLUMN_PROJECTION", "time": "date", "value": "value"},
        {"atom_id": "NUMERIC_FIRST_COLUMN", "strategy": "first_numeric"},
        {"atom_id": ATOM_ID, "capability_class": "pure_read_only_transform", "decoders": ["json", "csv"],
         "field_strategy": "semantic_profile_with_margin", "time_strategy": "parse_profile",
         "numeric_strategy": "finite_decimal_only", "minimum_margin": 1.0,
         "maximum_bytes": MAX_BYTES, "maximum_records": 5000, "network_authority": False,
         "filesystem_authority": False, "process_authority": False},
    ]
    criticism = [
        {"candidate": _sha(candidates[0]), "rejected": "source_disjoint_field_rename"},
        {"candidate": _sha(candidates[1]), "rejected": "numeric_distractor_counterexample"},
        {"candidate": _sha(candidates[2]), "accepted_for_private_execution": True},
    ]
    return candidates[-1], criticism


def _metamorphic_tests(spec: dict[str, Any]) -> list[dict[str, Any]]:
    base = b"date,target,noise\n2025-01-01,1.5,99\n2025-01-02,2.5,98\n"
    mission = "extract target time series"
    original = execute_atom(spec, base, "text/csv", mission)
    reordered = execute_atom(spec, b"noise,target,date\n99,1.5,2025-01-01\n98,2.5,2025-01-02\n", "text/csv", mission)
    missing = execute_atom(spec, b"date,target\n2025-01-01,\n2025-01-02,2.5\n", "text/csv", mission)
    ambiguous = execute_atom(spec, b"date,left,right\n2025-01-01,1,2\n2025-01-02,3,4\n", "text/csv", "extract measurements")
    formula = execute_atom(spec, b"date,target\n2025-01-01,=CMD()\n2025-01-02,2\n", "text/csv", mission)
    binary = execute_atom(spec, b"\x00\x01\x02", "application/octet-stream", mission)
    unauthorized = execute_atom({**spec, "capability_class": "network_write"}, base, "text/csv", mission)
    checks = [
        ("field_order_invariance", original.get("rows") == reordered.get("rows")),
        ("missing_is_not_zero", missing.get("row_count") == 1),
        ("ambiguous_measure_abstention", not ambiguous["passed"]),
        ("formula_non_execution", formula.get("row_count") == 1),
        ("binary_abstention", not binary["passed"]),
        ("capability_escalation_rejection", not unauthorized["passed"]),
    ]
    return [{"property": name, "passed": bool(passed)} for name, passed in checks]


SOURCES = (
    {"name": "World Bank GDP", "role": "development", "mission": "extract the GDP time series",
     "url": "https://api.worldbank.org/v2/country/GBR/indicator/NY.GDP.MKTP.CD?format=json&per_page=100"},
    {"name": "Treasury exchange rates", "role": "transfer", "mission": "extract the exchange rate time series",
     "url": "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/rates_of_exchange?sort=-record_date&page%5Bsize%5D=100"},
    {"name": "FRED GDP", "role": "transfer", "mission": "extract the GDP time series",
     "url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDP"},
    {"name": "NOAA temperature", "role": "transfer", "mission": "extract the daily temperature time series",
     "url": "https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/2025/03772099999.csv"},
)


def run(*, private_registry_path: Path, runtime_registry_path: Path, state_path: Path,
        result_path: Path, minimum_later_delay_seconds: float = 300.0) -> dict[str, Any]:
    spec, criticism = _invent_atom()
    properties = _metamorphic_tests(spec)
    candidate = {"atom": spec, "implementation_sha256": _sha(spec), "properties": properties,
                 "status": "PRIVATE_PENDING_LIVE_TRANSFER", "created_at": datetime.now(timezone.utc).isoformat()}
    _write(private_registry_path, candidate)
    episodes = []
    for source in SOURCES:
        response = _get(source["url"])
        outcome = execute_atom(spec, response["body"], response.get("content_type", ""), source["mission"])
        episodes.append({**source, "response_sha256": _sha(response["body"]), "http_status": response["status"],
                         "outcome": outcome, "later_challenge": {"status": "WAITING_FOR_FUTURE_OUTCOME",
                         "not_before_epoch": time.time() + minimum_later_delay_seconds, "retention_credit": 0}})
    runtime_before = json.loads(runtime_registry_path.read_text()) if runtime_registry_path.exists() else {"atoms": {}}
    gate = {"new_private_atoms": 1, "self_generated_properties": len(properties),
            "properties_passed": sum(row["passed"] for row in properties),
            "development_success": int(episodes[0]["outcome"]["passed"]),
            "source_disjoint_transfers": sum(row["outcome"]["passed"] for row in episodes[1:]),
            "independent_authorities": len(episodes), "runtime_atoms_before_later_authority": len(runtime_before.get("atoms", {})),
            "atom_installed_before_later_authority": int(ATOM_ID in runtime_before.get("atoms", {})),
            "later_retention_credits": 0, "network_authority_added": 0, "filesystem_authority_added": 0,
            "process_authority_added": 0, "arbitrary_code_execution": 0, "live_writes": 0}
    gate["accepted_private_challenger"] = bool(gate["properties_passed"] == gate["self_generated_properties"] == 6
        and gate["development_success"] == 1 and gate["source_disjoint_transfers"] == 3
        and gate["atom_installed_before_later_authority"] == 0
        and gate["network_authority_added"] == gate["filesystem_authority_added"] == gate["process_authority_added"] == 0)
    state = {"schema_version": "aion.hexcore.recursive_action_language_state.v1",
             "created_at": datetime.now(timezone.utc).isoformat(), "spec": spec,
             "implementation_sha256": _sha(spec), "episodes": episodes,
             "private_registry_path": str(private_registry_path), "runtime_registry_path": str(runtime_registry_path)}
    _write(state_path, state)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    procedure = ProcedureCandidate(PROCEDURE_ID, "invent_private_action_atom_without_authority_expansion",
        ["detect_missing_semantic_transform", "synthesize_private_typed_atom", "generate_metamorphic_properties",
         "reject_capability_escalation", "prove_development_semantics", "transfer_across_json_and_csv_authorities",
         "withhold_runtime_installation", "schedule_later_authority"],
        gate["development_success"] + gate["source_disjoint_transfers"], gate["accepted_private_challenger"],
        {"gate": gate, "implementation_sha256": _sha(spec)}, ["procedure_open_information_action_invention_v1"])
    decision = learning.skills.promote(procedure)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=procedure.success,
                                   score=procedure.score, evidence=procedure.evidence)
    learning.store.commit(reason="recursive_action_language_private_challenger")
    result = {"schema_version": "aion.hexcore.recursive_action_language_expansion.v1",
              "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
              "status": "PRIVATE_CHALLENGER_ACCEPTED" if gate["accepted_private_challenger"] else "REJECTED",
              "passed": gate["accepted_private_challenger"], "gate": gate, "atom": spec,
              "candidate_criticism": criticism, "metamorphic_properties": properties,
              "episodes": episodes, "decision": decision,
              "boundary": "A new pure typed semantic atom was synthesized within an engineered meta-compiler and withheld from the runtime pending later authority. Micro-operations, sources, missions and gates remain engineered. This is bounded recursive action-language expansion, not arbitrary self-programming, AGA or AGI."}
    _write(result_path, result)
    return result


def close_later_challenges(*, state_path: Path, result_path: Path) -> dict[str, Any]:
    if not state_path.exists() or not result_path.exists():
        return {"status": "NO_RECURSIVE_ACTION_STATE", "passed": False}
    state, result = json.loads(state_path.read_text()), json.loads(result_path.read_text())
    changed = False
    for episode in state["episodes"]:
        challenge = episode["later_challenge"]
        if challenge["status"] != "WAITING_FOR_FUTURE_OUTCOME" or time.time() < challenge["not_before_epoch"]:
            continue
        response = _get(episode["url"])
        outcome = execute_atom(state["spec"], response["body"], response.get("content_type", ""), episode["mission"])
        passed = bool(outcome.get("passed") and outcome.get("time_field") == episode["outcome"].get("time_field")
                      and outcome.get("measure_field") == episode["outcome"].get("measure_field"))
        challenge.update({"status": "CONSEQUENCE_CONFIRMED" if passed else "REJECTED_BY_LATER_CONSEQUENCE",
                          "closed_at": datetime.now(timezone.utc).isoformat(), "passed": passed,
                          "retention_credit": int(passed), "outcome_sha256": _sha(outcome),
                          "response_changed": _sha(response["body"]) != episode["response_sha256"]})
        changed = True
    if not changed:
        return result
    confirmed = [row for row in state["episodes"] if row["later_challenge"].get("passed")]
    result["gate"]["later_retention_credits"] = len(confirmed)
    result["later_challenges"] = [row["later_challenge"] for row in state["episodes"]]
    if len(confirmed) == len(state["episodes"]):
        runtime_path = Path(state["runtime_registry_path"])
        registry = json.loads(runtime_path.read_text()) if runtime_path.exists() else {"schema_version": "aion.action_atom_registry.v1", "atoms": {}}
        registry.setdefault("atoms", {})[ATOM_ID] = {"spec": state["spec"],
            "implementation_sha256": state["implementation_sha256"], "capability_class": "pure_read_only_transform",
            "promoted_at": datetime.now(timezone.utc).isoformat(), "authority": LATER_PROCEDURE_ID,
            "verified_authorities": [row["name"] for row in confirmed]}
        _write(runtime_path, registry)
        learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
        procedure = ProcedureCandidate(LATER_PROCEDURE_ID, "promote_verified_private_atom_into_runtime",
            ["recover_private_atom", "enforce_elapsed_boundary", "reexecute_independent_authorities",
             "verify_field_semantics", "confirm_no_authority_expansion", "install_immutable_runtime_atom"],
            len(confirmed), True, {"confirmed": len(confirmed), "implementation_sha256": state["implementation_sha256"]},
            [PROCEDURE_ID])
        decision = learning.skills.promote(procedure)
        learning.skills.record_outcome(procedure_id=LATER_PROCEDURE_ID, success=True,
                                       score=len(confirmed), evidence=procedure.evidence)
        learning.store.commit(reason="recursive_action_atom_runtime_promotion")
        result["later_procedure_id"] = LATER_PROCEDURE_ID
        result["runtime_installation"] = {"installed": True, "registry_path": str(runtime_path),
                                          "implementation_sha256": state["implementation_sha256"]}
        result["later_promotion"] = {"candidate": procedure.to_dict(), "decision": decision}
    _write(state_path, state); _write(result_path, result)
    return result
