import json
import urllib.parse

from backend.modules.hexcore.open_information_action_invention import (
    _invent_pagination,
    _invent_xml,
    _run_pagination,
    _run_xml,
)


def _response(payload, content_type="application/json"):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return {"status": 200, "body": body, "oversize": False, "content_type": content_type}


def test_invented_pagination_handles_transfer_and_rejects_cycles() -> None:
    program, criticism = _invent_pagination()
    pages = {
        "https://authority.gov/page/1": {"results": [{"id": 1}, {"id": 2}], "next_page_url": "https://authority.gov/page/2"},
        "https://authority.gov/page/2": {"results": [{"id": 2}, {"id": 3}], "next_page_url": None},
    }
    outcome = _run_pagination(program, "https://authority.gov/page/1",
                              fetch=lambda url, accept: _response(pages[url]))
    assert outcome["passed"] is True
    assert outcome["unique_records"] == 3
    assert len(criticism) == 4

    cyclic = {"results": [{"id": 1}], "next_page_url": "https://authority.gov/cycle"}
    rejected = _run_pagination(program, "https://authority.gov/cycle",
                               fetch=lambda url, accept: _response(cyclic))
    assert rejected["passed"] is False
    assert rejected["reason"] == "continuation_cycle"

    world_bank = {
        1: [{"page": 1, "pages": 2}, [{"date": "2025", "value": 1}]],
        2: [{"page": 2, "pages": 2}, [{"date": "2024", "value": 2}]],
    }
    transferred = _run_pagination(
        program, "https://api.worldbank.org/data?page=1",
        fetch=lambda url, accept: _response(world_bank[int(dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))["page"])]),
    )
    assert transferred["passed"] is True
    assert transferred["unique_records"] == 2


def test_invented_xml_operator_transfers_and_rejects_entities() -> None:
    program, criticism = _invent_xml()
    federal = b"<RULE><AGENCY>Environmental Protection Agency</AGENCY><SUBJECT>Test rule</SUBJECT></RULE>"
    result = _run_xml(program, "https://authority.gov/rule.xml", ["AGENCY", "SUBJECT"],
                      fetch=lambda url, accept: _response(federal, "application/xml"))
    assert result["passed"] is True
    namespaced = b'<r:rfc xmlns:r="urn:rfc"><r:title>HTTP</r:title><r:abstract>Semantics</r:abstract></r:rfc>'
    transfer = _run_xml(program, "https://authority.gov/rfc.xml", ["title", "abstract"],
                        fetch=lambda url, accept: _response(namespaced, "application/xml"))
    assert transfer["passed"] is True
    hostile = b'<!DOCTYPE x [<!ENTITY leak SYSTEM "file:///etc/passwd">]><x>&leak;</x>'
    rejected = _run_xml(program, "https://authority.gov/bad.xml", ["x"],
                        fetch=lambda url, accept: _response(hostile, "application/xml"))
    assert rejected["passed"] is False
    assert rejected["reason"] == "unsafe_or_invalid_xml"
    assert len(criticism) == 3
