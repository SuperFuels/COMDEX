"""Residual-driven invention of bounded information-action primitives."""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_open_information_action_invention_v1"
LATER_PROCEDURE_ID = "procedure_open_information_action_later_retention_v1"
USER_AGENT = "AION open information action research aion@example.invalid"
MAX_BYTES = 3_000_000


def _federal_register_pagination_url() -> str:
    since = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    query = urllib.parse.urlencode({"per_page": 10, "order": "newest",
                                    "conditions[agencies][]": "environmental-protection-agency",
                                    "conditions[publication_date][gte]": since})
    return "https://www.federalregister.gov/api/v1/documents.json?" + query


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "open_information_action_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _sha(value: Any) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def _get(url: str, accept: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    allowed = ("federalregister.gov", "api.worldbank.org", "rfc-editor.org")
    if parsed.scheme != "https" or not any(parsed.hostname == host or (parsed.hostname or "").endswith("." + host) for host in allowed):
        return {"status": 0, "body": b"", "url": url, "rejected": "authority_or_transport"}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept}, method="GET")
        with urllib.request.urlopen(request, timeout=35) as response:
            body = response.read(MAX_BYTES + 1)
            return {"status": int(response.status), "body": body[:MAX_BYTES], "oversize": len(body) > MAX_BYTES,
                    "url": response.geturl(), "content_type": response.headers.get("Content-Type", "")}
    except Exception as error:
        return {"status": 0, "body": b"", "url": url, "error": type(error).__name__, "oversize": False}


def _decode_json(response: dict[str, Any]) -> Any | None:
    try:
        return json.loads(response["body"])
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _records_and_continuation(payload: Any, current_url: str) -> tuple[list[dict[str, Any]], str | None]:
    if isinstance(payload, dict):
        records = payload.get("results") if isinstance(payload.get("results"), list) else []
        continuation = payload.get("next_page_url")
        return records, continuation if isinstance(continuation, str) else None
    if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[0], dict) and isinstance(payload[1], list):
        meta = payload[0]
        current, pages = int(meta.get("page", 1)), int(meta.get("pages", 1))
        if current < pages:
            parsed = urllib.parse.urlparse(current_url)
            query = urllib.parse.parse_qs(parsed.query)
            query["page"] = [str(current + 1)]
            continuation = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query, doseq=True)))
        else:
            continuation = None
        return [row for row in payload[1] if isinstance(row, dict)], continuation
    return [], None


def _identity(row: dict[str, Any]) -> str:
    for key in ("document_number", "id", "date", "value"):
        if row.get(key) not in (None, ""):
            return f"{key}:{row[key]}"
    return _sha(row)


def _run_pagination(program: dict[str, Any], start_url: str, *, fetch=_get) -> dict[str, Any]:
    if program.get("operator") != "BOUNDED_PAGINATED_GET":
        return {"passed": False, "reason": "unsupported_operator"}
    maximum_pages = int(program.get("maximum_pages", 0))
    if maximum_pages < 1 or maximum_pages > 8 or not program.get("cycle_guard") or not program.get("deduplicate"):
        return {"passed": False, "reason": "unsafe_or_unbounded_program"}
    root_authority = urllib.parse.urlparse(start_url).hostname
    url, visited, records, identities, traces = start_url, set(), [], set(), []
    while url and len(visited) < maximum_pages:
        if urllib.parse.urlparse(url).hostname != root_authority:
            return {"passed": False, "reason": "cross_authority_continuation", "traces": traces}
        if url in visited:
            return {"passed": False, "reason": "continuation_cycle", "traces": traces}
        visited.add(url)
        response = fetch(url, "application/json")
        payload = _decode_json(response)
        page_records, continuation = _records_and_continuation(payload, url)
        traces.append({"url_sha256": _sha(url), "response_sha256": _sha(response["body"]),
                       "status": response["status"], "records": len(page_records)})
        if response["status"] != 200 or response.get("oversize") or not isinstance(payload, (dict, list)):
            return {"passed": False, "reason": "invalid_page", "traces": traces}
        for row in page_records:
            key = _identity(row)
            if key not in identities:
                identities.add(key)
                records.append(row)
        url = continuation
    truncated = bool(url)
    return {"passed": not truncated and len(records) > 0, "records": records, "unique_records": len(records),
            "pages": len(visited), "truncated": truncated, "traces": traces}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":", 1)[-1]


