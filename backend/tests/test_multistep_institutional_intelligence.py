import json
from pathlib import Path

import backend.modules.hexcore.multistep_institutional_intelligence as institutional


def test_multistep_institutional_identifier_chains(tmp_path: Path, monkeypatch) -> None:
    sec_doc = "https://www.sec.gov/search-filings/edgar-application-programming-interfaces"
    fr_doc = "https://www.federalregister.gov/developers/documentation/api/v1"

    def fake_search(query: str):
        rows = ([{"title": "SEC API", "url": sec_doc}] if "sec.gov" in query else
                [{"title": "Federal Register API", "url": fr_doc}])
        return {"query": query, "response_sha256": "search-hash", "results": rows}

    sec_html = b'''<form action="https://www.sec.gov/cgi-bin/cik_lookup" method="POST">
      <input name="company"></form>
      https://data.sec.gov/submissions/CIK<strong>##########</strong>.json'''
    lookup_html = b'<a href="browse-edgar?action=getcompany&amp;CIK=320193">0000320193</a> APPLE INC.'
    submissions = {"cik": "0000320193", "filings": {"recent": {
        "form": ["10-K"], "accessionNumber": ["0000320193-25-000079"],
        "filingDate": ["2025-10-31"], "reportDate": ["2025-09-27"],
        "primaryDocument": ["aapl-20250927.htm"]}}}
    agencies = [{"name": "Environmental Protection Agency", "id": 145,
                 "slug": "environmental-protection-agency"}]
    collection = {"results": [{"document_number": "2026-15634"}]}
    detail = {"document_number": "2026-15634", "title": "Permethrin; Pesticide Tolerances",
              "type": "Rule", "publication_date": "2026-08-03",
              "agencies": [{"id": 145, "name": "Environmental Protection Agency"}]}

    def fake_get(url: str, *, accept: str = "application/json"):
        if url == sec_doc:
            body = sec_html
        elif "cik_lookup" in url:
            body = lookup_html
        elif "data.sec.gov/submissions" in url:
            body = json.dumps(submissions).encode()
        elif url.endswith("/agencies.json"):
            body = json.dumps(agencies).encode()
        elif "/documents.json?" in url:
            body = json.dumps(collection).encode()
        elif url.endswith("/documents/2026-15634.json"):
            body = json.dumps(detail).encode()
        elif url == fr_doc:
            body = b"Federal Register API documentation"
        else:
            return {"status": 0, "body": b"", "url": url}
        return {"status": 200, "body": body, "url": url, "content_type": accept}

    monkeypatch.setattr(institutional, "_search", fake_search)
    monkeypatch.setattr(institutional, "_get", fake_get)
    state_path = tmp_path / "state.json"
    result_path = tmp_path / "result.json"
    result = institutional.run(state_path=state_path, result_path=result_path,
                               minimum_later_delay_seconds=300)
    assert result["passed"] is True
    assert result["gate"]["successful_dependency_chains"] == 2
    assert result["gate"]["supplied_identifiers"] == 0
    assert result["gate"]["supplied_final_endpoints"] == 0
    assert result["gate"]["valid_dependency_graphs"] == 2
    assert result["gate"]["identity_continuity_passes"] == 2
    assert result["gate"]["malicious_or_invalid_chains_rejected"] == 8
    state = json.loads(state_path.read_text())
    for episode in state["episodes"]:
        episode["later_challenge"]["not_before_epoch"] = 0
    state_path.write_text(json.dumps(state))
    closed = institutional.close_later_challenges(state_path=state_path, result_path=result_path)
    assert closed["gate"]["later_retention_credits"] == 2
    assert closed["later_procedure_id"] == "procedure_multistep_institutional_later_retention_v1"
    assert all(row["status"] == "CONSEQUENCE_CONFIRMED" for row in closed["later_challenges"])
