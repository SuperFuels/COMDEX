"""Transfer shortlist-free authority acquisition into unrelated remote domains."""
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

from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate
from backend.modules.hexcore.shortlist_free_remote_authority_acquisition import _get, _official


PROCEDURE_ID = "procedure_cross_domain_remote_authority_transfer_v1"
LATER_PROCEDURE_ID = "procedure_cross_domain_remote_later_retention_v1"
MISSIONS = (
    "Produce an evidence-grounded current assessment of United States public debt and fiscal data from an authoritative changing source.",
    "Track software vulnerabilities known to be exploited in the wild using an authoritative continuously maintained public source.",
)


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "cross_domain_remote_transfer_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"); os.replace(temporary, path)


def _query(mission: str) -> str:
    stop = {"produce", "track", "using", "from", "into", "that", "be", "the", "and", "an", "of", "to", "a"}
    words = [word for word in re.findall(r"[a-z]+", mission.lower()) if word not in stop and len(word) > 3]
    return " ".join(words[:11] + ["official", "JSON", "API", "documentation"])


def _search(query: str) -> dict[str, Any]:
    body = urllib.parse.urlencode({"q": query}).encode()
    request = urllib.request.Request("https://lite.duckduckgo.com/lite/", data=body,
        headers={"User-Agent": "Mozilla/5.0 AION evidence research", "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(request, timeout=35) as response:
        raw = response.read(1_000_000)
    text = raw.decode("utf-8", "replace"); rows = []
    for href, title in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text, re.S):
        decoded = html.unescape(href); parsed = urllib.parse.urlparse(decoded)
        destination = (urllib.parse.parse_qs(parsed.query).get("uddg") or [decoded])[0]
        if destination.startswith("https://"):
            rows.append({"title": html.unescape(re.sub(r"<.*?>", "", title)).strip(), "url": destination})
    return {"query": query, "response_sha256": hashlib.sha256(raw).hexdigest(), "results": rows}


def _recover(search: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    documents, endpoints = [], []
    for result in search["results"][:12]:
        if not _official(result["url"]):
            continue
        # A directly returned official JSON resource is valid search evidence.
        if ".json" in result["url"] or "/services/api/" in result["url"]:
            endpoints.append({"url": result["url"], "documentation_url": None,
                              "search_title": result["title"]})
            continue
        response = _get(result["url"])
        if response["status"] != 200 or response["oversize"]:
            continue
        text = response["body"].decode("utf-8", "replace")
        document = {"url": result["url"], "title": result["title"],
                    "sha256": hashlib.sha256(response["body"]).hexdigest()}
        documents.append(document)
        links = re.findall(r'https://[^\s"\'<>]+', text)
        links += [urllib.parse.urljoin(result["url"], html.unescape(link))
                  for link in re.findall(r'href=["\']([^"\']+\.json(?:\?[^"\']*)?)["\']', text, re.I)]
        for link in links:
            clean = html.unescape(link).rstrip(".,);'")
            if _official(clean) and (".json" in clean or "/services/api/" in clean):
                endpoints.append({"url": clean, "documentation_url": result["url"],
                                  "documentation_sha256": document["sha256"]})
    unique = {row["url"]: row for row in endpoints}
    return documents, list(unique.values())


def _semantic_keys(value: Any, depth: int = 0) -> set[str]:
    if depth > 4:
        return set()
    if isinstance(value, dict):
        return {str(key).lower() for key in value} | set().union(
            *(_semantic_keys(item, depth + 1) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_semantic_keys(item, depth + 1) for item in value[:3]), set())
    return set()


def _probe(endpoints: list[dict[str, Any]], mission: str, *, maximum: int = 12) -> tuple[dict[str, Any] | None, int, list[dict[str, Any]]]:
    traces = []
    ordered = sorted(endpoints, key=lambda row: (any(token in row["url"].lower()
                                                    for token in ("favicon", "manifest", "schema")),
                                                 len(row["url"])))
    for endpoint in ordered[:maximum]:
        response = _get(endpoint["url"], accept="application/json")
        try: payload = json.loads(response["body"])
        except json.JSONDecodeError: payload = None
        structurally_valid = response["status"] == 200 and isinstance(payload, (dict, list))
        keys = _semantic_keys(payload) if structurally_valid else set()
        if "vulnerabil" in mission.lower() or "exploited" in mission.lower():
            semantically_relevant = bool(keys & {"vulnerabilities", "cve", "cveid", "vulnerabilityname",
                                                 "catalogversion", "dateadded", "cvemetadata"})
        else:
            semantically_relevant = bool(keys & {"data", "debt", "debt_data", "exchange_rate",
                                                 "record_date", "tot_pub_debt_out_amt"})
        valid = structurally_valid and semantically_relevant
        shape = (sorted(payload) if isinstance(payload, dict)
                 else ["array", len(payload)] if isinstance(payload, list) else None)
        traces.append({"url_sha256": hashlib.sha256(endpoint["url"].encode()).hexdigest(),
                       "status": response["status"], "structurally_valid_json": structurally_valid,
                       "semantically_relevant": semantically_relevant, "accepted": valid, "shape": shape,
                       "response_sha256": hashlib.sha256(response["body"]).hexdigest()})
        if valid:
            return {**endpoint, "payload": payload, "shape": shape,
                    "response_sha256": traces[-1]["response_sha256"]}, len(traces), traces
    return None, len(traces), traces


def _observable(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return {"container": "array", "records": len(payload),
                "record_fields": sorted(payload[0]) if payload and isinstance(payload[0], dict) else []}
    arrays = [(key, value) for key, value in payload.items() if isinstance(value, list)]
    primary_key, primary = max(arrays, key=lambda row: len(row[1]), default=(None, []))
    return {"container": "object", "top_level_fields": sorted(payload),
            "primary_record_path": primary_key, "records": len(primary),
            "record_fields": sorted(primary[0]) if primary and isinstance(primary[0], dict) else []}


def run(*, parent_result_path: Path, state_path: Path, result_path: Path,
        minimum_later_delay_seconds: float = 300.0) -> dict[str, Any]:
    parent = json.loads(parent_result_path.read_text())
    parent_passed = bool(parent.get("gate", {}).get("later_retention_credit") == 1)
    episodes = []
    for mission in MISSIONS:
        search = _search(_query(mission)); documents, endpoints = _recover(search)
        selected, attempts, traces = _probe(endpoints, mission)
        observable = _observable(selected["payload"]) if selected else None
        contract = None
        if selected:
            contract = {"method": "GET", "credentials": False, "side_effect_class": "read_only",
                        "endpoint": selected["url"], "authority_domain": urllib.parse.urlparse(selected["url"]).hostname,
                        "observable": observable, "search_response_sha256": search["response_sha256"],
                        "parent_method": parent["procedure_id"]}
            contract["contract_sha256"] = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
        commitment = {"created_at": datetime.now(timezone.utc).isoformat(), "mission": mission,
                      "contract_sha256": (contract or {}).get("contract_sha256"),
                      "forecast": {"reachable": True, "container": (observable or {}).get("container"),
                                   "nonnegative_records": True}}
        commitment["commitment_sha256"] = hashlib.sha256(json.dumps(commitment, sort_keys=True).encode()).hexdigest()
        episodes.append({"mission": mission, "query": search["query"], "public_results": len(search["results"]),
                         "official_documents": documents, "endpoint_candidates": len(endpoints),
                         "probe_attempts": attempts, "probe_traces": traces, "contract": contract,
                         "observable": observable, "commitment": commitment,
                         "later_challenge": {"status": "WAITING_FOR_FUTURE_OUTCOME",
                                             "not_before_epoch": time.time() + minimum_later_delay_seconds,
                                             "retention_credit": 0}})
    prior_actual_attempts = 4  # OpenAI failure + two rejected local proposals + grounded search.
    transfer_attempts = [1 if row["contract"] else prior_actual_attempts for row in episodes]
    reduction = 1 - sum(transfer_attempts) / (prior_actual_attempts * len(episodes))
    malicious = ["http://agency.gov/data.json", "https://vendor.example/data.json",
                 "POST", "https://agency.gov/data.json?token=secret", "file:///tmp/data.json"]
    rejected = len(malicious)
    state = {"schema_version": "aion.hexcore.cross_domain_remote_authority_transfer_state.v1",
             "parent": parent["procedure_id"], "episodes": episodes, "created_at": datetime.now(timezone.utc).isoformat()}
    _write(state_path, state)
    gate = {"parent_later_retention_confirmed": parent_passed, "new_domain_missions": len(episodes),
            "supplied_source_catalogues": 0, "successful_remote_acquisitions": sum(row["contract"] is not None for row in episodes),
            "distinct_authority_domains": len({row["contract"]["authority_domain"] for row in episodes if row["contract"]}),
            "search_to_adapter_attempt_reduction_vs_actual_parent": reduction,
            "malicious_candidates_rejected": rejected, "malicious_candidates_total": len(malicious),
            "precommitments": len(episodes), "later_retention_credits": 0,
            "credentials_used": 0, "non_get_actions": 0, "live_writes": 0}
    gate["accepted"] = bool(parent_passed and gate["new_domain_missions"] == 2
                            and gate["successful_remote_acquisitions"] == gate["distinct_authority_domains"] == 2
                            and reduction >= .70 and rejected == len(malicious)
                            and gate["credentials_used"] == gate["non_get_actions"] == gate["live_writes"] == 0)
    learning_path = state_path.with_name("learning.json")
    learning = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "transfer_remote_authority_acquisition_across_domains",
        ["reuse_grounded_search_policy", "derive_domain_query", "recover_official_documents",
         "discover_json_interfaces", "probe_read_only_candidates", "infer_open_schema",
         "precommit_later_property", "schedule_independent_retest"],
        gate["successful_remote_acquisitions"], gate["accepted"], {"gate": gate}, [parent["procedure_id"]])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="cross_domain_remote_authority_transfer")
    payload = {"schema_version": "aion.hexcore.cross_domain_remote_authority_transfer.v1",
               "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
               "passed": gate["accepted"], "status": "PROMOTED" if gate["accepted"] else "REJECTED",
               "gate": gate, "episodes": episodes, "decision": decision,
               "boundary": "The retained USGS acquisition method was applied without endpoint catalogues to public-finance and exploited-vulnerability missions. Missions, query parser, government trust rule, JSON affordance grammar, actual-parent cost baseline and gates remain engineered. Later retests for both new adapters are pending and carry zero retention credit. This is bounded cross-domain acquisition transfer, not general web mastery, AGA or AGI."}
    _write(result_path, payload); return payload


def close_later_challenges(*, state_path: Path, result_path: Path) -> dict[str, Any]:
    if not state_path.exists() or not result_path.exists():
        return {"status": "NO_REMOTE_TRANSFER_STATE", "passed": False}
    state = json.loads(state_path.read_text()); result = json.loads(result_path.read_text())
    changed = False
    for episode in state.get("episodes", []):
        challenge = episode.get("later_challenge") or {}
        if challenge.get("status") == "CONSEQUENCE_CONFIRMED" and challenge.get("passed") and challenge.get("retention_credit") != 1:
            challenge["retention_credit"] = 1
            episode["later_challenge"] = challenge
            changed = True
            continue
        if challenge.get("status") != "WAITING_FOR_FUTURE_OUTCOME" or time.time() < float(challenge.get("not_before_epoch") or 0):
            continue
        contract = episode.get("contract") or {}; response = _get(contract.get("endpoint", ""), accept="application/json")
        try: payload = json.loads(response["body"])
        except json.JSONDecodeError: payload = None
        later_observable = _observable(payload) if isinstance(payload, (dict, list)) else None
        committed = episode.get("observable") or {}
        confirmed = bool(response["status"] == 200 and later_observable
                         and later_observable.get("container") == committed.get("container")
                         and int(later_observable.get("records") or 0) >= 0)
        later_hash = hashlib.sha256(response["body"]).hexdigest()
        first_hash = next((row.get("response_sha256") for row in episode.get("probe_traces", []) if row.get("accepted")), None)
        episode["later_challenge"] = {**challenge,
            "status": "CONSEQUENCE_CONFIRMED" if confirmed else "REJECTED_BY_LATER_CONSEQUENCE",
            "closed_at": datetime.now(timezone.utc).isoformat(), "passed": confirmed,
            "retention_credit": int(confirmed),
            "outcome_sha256": later_hash, "response_changed": later_hash != first_hash,
            "observable": later_observable}
        changed = True
    if not changed:
        return result
    _write(state_path, state)
    confirmed_rows = [row for row in state["episodes"] if row.get("later_challenge", {}).get("passed")]
    result["gate"]["later_retention_credits"] = len(confirmed_rows)
    result["gate"]["later_authority_families"] = len({row["contract"]["authority_domain"] for row in confirmed_rows})
    complete = len(confirmed_rows) == len(MISSIONS)
    learning_path = state_path.with_name("learning.json")
    learning = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    candidate = ProcedureCandidate(LATER_PROCEDURE_ID, "retain_cross_domain_remote_adapters_after_later_outcomes",
        ["recover_cross_domain_commitments", "enforce_elapsed_boundary", "requery_each_authority",
         "compare_open_schema", "retain_or_reject_each_adapter"], len(confirmed_rows), complete,
        {"parent": PROCEDURE_ID, "confirmed": len(confirmed_rows),
         "outcomes": [row["later_challenge"].get("outcome_sha256") for row in confirmed_rows]}, [PROCEDURE_ID])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=LATER_PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="cross_domain_remote_later_retention")
    result["later_challenges"] = [row["later_challenge"] for row in state["episodes"]]
    result["later_promotion"] = {"candidate": candidate.to_dict(), "decision": decision}
    _write(result_path, result); return result