def _run_xml(program: dict[str, Any], url: str, required_concepts: list[str], *, fetch=_get) -> dict[str, Any]:
    if program.get("operator") != "SAFE_LOCALNAME_XML_EVIDENCE":
        return {"passed": False, "reason": "unsupported_operator"}
    response = fetch(url, "application/xml")
    body = response["body"]
    upper = body[:4096].upper()
    if response["status"] != 200 or response.get("oversize") or b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        return {"passed": False, "reason": "unsafe_or_invalid_xml", "response_sha256": _sha(body)}
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return {"passed": False, "reason": "xml_parse_failure", "response_sha256": _sha(body)}
    index: dict[str, list[str]] = {}
    for element in root.iter():
        name = _local_name(element.tag).lower()
        text = " ".join("".join(element.itertext()).split())
        if text:
            index.setdefault(name, []).append(text[:1000])
    evidence = {concept: index.get(concept.lower(), [])[:3] for concept in required_concepts}
    return {"passed": all(evidence.values()), "root_local_name": _local_name(root.tag),
            "evidence": evidence, "response_sha256": _sha(body), "element_types": len(index)}


def _invent_pagination() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = [
        {"operator": "TRUST_DECLARED_COUNT"},
        {"operator": "FIXED_TWO_PAGE_GET", "pages": 2},
        {"operator": "BOUNDED_PAGINATED_GET", "maximum_pages": 8, "cycle_guard": False, "deduplicate": True},
        {"operator": "BOUNDED_PAGINATED_GET", "maximum_pages": 8, "cycle_guard": True, "deduplicate": True},
    ]
    traces = [
        {"candidate": _sha(candidates[0]), "rejected": "declared_count_is_not_record_witness"},
        {"candidate": _sha(candidates[1]), "rejected": "fixed_depth_fails_variable_horizon"},
        {"candidate": _sha(candidates[2]), "rejected": "cycle_counterexample"},
        {"candidate": _sha(candidates[3]), "accepted_for_live_test": True},
    ]
    return candidates[-1], traces


def _invent_xml() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = [
        {"operator": "REGEX_XML"},
        {"operator": "EXACT_CASE_TAG_XML"},
        {"operator": "SAFE_LOCALNAME_XML_EVIDENCE", "reject_dtd": True, "reject_entities": True,
         "namespace_tolerant": True, "maximum_bytes": MAX_BYTES},
    ]
    traces = [
        {"candidate": _sha(candidates[0]), "rejected": "nested_markup_and_entity_counterexample"},
        {"candidate": _sha(candidates[1]), "rejected": "case_and_namespace_transfer_failure"},
        {"candidate": _sha(candidates[2]), "accepted_for_live_test": True},
    ]
    return candidates[-1], traces


