from __future__ import annotations

import io
import json

from backend.modules.aion_fabric.programme_companion import EvidenceBackedProgrammeCompanion
from backend.modules.aion_fabric.voice import parse_voice_intent


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


CAST = [
    {
        "person": {"id": 101, "name": "Claire Foy", "url": "https://www.tvmaze.com/people/101/claire-foy"},
        "character": {"id": 201, "name": "Queen Elizabeth II", "url": "https://www.tvmaze.com/characters/201/queen-elizabeth-ii"},
    },
    {
        "person": {"id": 102, "name": "Matt Smith", "url": "https://www.tvmaze.com/people/102/matt-smith"},
        "character": {"id": 202, "name": "Prince Philip", "url": "https://www.tvmaze.com/characters/202/prince-philip"},
    },
]


def test_verified_programme_cast_is_evidence_backed_without_face_identification(tmp_path, monkeypatch):
    calls = []

    def open_cast(request, timeout=0):
        calls.append(request.full_url)
        return Response(json.dumps(CAST).encode())

    monkeypatch.setattr(
        "backend.modules.aion_fabric.programme_companion.urllib.request.urlopen",
        open_cast,
    )
    service = EvidenceBackedProgrammeCompanion(tmp_path)
    result = service.lookup(
        programme={"title": "The Crown", "stable": True, "current_playback_verified": False},
        provider_metadata={
            "provider": "programme_catalogue",
            "content_id": "3594",
            "metadata_status": "public_catalogue_exact_match",
            "catalogue_identity_verified": True,
        },
        question_kind="visible_actor",
    )

    assert result["programme"]["catalogue_id"] == "3594"
    assert result["cast"][0] == {
        "person_id": "101",
        "person": "Claire Foy",
        "character": "Queen Elizabeth II",
        "person_url": "https://www.tvmaze.com/people/101/claire-foy",
        "character_url": "https://www.tvmaze.com/characters/201/queen-elizabeth-ii",
    }
    assert result["answer"].startswith("I cannot identify the person currently visible.")
    assert result["safety"]["face_recognition_used"] is False
    assert result["safety"]["visible_person_identified"] is False
    assert result["presentation"]["playback_preserved"] is True
    assert calls == ["https://api.tvmaze.com/shows/3594/cast"]

    cached = service.lookup(
        programme={"title": "The Crown", "stable": True},
        provider_metadata={"content_id": "3594", "metadata_status": "public_catalogue_exact_match"},
    )
    assert cached["catalogue_cache_hit"] is True
    assert len(calls) == 1


def test_exact_character_question_returns_verified_actor(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.modules.aion_fabric.programme_companion.urllib.request.urlopen",
        lambda request, timeout=0: Response(json.dumps(CAST).encode()),
    )
    result = EvidenceBackedProgrammeCompanion(tmp_path).lookup(
        programme={"title": "The Crown", "stable": True},
        provider_metadata={"content_id": "3594", "metadata_status": "public_catalogue_exact_match"},
        question_kind="character",
        character="Queen Elizabeth II",
    )
    assert result["answer"] == "In The Crown, Queen Elizabeth II is played by Claire Foy."
    assert result["matches"][0]["person"] == "Claire Foy"


def test_cast_lookup_fails_closed_without_stable_programme_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.modules.aion_fabric.programme_companion.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network must not be used")),
    )
    result = EvidenceBackedProgrammeCompanion(tmp_path).lookup(
        programme={"title": "The Crown", "stable": False},
        provider_metadata={},
    )
    assert result["confidence"] == 0
    assert result["cast"] == []
    assert "stable programme identity" in result["answer"]


def test_cast_voice_commands_are_deterministic():
    visible = parse_voice_intent("Pilot, who is that actor?")
    cast = parse_voice_intent("Pilot, show me the cast")
    character = parse_voice_intent("Pilot, who plays Queen Elizabeth II?")
    credits = parse_voice_intent("Pilot, what else has Claire Foy been in?")

    assert visible.action == "programme_cast"
    assert visible.arguments == {"kind": "visible_actor"}
    assert cast.action == "programme_cast"
    assert cast.arguments == {"kind": "cast"}
    assert character.action == "programme_cast"
    assert character.arguments == {"kind": "character", "character": "queen elizabeth ii"}
    assert credits.action == "programme_cast"
    assert credits.arguments == {"kind": "credits", "person": "claire foy"}


def test_broader_person_credits_require_exact_current_cast_match(tmp_path, monkeypatch):
    credit_rows = [
        {"_embedded": {"show": {"id": 3594, "name": "The Crown", "url": "https://www.tvmaze.com/shows/3594/the-crown"}}},
        {"_embedded": {"show": {"id": 526, "name": "Wolf Hall", "premiered": "2015-01-21", "url": "https://www.tvmaze.com/shows/526/wolf-hall"}}},
        {"_embedded": {"show": {"id": 7000, "name": "A Very British Scandal", "url": "https://www.tvmaze.com/shows/7000/a-very-british-scandal"}}},
    ]
    calls = []

    def open_evidence(request, timeout=0):
        calls.append(request.full_url)
        payload = credit_rows if "castcredits" in request.full_url else CAST
        return Response(json.dumps(payload).encode())

    monkeypatch.setattr(
        "backend.modules.aion_fabric.programme_companion.urllib.request.urlopen",
        open_evidence,
    )
    service = EvidenceBackedProgrammeCompanion(tmp_path)
    result = service.lookup(
        programme={"title": "The Crown", "stable": True},
        provider_metadata={"content_id": "3594", "metadata_status": "public_catalogue_exact_match"},
        question_kind="credits",
        person="Claire Foy",
    )

    assert "Wolf Hall" in result["answer"]
    assert "A Very British Scandal" in result["answer"]
    assert result["person_matches"][0]["person"] == "Claire Foy"
    assert [item["title"] for item in result["credits"]] == ["The Crown", "Wolf Hall", "A Very British Scandal"]
    assert calls == [
        "https://api.tvmaze.com/shows/3594/cast",
        "https://api.tvmaze.com/people/101/castcredits?embed=show",
    ]

    cached = service.lookup(
        programme={"title": "The Crown", "stable": True},
        provider_metadata={"content_id": "3594", "metadata_status": "public_catalogue_exact_match"},
        question_kind="credits",
        person="Claire Foy",
    )
    assert cached["catalogue_cache_hit"] is True
    assert cached["credits_cache_hit"] is True
    assert len(calls) == 2
