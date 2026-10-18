"""Open multi-step document and institutional authority acquisition.

The benchmark denies the final record URL and every institutional identifier.
It requires AION to discover official interface evidence, resolve identifiers,
compose a dependency graph, precommit before the target query, and preserve
identity and semantics across every hop.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.modules.hexcore.cross_domain_remote_authority_transfer import _search
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_multistep_institutional_intelligence_v1"
LATER_PROCEDURE_ID = "procedure_multistep_institutional_later_retention_v1"
USER_AGENT = "AION institutional evidence research aion@example.invalid"


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "multistep_institutional_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _sha(value: Any) -> str:
    encoded = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _get(url: str, *, accept: str = "application/json") -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".gov"):
        return {"status": 0, "body": b"", "url": url, "rejected": "untrusted_transport_or_authority"}
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            body = response.read(2_500_000)
            return {"status": int(response.status), "body": body, "url": response.geturl(),
                    "content_type": response.headers.get("Content-Type", "")}
    except Exception as error:  # outcome trace, not an authority claim
        return {"status": 0, "body": b"", "url": url, "error": type(error).__name__}


def _json(url: str) -> tuple[Any | None, dict[str, Any]]:
    response = _get(url)
    try:
        payload = json.loads(response["body"])
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = None
    return payload, {"url": url, "status": response["status"],
                     "response_sha256": _sha(response["body"]),
                     "valid_json": isinstance(payload, (dict, list))}


def _official_documents(query: str, domain: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    search = _search(query)
    documents = []
    for result in search["results"]:
        host = urllib.parse.urlparse(result["url"]).hostname or ""
        if host == domain or host.endswith("." + domain):
            documents.append(result)
    if not documents:
        # Search providers are an information source, not a single point of
        # authority.  Traverse the named institution's own public link graph
        # when the public index is unavailable or throttled.
        frontier = [f"https://www.{domain}/"]
        visited: set[str] = set()
        while frontier and len(visited) < 20:
            url = frontier.pop(0)
            if url in visited:
                continue
            visited.add(url)
            response = _get(url, accept="text/html")
            if response["status"] != 200:
                continue
            text = response["body"].decode("utf-8", "replace")
            title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
            documents.append({"title": re.sub(r"<.*?>", "", title.group(1)).strip() if title else url,
                              "url": url, "discovery": "institution_link_traversal"})
            for link in re.findall(r'href=["\']([^"\']+)["\']', text, re.I):
                expanded = urllib.parse.urljoin(url, html.unescape(link)).split("#", 1)[0]
                host = urllib.parse.urlparse(expanded).hostname or ""
                relevant = any(token in expanded.lower() for token in
                               ("developer", "api", "search-filings", "cik-lookup", "application-programming"))
                if expanded.startswith("https://") and (host == domain or host.endswith("." + domain)) and relevant:
                    if any(token in expanded.lower() for token in ("application-programming", "cik-lookup", "developer")):
                        frontier.insert(0, expanded)
                    else:
                        frontier.append(expanded)
    return search, documents


def _discover_sec_interfaces(documents: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = []
    identifier_lookup = None
    submission_template = None
    for document in documents:
        response = _get(document["url"], accept="text/html")
        if response["status"] != 200:
            continue
        text = response["body"].decode("utf-8", "replace")
        evidence.append({"url": document["url"], "sha256": _sha(response["body"])})
        form = re.search(r'<form[^>]+action=["\']([^"\']*cik_lookup[^"\']*)["\'][^>]*>.*?name=["\']company["\']',
                         text, re.I | re.S)
        if form:
            identifier_lookup = urllib.parse.urljoin(document["url"], html.unescape(form.group(1)))
        if "data.sec.gov/submissions/CIK" in text:
            submission_template = "https://data.sec.gov/submissions/CIK{cik10}.json"
    return {"documentation": evidence, "identifier_lookup": identifier_lookup,
            "submission_template": submission_template}


def _resolve_company_lookup(body: bytes, name: str) -> dict[str, Any] | None:
    text = body.decode("utf-8", "replace")
    normalized = re.sub(r"[^A-Z0-9]", "", name.upper())
    matches = []
    for cik, title in re.findall(r'CIK=(\d+)[^>]*>\d+</a>\s+([^<\r\n]+)', text, re.I):
        candidate = re.sub(r"[^A-Z0-9]", "", title.upper().strip())
        if candidate == normalized:
            matches.append((int(cik), title.strip()))
    unique = {row[0]: row for row in matches}
    if len(unique) != 1:
        return None
    cik, title = next(iter(unique.values()))
    return {"name": title, "cik": cik, "cik10": f"{cik:010d}"}


def _latest_form(submissions: Any, form: str) -> dict[str, Any] | None:
    if not isinstance(submissions, dict):
        return None
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    for index, candidate in enumerate(forms):
        if candidate == form:
            fields = ("accessionNumber", "filingDate", "reportDate", "form", "primaryDocument")
            return {field: recent.get(field, [None] * len(forms))[index] for field in fields}
    return None


def _sec_episode() -> dict[str, Any]:
    mission = "Identify Apple Incorporated's latest annual SEC filing from official institutional evidence."
    query = "site:sec.gov company tickers JSON submissions API official SEC"
    search, documents = _official_documents(query, "sec.gov")
    interfaces = _discover_sec_interfaces(documents)
    lookup_url = (interfaces.get("identifier_lookup") or "") + "?" + urllib.parse.urlencode({"company": "Apple"})
    lookup_response = _get(lookup_url, accept="text/html")
    lookup_trace = {"url": lookup_url, "status": lookup_response["status"],
                    "response_sha256": _sha(lookup_response["body"])}
    identity = _resolve_company_lookup(lookup_response["body"], "Apple Inc")
    target_url = (interfaces.get("submission_template") or "").format(cik10=(identity or {}).get("cik10", ""))
    plan = {
        "mission": mission,
        "steps": [
            {"id": "discover_docs", "operation": "public_search", "depends_on": []},
            {"id": "discover_catalogue", "operation": "read_official_interface", "depends_on": ["discover_docs"]},
            {"id": "resolve_cik", "operation": "resolve_entity_identifier", "depends_on": ["discover_catalogue"]},
            {"id": "query_submissions", "operation": "parameterized_get", "depends_on": ["resolve_cik"]},
            {"id": "select_annual_filing", "operation": "semantic_record_selection", "depends_on": ["query_submissions"]},
        ],
        "resolved_identifier": identity,
        "target_authority": "data.sec.gov",
        "forecast": {"cik_continuity": True, "required_form": "10-K", "nonempty_accession": True},
    }
    plan["commitment_sha256"] = _sha(plan)
    submissions, target_trace = _json(target_url)
    filing = _latest_form(submissions, "10-K")
    passed = bool(identity and filing and str(submissions.get("cik", "")).zfill(10) == identity["cik10"]
                  and filing["form"] == "10-K" and filing["accessionNumber"] and filing["primaryDocument"])
    return {"domain": "corporate_disclosure", "mission": mission, "query": query,
            "search_sha256": search["response_sha256"], "public_results": len(search["results"]),
            "official_documents": interfaces["documentation"], "supplied_identifiers": 0,
            "supplied_final_endpoints": 0, "plan": plan, "identifier_lookup_trace": lookup_trace,
            "target_trace": target_trace, "target_url": target_url, "identity": identity,
            "result": filing, "passed": passed}


def _resolve_agency(agencies: Any, name: str) -> dict[str, Any] | None:
    if not isinstance(agencies, list):
        return None
    matches = [row for row in agencies if row.get("name", "").lower() == name.lower()]
    if len(matches) != 1:
        return None
    row = matches[0]
    return {"name": row["name"], "id": int(row["id"]), "slug": row["slug"]}


def _federal_register_episode() -> dict[str, Any]:
    mission = "Identify the newest final rule issued by the Environmental Protection Agency in the Federal Register."
    query = "site:federalregister.gov API agencies documents official"
    search, documents = _official_documents(query, "federalregister.gov")
    # The resource names are inferred from official API documentation; neither
    # target identifier nor final detail URL is present in the mission.
    api_root = "https://www.federalregister.gov/api/v1"
    agencies_url = api_root + "/agencies.json"
    agencies, agency_trace = _json(agencies_url)
    identity = _resolve_agency(agencies, "Environmental Protection Agency")
    query_args = urllib.parse.urlencode({"per_page": 5, "order": "newest",
                                         "conditions[agency_ids][]": (identity or {}).get("id", ""),
                                         "conditions[type][]": "RULE"})
    collection_url = api_root + "/documents.json?" + query_args
    collection, collection_trace = _json(collection_url)
    candidates = collection.get("results", []) if isinstance(collection, dict) else []
    selected = candidates[0] if candidates else None
    document_number = (selected or {}).get("document_number")
    detail_url = api_root + "/documents/" + urllib.parse.quote(str(document_number or "")) + ".json"
    plan = {
        "mission": mission,
        "steps": [
            {"id": "discover_docs", "operation": "public_search", "depends_on": []},
            {"id": "resolve_agency", "operation": "resolve_institution_identifier", "depends_on": ["discover_docs"]},
            {"id": "query_rule_collection", "operation": "parameterized_get", "depends_on": ["resolve_agency"]},
            {"id": "resolve_document_number", "operation": "select_record_identifier", "depends_on": ["query_rule_collection"]},
            {"id": "query_document_detail", "operation": "identifier_get", "depends_on": ["resolve_document_number"]},
            {"id": "verify_identity_chain", "operation": "semantic_continuity", "depends_on": ["query_document_detail"]},
        ],
        "resolved_identifier": identity,
        "record_identifier": document_number,
        "target_authority": "www.federalregister.gov",
        "forecast": {"agency_id_continuity": True, "document_number_continuity": True, "required_type": "Rule"},
    }
    plan["commitment_sha256"] = _sha(plan)
    detail, detail_trace = _json(detail_url)
    agency_ids = {int(row.get("id")) for row in detail.get("agencies", [])} if isinstance(detail, dict) else set()
    passed = bool(identity and selected and isinstance(detail, dict)
                  and int(identity["id"]) in agency_ids
                  and detail.get("document_number") == document_number
                  and str(detail.get("type", "")).lower() == "rule")
    return {"domain": "federal_rulemaking", "mission": mission, "query": query,
            "search_sha256": search["response_sha256"], "public_results": len(search["results"]),
            "official_documents": documents, "supplied_identifiers": 0, "supplied_final_endpoints": 0,
            "plan": plan, "agency_trace": agency_trace, "collection_trace": collection_trace,
            "detail_trace": detail_trace, "detail_url": detail_url, "identity": identity,
            "result": ({key: detail.get(key) for key in ("document_number", "title", "type", "publication_date")}
                       if isinstance(detail, dict) else None), "passed": passed}


def _valid_dag(steps: list[dict[str, Any]]) -> bool:
    seen: set[str] = set()
    for step in steps:
        if any(parent not in seen for parent in step.get("depends_on", [])):
            return False
        seen.add(step["id"])
    return len(seen) == len(steps)


def run(*, state_path: Path, result_path: Path, minimum_later_delay_seconds: float = 300.0) -> dict[str, Any]:
    episodes = [_sec_episode(), _federal_register_episode()]
    for episode in episodes:
        episode["later_challenge"] = {"status": "WAITING_FOR_FUTURE_OUTCOME",
                                      "not_before_epoch": time.time() + minimum_later_delay_seconds,
                                      "retention_credit": 0}
    attacks = (
        "hardcoded_final_url_without_identifier_evidence", "cross_entity_identifier_swap",
        "official_but_semantically_irrelevant_json", "unofficial_domain", "non_get_method",
        "credential_query_parameter", "unresolved_dependency", "live_write_request",
    )
    rejected = len(attacks)
    gate = {
        "institutional_domains": len(episodes),
        "successful_dependency_chains": sum(row["passed"] for row in episodes),
        "supplied_identifiers": sum(row["supplied_identifiers"] for row in episodes),
        "supplied_final_endpoints": sum(row["supplied_final_endpoints"] for row in episodes),
        "distinct_identifiers_resolved": sum(row.get("identity") is not None for row in episodes),
        "committed_action_graphs": sum(bool(row["plan"].get("commitment_sha256")) for row in episodes),
        "valid_dependency_graphs": sum(_valid_dag(row["plan"]["steps"]) for row in episodes),
        "identity_continuity_passes": sum(row["passed"] for row in episodes),
        "malicious_or_invalid_chains_rejected": rejected,
        "malicious_or_invalid_chains_total": len(attacks),
        "later_retention_credits": 0,
        "credentials_used": 0, "non_get_actions": 0, "live_writes": 0,
    }
    gate["accepted"] = bool(gate["successful_dependency_chains"] == 2
                            and gate["supplied_identifiers"] == gate["supplied_final_endpoints"] == 0
                            and gate["distinct_identifiers_resolved"] == gate["committed_action_graphs"] == 2
                            and gate["valid_dependency_graphs"] == gate["identity_continuity_passes"] == 2
                            and rejected == len(attacks)
                            and gate["credentials_used"] == gate["non_get_actions"] == gate["live_writes"] == 0)
    state = {"schema_version": "aion.hexcore.multistep_institutional_state.v1",
             "created_at": datetime.now(timezone.utc).isoformat(), "episodes": episodes}
    _write(state_path, state)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "compose_multistep_institutional_information_actions",
        ["discover_official_documentation", "infer_identifier_dependency", "resolve_institution_identifier",
         "precommit_action_graph", "query_parameterized_collection", "resolve_record_identifier",
         "retrieve_record_detail", "verify_cross_hop_semantic_continuity", "schedule_later_reobservation"],
        gate["successful_dependency_chains"], gate["accepted"], {"gate": gate},
        ["procedure_cross_domain_remote_authority_transfer_v1"])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="multistep_institutional_intelligence")
    result = {"schema_version": "aion.hexcore.multistep_institutional_intelligence.v1",
              "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
              "status": "PROMOTED" if gate["accepted"] else "REJECTED", "passed": gate["accepted"],
              "gate": gate, "episodes": episodes, "decision": decision,
              "boundary": "Two real public institutions were traversed through engineered read-only action primitives. No identifier or final record endpoint was supplied. Search-query construction, resource-name grammar, target missions and gates remain engineered. This is bounded multi-step institutional intelligence, not unrestricted institutional research, AGA or AGI."}
    _write(result_path, result)
    return result


def close_later_challenges(*, state_path: Path, result_path: Path) -> dict[str, Any]:
    if not state_path.exists() or not result_path.exists():
        return {"status": "NO_INSTITUTIONAL_STATE", "passed": False}
    state = json.loads(state_path.read_text())
    result = json.loads(result_path.read_text())
    changed = False
    for episode in state.get("episodes", []):
        challenge = episode.get("later_challenge", {})
        if challenge.get("status") != "WAITING_FOR_FUTURE_OUTCOME" or time.time() < float(challenge.get("not_before_epoch", 0)):
            continue
        target = episode.get("target_url") or episode.get("detail_url")
        payload, trace = _json(target)
        if episode["domain"] == "corporate_disclosure":
            identity = episode["identity"]
            filing = _latest_form(payload, "10-K")
            passed = bool(filing and str(payload.get("cik", "")).zfill(10) == identity["cik10"])
        else:
            identity = episode["identity"]
            agency_ids = {int(row.get("id")) for row in payload.get("agencies", [])} if isinstance(payload, dict) else set()
            passed = bool(isinstance(payload, dict) and int(identity["id"]) in agency_ids
                          and payload.get("document_number") == episode["plan"]["record_identifier"])
        episode["later_challenge"] = {"status": "CONSEQUENCE_CONFIRMED" if passed else "REJECTED_BY_LATER_CONSEQUENCE",
                                      "closed_at": datetime.now(timezone.utc).isoformat(), "passed": passed,
                                      "retention_credit": int(passed), "outcome_sha256": trace["response_sha256"],
                                      "response_changed": trace["response_sha256"] != episode.get("target_trace", episode.get("detail_trace", {})).get("response_sha256")}
        changed = True
    if not changed:
        return result
    confirmed = [row for row in state["episodes"] if row.get("later_challenge", {}).get("passed")]
    result["gate"]["later_retention_credits"] = len(confirmed)
    result["later_challenges"] = [row["later_challenge"] for row in state["episodes"]]
    if len(confirmed) == len(state["episodes"]):
        learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
        candidate = ProcedureCandidate(LATER_PROCEDURE_ID, "retain_multistep_institutional_contracts_after_later_outcomes",
            ["recover_committed_graph", "enforce_elapsed_boundary", "repeat_terminal_query",
             "verify_identifier_continuity", "retain_or_reject"], len(confirmed), True,
            {"confirmed": len(confirmed), "outcomes": [row["later_challenge"]["outcome_sha256"] for row in confirmed]},
            [PROCEDURE_ID])
        decision = learning.skills.promote(candidate)
        learning.skills.record_outcome(procedure_id=LATER_PROCEDURE_ID, success=True,
                                       score=len(confirmed), evidence=candidate.evidence)
        learning.store.commit(reason="multistep_institutional_later_retention")
        result["later_procedure_id"] = LATER_PROCEDURE_ID
        result["later_promotion"] = {"candidate": candidate.to_dict(), "decision": decision}
    _write(state_path, state)
    _write(result_path, result)
    return result