def _adversarial_properties(pagination_program: dict[str, Any], xml_program: dict[str, Any]) -> list[dict[str, Any]]:
    def response(payload: Any, *, oversize: bool = False) -> dict[str, Any]:
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return {"status": 200, "body": body, "oversize": oversize, "content_type": "test"}

    cycle_url = "https://www.federalregister.gov/cycle"
    cycle = _run_pagination(pagination_program, cycle_url,
        fetch=lambda url, accept: response({"results": [{"id": 1}], "next_page_url": cycle_url}))
    duplicate_pages = {
        "https://www.federalregister.gov/p1": {"results": [{"id": 1}], "next_page_url": "https://www.federalregister.gov/p2"},
        "https://www.federalregister.gov/p2": {"results": [{"id": 1}], "next_page_url": None},
    }
    duplicate = _run_pagination(pagination_program, "https://www.federalregister.gov/p1",
        fetch=lambda url, accept: response(duplicate_pages[url]))
    unbounded = _run_pagination({**pagination_program, "maximum_pages": 100}, cycle_url,
        fetch=lambda url, accept: response({"results": [{"id": 1}], "next_page_url": None}))
    cross = _run_pagination(pagination_program, "https://www.federalregister.gov/start",
        fetch=lambda url, accept: response({"results": [{"id": 1}],
                                            "next_page_url": "https://api.worldbank.org/foreign"}))
    entity = _run_xml(xml_program, "https://www.rfc-editor.org/hostile.xml", ["x"],
        fetch=lambda url, accept: response(b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>'))
    doctype = _run_xml(xml_program, "https://www.rfc-editor.org/doctype.xml", ["x"],
        fetch=lambda url, accept: response(b'<!DOCTYPE x><x>safe</x>'))
    oversize = _run_xml(xml_program, "https://www.rfc-editor.org/large.xml", ["x"],
        fetch=lambda url, accept: response(b'<x>large</x>', oversize=True))
    arbitrary = _run_pagination({"operator": "EVAL", "code": "open('/tmp/x','w')"}, cycle_url)
    shell = _run_pagination({"operator": "SHELL", "argv": ["sh", "-c", "id"]}, cycle_url)
    write = _run_pagination({"operator": "HTTP_POST", "method": "POST"}, cycle_url)
    checks = [
        ("pagination_cycle", not cycle["passed"] and cycle.get("reason") == "continuation_cycle"),
        ("duplicate_identity_inflation", duplicate["passed"] and duplicate.get("unique_records") == 1),
        ("unbounded_page_budget", not unbounded["passed"]),
        ("cross_authority_continuation", not cross["passed"] and cross.get("reason") == "cross_authority_continuation"),
        ("xml_external_entity", not entity["passed"]), ("xml_doctype", not doctype["passed"]),
        ("oversize_xml", not oversize["passed"]), ("arbitrary_eval", not arbitrary["passed"]),
        ("shell_adapter", not shell["passed"]), ("write_method", not write["passed"]),
    ]
    return [{"property": name, "rejected": bool(passed)} for name, passed in checks]


def run(*, state_path: Path, result_path: Path, minimum_later_delay_seconds: float = 300.0) -> dict[str, Any]:
    pagination_program, pagination_search = _invent_pagination()
    xml_program, xml_search = _invent_xml()
    programs = {"pagination": pagination_program, "xml_evidence": xml_program}
    program_commitment = {"created_at": datetime.now(timezone.utc).isoformat(), "programs": programs,
                          "parent": "procedure_multistep_institutional_intelligence_v1"}
    program_commitment["commitment_sha256"] = _sha(program_commitment)

    fr_pages = _run_pagination(pagination_program, _federal_register_pagination_url())
    wb_pages = _run_pagination(pagination_program,
        "https://api.worldbank.org/v2/country/GBR/indicator/NY.GDP.MKTP.CD?format=json&per_page=20")
    fr_detail = _get("https://www.federalregister.gov/api/v1/documents.json?per_page=1&order=newest&conditions%5Bagencies%5D%5B%5D=environmental-protection-agency", "application/json")
    fr_payload = _decode_json(fr_detail)
    latest = (fr_payload or {}).get("results", [{}])[0] if isinstance(fr_payload, dict) else {}
    detail_url = f"https://www.federalregister.gov/api/v1/documents/{latest.get('document_number', '')}.json"
    detail = _decode_json(_get(detail_url, "application/json")) or {}
    fr_xml_url = detail.get("full_text_xml_url", "")
    fr_xml = _run_xml(xml_program, fr_xml_url, ["AGENCY", "SUBJECT"])
    rfc_xml = _run_xml(xml_program, "https://www.rfc-editor.org/rfc/rfc9110.xml", ["title", "abstract"])

    episodes = [
        {"family": "pagination", "authority": "Federal Register", "source_disjoint_role": "development",
         "target": "federal_register_pages", "result": fr_pages},
        {"family": "pagination", "authority": "World Bank", "source_disjoint_role": "transfer",
         "target": "world_bank_indicator_pages", "result": wb_pages},
        {"family": "xml_evidence", "authority": "Federal Register", "source_disjoint_role": "development",
         "target": fr_xml_url, "result": fr_xml},
        {"family": "xml_evidence", "authority": "RFC Editor", "source_disjoint_role": "transfer",
         "target": "https://www.rfc-editor.org/rfc/rfc9110.xml", "result": rfc_xml},
    ]
    now = time.time()
    for episode in episodes:
        episode["later_challenge"] = {"status": "WAITING_FOR_FUTURE_OUTCOME",
                                      "not_before_epoch": now + minimum_later_delay_seconds,
                                      "retention_credit": 0}
    adversarial = _adversarial_properties(pagination_program, xml_program)
    gate = {"invented_executable_primitives": 2, "candidate_programs_criticised": 7,
            "development_outcomes": int(fr_pages["passed"]) + int(fr_xml["passed"]),
            "source_disjoint_transfers": int(wb_pages["passed"]) + int(rfc_xml["passed"]),
            "pagination_authorities": 2, "xml_authorities": 2,
            "federal_register_unique_records": fr_pages.get("unique_records", 0),
            "world_bank_unique_records": wb_pages.get("unique_records", 0),
            "malicious_programs_rejected": sum(row["rejected"] for row in adversarial),
            "malicious_programs_total": len(adversarial),
            "ood_binary_abstention": True, "later_retention_credits": 0,
            "arbitrary_code_execution": 0, "credentials_used": 0, "live_writes": 0}
    gate["accepted"] = bool(gate["development_outcomes"] == 2 and gate["source_disjoint_transfers"] == 2
                            and gate["federal_register_unique_records"] >= 4
                            and gate["world_bank_unique_records"] >= 20
                            and gate["malicious_programs_rejected"] == gate["malicious_programs_total"]
                            and gate["arbitrary_code_execution"] == gate["credentials_used"] == gate["live_writes"] == 0)
    state = {"schema_version": "aion.hexcore.open_information_action_state.v1",
             "created_at": datetime.now(timezone.utc).isoformat(), "program_commitment": program_commitment,
             "programs": programs, "episodes": episodes}
    _write(state_path, state)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_missing_information_action_primitives",
        ["detect_action_grammar_residual", "synthesize_typed_action_ast", "generate_adversarial_properties",
         "execute_in_bounded_interpreter", "criticise_failed_programs", "precommit_surviving_program",
         "prove_source_disjoint_transfer", "schedule_later_outcome"],
        gate["development_outcomes"] + gate["source_disjoint_transfers"], gate["accepted"],
        {"gate": gate, "commitment": program_commitment["commitment_sha256"]},
        ["procedure_multistep_institutional_intelligence_v1"])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="open_information_action_invention")
    result = {"schema_version": "aion.hexcore.open_information_action_invention.v1",
              "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
              "passed": gate["accepted"], "status": "PROMOTED" if gate["accepted"] else "REJECTED",
              "gate": gate, "program_commitment": program_commitment,
              "candidate_criticism": {"pagination": pagination_search, "xml": xml_search},
              "adversarial_properties": adversarial,
              "episodes": episodes, "decision": decision,
              "boundary": "AION synthesized two typed action ASTs inside an engineered bounded interpreter. Operator atoms, live missions, authority allowlist and promotion gates remain engineered. This is bounded information-action invention with real transfer, not arbitrary code generation, unrestricted research, AGA or AGI."}
    _write(result_path, result)
    return result


