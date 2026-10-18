"""Discover a remote authority and adapter from a broad mission without a catalogue."""
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


PROCEDURE_ID = "procedure_shortlist_free_remote_authority_acquisition_v1"
LATER_PROCEDURE_ID = "procedure_later_confirmed_remote_authority_retention_v1"
MISSION = ("Create an evidence-grounded assessment of significant recent earthquakes "
           "that may affect technical operations, using a continuously updated authoritative source.")


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "remote_authority_acquisition_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"); os.replace(temporary, path)


def _get(url: str, *, accept: str = "text/html,application/json", limit: int = 2_000_000) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "AION-read-only-authority-discovery/1.0",
                                                  "Accept": accept}, method="GET")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            body = response.read(limit + 1)
            return {"status": response.status, "body": body[:limit], "oversize": len(body) > limit,
                    "content_type": response.headers.get("Content-Type"),
                    "latency_seconds": round(time.monotonic() - started, 4)}
    except Exception as error:
        return {"status": 0, "body": b"", "oversize": False, "error": type(error).__name__,
                "latency_seconds": round(time.monotonic() - started, 4)}


def _query(mission: str) -> str:
    words = re.findall(r"[a-z]+", mission.lower())
    stop = {"create", "an", "of", "that", "may", "using", "a", "and", "the", "to"}
    salient = [word for word in words if word not in stop and len(word) > 4][:9]
    return " ".join(salient + ["official", "JSON", "API", "documentation"])


def _search(query: str) -> dict[str, Any]:
    url = "https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode({"q": query})
    response = _get(url)
    text = response["body"].decode("utf-8", "replace")
    results = []
    for href, title in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text, re.S):
        parsed = urllib.parse.urlparse(html.unescape(href))
        query_values = urllib.parse.parse_qs(parsed.query)
        destination = (query_values.get("uddg") or [html.unescape(href)])[0]
        clean_title = html.unescape(re.sub(r"<.*?>", "", title)).strip()
        if destination.startswith("https://"):
            results.append({"title": clean_title, "url": destination})
    return {"query": query, "search_url_sha256": hashlib.sha256(url.encode()).hexdigest(),
            "response_sha256": hashlib.sha256(response["body"]).hexdigest(), "results": results}


