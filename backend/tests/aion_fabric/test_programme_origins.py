from __future__ import annotations

import io
import json
import urllib.parse

from backend.modules.aion_fabric.programme_origins import ProgrammeOriginEvidence
from backend.modules.aion_fabric.voice import parse_voice_intent


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def _statement(entity_id):
    return {"mainsnak": {"datavalue": {"value": {"id": entity_id}}}}


def test_structured_filming_location_and_original_source_are_exact_and_cached(tmp_path, monkeypatch):
    search = {"search": [{"id": "Q123", "label": "The Crown", "description": "television series"}]}
    entity = {
        "entities": {
            "Q123": {
                "claims": {
                    "P915": [_statement("Q84")],
                    "P840": [_statement("Q145")],
                    "P144": [_statement("Q999")],
                    "P495": [_statement("Q145")],
                    "P364": [_statement("Q1860")],
                    "P449": [_statement("Q907311")],
                }
            }
        }
    }
    labels = {
        "entities": {
            "Q84": {"labels": {"en": {"value": "London"}}},
            "Q145": {"labels": {"en": {"value": "United Kingdom"}}},
            "Q999": {"labels": {"en": {"value": "historical events"}}},
            "Q1860": {"labels": {"en": {"value": "English"}}},
            "Q907311": {"labels": {"en": {"value": "Netflix"}}},
        }
    }
    calls = []

    def open_wikidata(request, timeout=0):
        calls.append(request.full_url)
        if "Special:EntityData" in request.full_url:
            payload = entity
        else:
            query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)
            payload = labels if query.get("action") == ["wbgetentities"] else search
        return Response(json.dumps(payload).encode())

    monkeypatch.setattr(
        "backend.modules.aion_fabric.programme_origins.urllib.request.urlopen",
        open_wikidata,
    )
    service = ProgrammeOriginEvidence(tmp_path)
    filming = service.lookup(
        programme={"title": "The Crown", "stable": True},
        question_kind="filming_location",
    )
    assert filming["answer"] == "The structured source lists these filming locations for The Crown: London."
    assert filming["evidence"]["based_on"][0]["label"] == "historical events"
    assert filming["safety"]["current_scene_location_claimed"] is False
    assert filming["presentation"]["playback_preserved"] is True
    assert len(calls) == 3

    source = service.lookup(
        programme={"title": "The Crown", "stable": True},
        question_kind="original_source",
    )
    assert source["answer"] == "The structured source says The Crown is based on historical events."
    assert source["cache_hit"] is True
    assert len(calls) == 3


def test_ambiguous_programme_origin_fails_closed(tmp_path, monkeypatch):
    payload = {"search": [
        {"id": "Q1", "label": "Utopia", "description": "British television series"},
        {"id": "Q2", "label": "Utopia", "description": "American television series"},
    ]}
    monkeypatch.setattr(
        "backend.modules.aion_fabric.programme_origins.urllib.request.urlopen",
        lambda request, timeout=0: Response(json.dumps(payload).encode()),
    )
    result = ProgrammeOriginEvidence(tmp_path).lookup(
        programme={"title": "Utopia", "stable": True},
        question_kind="setting",
    )
    assert result["confidence"] == 0
    assert "will not guess" in result["answer"]


def test_programme_origin_voice_routes_are_explicit():
    assert parse_voice_intent("Pilot, where was this filmed?").arguments == {"kind": "filming_location"}
    assert parse_voice_intent("Pilot, where is this set?").arguments == {"kind": "setting"}
    assert parse_voice_intent("Pilot, is this based on a book?").arguments == {"kind": "original_source"}