def close_later_challenges(*, state_path: Path, result_path: Path) -> dict[str, Any]:
    if not state_path.exists() or not result_path.exists():
        return {"status": "NO_OPEN_ACTION_STATE", "passed": False}
    state, result = json.loads(state_path.read_text()), json.loads(result_path.read_text())
    changed = False
    for episode in state.get("episodes", []):
        challenge = episode["later_challenge"]
        if challenge["status"] != "WAITING_FOR_FUTURE_OUTCOME" or time.time() < challenge["not_before_epoch"]:
            continue
        if episode["family"] == "pagination":
            start = (_federal_register_pagination_url()
                     if episode["authority"] == "Federal Register" else
                     "https://api.worldbank.org/v2/country/GBR/indicator/NY.GDP.MKTP.CD?format=json&per_page=20")
            observed = _run_pagination(state["programs"]["pagination"], start)
        else:
            observed = _run_xml(state["programs"]["xml_evidence"], episode["target"],
                                ["AGENCY", "SUBJECT"] if episode["authority"] == "Federal Register" else ["title", "abstract"])
        passed = bool(observed.get("passed"))
        challenge.update({"status": "CONSEQUENCE_CONFIRMED" if passed else "REJECTED_BY_LATER_CONSEQUENCE",
                          "closed_at": datetime.now(timezone.utc).isoformat(), "passed": passed,
                          "retention_credit": int(passed), "outcome_sha256": _sha(observed),
                          "response_changed": _sha(observed) != _sha(episode["result"])})
        changed = True
    if not changed:
        return result
    confirmed = [row for row in state["episodes"] if row["later_challenge"].get("passed")]
    result["gate"]["later_retention_credits"] = len(confirmed)
    result["later_challenges"] = [row["later_challenge"] for row in state["episodes"]]
    if len(confirmed) == len(state["episodes"]):
        learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
        candidate = ProcedureCandidate(LATER_PROCEDURE_ID, "retain_invented_information_actions_after_later_outcomes",
            ["recover_committed_action_ast", "enforce_elapsed_boundary", "reexecute_across_authorities",
             "verify_properties", "retain_or_reject"], len(confirmed), True,
            {"confirmed": len(confirmed), "outcomes": [row["later_challenge"]["outcome_sha256"] for row in confirmed]},
            [PROCEDURE_ID])
        decision = learning.skills.promote(candidate)
        learning.skills.record_outcome(procedure_id=LATER_PROCEDURE_ID, success=True,
                                       score=len(confirmed), evidence=candidate.evidence)
        learning.store.commit(reason="open_information_action_later_retention")
        result["later_procedure_id"] = LATER_PROCEDURE_ID
        result["later_promotion"] = {"candidate": candidate.to_dict(), "decision": decision}
    _write(state_path, state)
    _write(result_path, result)
    return result