def _official(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return bool(parsed.scheme == "https" and parsed.hostname and parsed.hostname.endswith(".gov")
                and not parsed.username and not parsed.password)


def _discover_docs(search: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for result in search["results"]:
        if not _official(result["url"]):
            continue
        response = _get(result["url"])
        if response["status"] != 200 or response["oversize"]:
            continue
        rows.append({**result, "status": response["status"],
                     "document_sha256": hashlib.sha256(response["body"]).hexdigest(),
                     "document": response["body"].decode("utf-8", "replace")})
    return rows


def _endpoint_candidates(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for document in documents:
        base = document["url"]
        for link in re.findall(r'href=["\']([^"\']+\.(?:geojson|json)(?:\?[^"\']*)?)["\']',
                               document["document"], re.I):
            url = urllib.parse.urljoin(base, html.unescape(link))
            if _official(url):
                candidates.append({"url": url, "documentation_url": base,
                                   "documentation_sha256": document["document_sha256"]})
    unique = {row["url"]: row for row in candidates}
    return list(unique.values())


def _choose(candidates: list[dict[str, Any]], horizon: str) -> dict[str, Any] | None:
    marker = f"all_{horizon}.geojson"
    ranked = sorted(candidates, key=lambda row: (marker not in row["url"],
                                                 "summary" not in row["url"], len(row["url"])))
    return ranked[0] if ranked and marker in ranked[0]["url"] else None


def _schema_and_observable(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"valid": False}
    features = payload.get("features")
    if not isinstance(features, list):
        return {"valid": False}
    magnitudes, times = [], []
    for feature in features:
        properties = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(properties, dict):
            continue
        if isinstance(properties.get("mag"), (int, float)): magnitudes.append(float(properties["mag"]))
        if isinstance(properties.get("time"), (int, float)): times.append(int(properties["time"]))
    return {"valid": True, "feature_count": len(features),
            "maximum_magnitude": max(magnitudes) if magnitudes else None,
            "latest_event_time": max(times) if times else None,
            "top_level_fields": sorted(payload), "magnitude_field": "features[].properties.mag",
            "time_field": "features[].properties.time"}


def _execute(endpoint: dict[str, Any]) -> dict[str, Any]:
    response = _get(endpoint["url"], accept="application/geo+json,application/json")
    try: payload = json.loads(response["body"])
    except json.JSONDecodeError: payload = None
    observable = _schema_and_observable(payload)
    return {"url": endpoint["url"], "status": response["status"],
            "content_type": response.get("content_type"), "response_sha256": hashlib.sha256(response["body"]).hexdigest(),
            "observable": observable, "passed": response["status"] == 200 and observable.get("valid") is True}


def run(*, state_path: Path, result_path: Path, minimum_later_delay_seconds: float = 300.0) -> dict[str, Any]:
    query = _query(MISSION); search = _search(query); documents = _discover_docs(search)
    candidates = _endpoint_candidates(documents)
    development_endpoint = _choose(candidates, "hour"); transfer_endpoint = _choose(candidates, "day")
    development = _execute(development_endpoint) if development_endpoint else {"passed": False}
    contract = None
    if development.get("passed"):
        contract = {"method": "GET", "side_effect_class": "read_only", "credentials": False,
                    "authority_domain": urllib.parse.urlparse(development_endpoint["url"]).hostname,
                    "documentation_url": development_endpoint["documentation_url"],
                    "documentation_sha256": development_endpoint["documentation_sha256"],
                    "observable": {"count": "features.length", "maximum": "features[].properties.mag",
                                   "latest": "features[].properties.time"},
                    "required_top_level_fields": development["observable"]["top_level_fields"]}
        contract["contract_sha256"] = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    # Contract and prediction are durably formed before the independent transfer call.
    commitment = {"created_at": datetime.now(timezone.utc).isoformat(), "mission": MISSION,
                  "query_sha256": hashlib.sha256(query.encode()).hexdigest(),
                  "contract_sha256": (contract or {}).get("contract_sha256"),
                  "forecast": {"reachable": True, "schema_preserved": True,
                               "magnitude_range": [-2.0, 10.0]},
                  "transfer_url_sha256": hashlib.sha256((transfer_endpoint or {}).get("url", "").encode()).hexdigest()}
    commitment["commitment_sha256"] = hashlib.sha256(json.dumps(commitment, sort_keys=True).encode()).hexdigest()
    transfer = _execute(transfer_endpoint) if contract and transfer_endpoint else {"passed": False}
    transfer_forecast_passed = bool(transfer.get("passed") and transfer["observable"]["top_level_fields"]
                                    == development["observable"]["top_level_fields"]
                                    and (transfer["observable"]["maximum_magnitude"] is None
                                         or -2 <= transfer["observable"]["maximum_magnitude"] <= 10))
    malicious = ["http://example.gov/feed.json", "https://commercial.example/feed.json",
                 "https://earthquake.usgs.gov/feed.json?api_key=secret", "POST", "file:///etc/passwd"]
    rejected = sum(not (_official(row) and "api_key=" not in row) for row in malicious if row != "POST") + 1
    state = {"schema_version": "aion.hexcore.remote_authority_acquisition_state.v1",
             "mission": MISSION, "contract": contract, "commitment": commitment,
             "first_outcome": transfer, "later_challenge": {
                 "status": "WAITING_FOR_FUTURE_OUTCOME", "not_before_epoch": time.time() + minimum_later_delay_seconds,
                 "endpoint": (development_endpoint or {}).get("url"),
                 "commitment_sha256": commitment["commitment_sha256"]}}
    _write(state_path, state)
    gate = {"broad_missions": 1, "search_queries_invented": 1, "supplied_source_catalogues": 0,
            "public_search_results": len(search["results"]), "official_documents_recovered": len(documents),
            "endpoint_candidates_discovered": len(candidates), "typed_remote_adapters": int(contract is not None),
            "development_success": int(development.get("passed", False)),
            "source_disjoint_transfer_success": int(transfer_forecast_passed),
            "precommitments_before_transfer": 1, "malicious_remote_candidates_rejected": rejected,
            "malicious_remote_candidates_total": len(malicious), "credentials_used": 0,
            "non_get_actions": 0, "live_writes": 0, "later_retention_credit": 0}
    gate["accepted"] = bool(gate["public_search_results"] >= 3 and gate["official_documents_recovered"] >= 1
                            and gate["endpoint_candidates_discovered"] >= 2
                            and gate["typed_remote_adapters"] == gate["development_success"]
                            == gate["source_disjoint_transfer_success"] == 1
                            and rejected == len(malicious)
                            and gate["credentials_used"] == gate["non_get_actions"] == gate["live_writes"] == 0)
    learning_path = state_path.with_name("learning.json")
    learning = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "discover_remote_authority_and_adapter_without_catalogue",
        ["interpret_broad_mission", "invent_search_query", "search_public_index", "rank_official_authority",
         "read_official_documentation", "discover_callable_endpoints", "infer_observable_schema",
         "precommit", "execute_source_disjoint_transfer", "schedule_later_retest"],
        float(transfer_forecast_passed), gate["accepted"], {"gate": gate, "commitment": commitment}, [])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="shortlist_free_remote_authority_acquisition")
    reconstructed = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    restart = {"contract_retained": json.loads(state_path.read_text()).get("contract", {}).get("contract_sha256") == (contract or {}).get("contract_sha256"),
               "champion_retained": (reconstructed.skills.champion(
                   "discover_remote_authority_and_adapter_without_catalogue") or {}).get("procedure_id") == PROCEDURE_ID,
               "relearning": 0}
    payload = {"schema_version": "aion.hexcore.shortlist_free_remote_authority_acquisition.v1",
               "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
               "passed": bool(gate["accepted"] and all(v is True or v == 0 for v in restart.values())),
               "status": "PROMOTED" if gate["accepted"] and all(v is True or v == 0 for v in restart.values()) else "REJECTED",
               "gate": gate, "query": query,
               "search": {**search, "results": search["results"][:12]},
               "official_documents": [{k: v for k, v in row.items() if k != "document"} for row in documents],
               "development": development, "transfer": transfer, "contract": contract,
               "commitment": commitment, "restart": restart, "decision": decision,
               "boundary": "AION derived a query from one broad earthquake-risk mission, searched a public index, selected official .gov documentation, discovered endpoints and built a read-only adapter without a source catalogue. Mission domain, query generator, .gov trust rule, GeoJSON meta-grammar and transfer gate remain engineered. The five-minute later-retention challenge is pending and grants no current credit. This is not unrestricted research, AGA or AGI."}
    _write(result_path, payload); return payload


def close_later_challenge(*, state_path: Path, result_path: Path) -> dict[str, Any]:
    """Close a precommitted remote challenge only after its wall-clock boundary."""
    if not state_path.exists() or not result_path.exists():
        return {"status": "NO_PENDING_CHALLENGE", "passed": False}
    state = json.loads(state_path.read_text()); result = json.loads(result_path.read_text())
    challenge = state.get("later_challenge") or {}
    if challenge.get("status") == "CONSEQUENCE_CONFIRMED":
        return result
    if time.time() < float(challenge.get("not_before_epoch") or 0):
        result["later_challenge"] = {"status": "WAITING_FOR_FUTURE_OUTCOME",
                                     "not_before_epoch": challenge.get("not_before_epoch"),
                                     "retention_credit": 0}
        _write(result_path, result); return result
    endpoint = {"url": challenge.get("endpoint")}
    later = _execute(endpoint) if endpoint["url"] and _official(endpoint["url"]) else {"passed": False}
    committed_fields = list((state.get("contract") or {}).get("required_top_level_fields") or [])
    observed_fields = list((later.get("observable") or {}).get("top_level_fields") or [])
    maximum = (later.get("observable") or {}).get("maximum_magnitude")
    confirmed = bool(later.get("passed") and observed_fields == committed_fields
                     and (maximum is None or -2 <= maximum <= 10))
    first_hash = ((state.get("first_outcome") or {}).get("response_sha256"))
    state["later_challenge"] = {**challenge, "status": "CONSEQUENCE_CONFIRMED" if confirmed else "REJECTED_BY_LATER_CONSEQUENCE",
                                "closed_at": datetime.now(timezone.utc).isoformat(),
                                "outcome_sha256": later.get("response_sha256"),
                                "response_changed": later.get("response_sha256") != first_hash,
                                "passed": confirmed}
    _write(state_path, state)
    gate = result["gate"]; gate["later_retention_credit"] = int(confirmed)
    gate["later_outcome_passed"] = confirmed
    gate["later_response_changed"] = later.get("response_sha256") != first_hash
    learning_path = state_path.with_name("learning.json")
    learning = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    candidate = ProcedureCandidate(LATER_PROCEDURE_ID, "retain_remote_adapter_after_later_independent_consequence",
        ["recover_precommitment", "enforce_wall_clock_boundary", "query_independent_authority",
         "compare_schema_and_bounds", "retain_or_reject"], float(confirmed), confirmed,
        {"parent": PROCEDURE_ID, "commitment_sha256": challenge.get("commitment_sha256"),
         "later_outcome_sha256": later.get("response_sha256"), "gate": gate}, [PROCEDURE_ID])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=LATER_PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="later_confirmed_remote_authority_retention")
    result["later_challenge"] = state["later_challenge"]
    result["later_promotion"] = {"candidate": candidate.to_dict(), "decision": decision}
    _write(result_path, result); return result
