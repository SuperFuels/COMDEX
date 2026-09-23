from __future__ import annotations

import json

from backend.modules.aion_fabric.research import AionTVResearch


class _StaticJSONResponse:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, amount=None):
        return json.dumps(self.value).encode()


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, amount=None):
        result = {
            "answer": "Two current options were found.",
            "items": [
                {
                    "title": "Example Locksmith",
                    "reason": "Official business page lists the service area.",
                    "url": "https://example.com/locksmith",
                    "detail": "Albox area",
                },
                {
                    "title": "Blocked local URL",
                    "reason": "Must not be projected.",
                    "url": "http://192.168.1.1/admin",
                    "detail": "unsafe",
                },
            ],
        }
        return json.dumps({"model": "test-model", "output_text": json.dumps(result)}).encode()


class _FactCheckResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, amount=None):
        result = {
            "answer": "Misleading: the figures use different periods.",
            "verdict": "Misleading",
            "confidence": 0.84,
            "claims": [{
                "claim": "The rate is two percent.",
                "verdict": "Misleading",
                "explanation": "The programme mixed monthly and annual measures.",
                "confidence": 0.84,
                "source_indexes": [1],
                "date_scope": "August 2026",
            }],
            "context_notes": ["Measurement periods differ."],
            "items": [{
                "title": "Official release",
                "reason": "Primary evidence",
                "url": "https://example.gov/release",
                "detail": "Current release",
            }],
        }
        return json.dumps({"model": "test-model", "output_text": json.dumps(result)}).encode()


def test_research_keeps_structured_https_projection_and_not_raw_response(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-never-persisted")
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: _Response())
    research = AionTVResearch(tmp_path)
    research.policy.set_mode("boost")
    monkeypatch.setattr(research, "_public_evidence", lambda query, mode: [])
    monkeypatch.setattr(AionTVResearch, "_gemini_credentials", staticmethod(lambda: None))
    result = research.search("find a locksmith in Albox")
    assert result["answer"] == "Two current options were found."
    assert len(result["items"]) == 1
    assert result["items"][0]["url"] == "https://example.com/locksmith"
    assert result["raw_response_retained"] is False
    persisted = research.path.read_text(encoding="utf-8")
    assert "sk-test-key-never-persisted" not in persisted
    assert research.result_url(1) == "https://example.com/locksmith"


def test_research_falls_back_to_truthful_live_handoffs_without_valid_key(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    monkeypatch.setattr(AionTVResearch, "_api_key", staticmethod(lambda: None))
    monkeypatch.setattr(AionTVResearch, "_gemini_credentials", staticmethod(lambda: None))
    research = AionTVResearch(tmp_path)
    monkeypatch.setattr(research, "_public_evidence", lambda query, mode: [])
    result = research.search("a locksmith in Albox")
    assert result["provider"] == "safe_search_handoff"
    assert "instead of inventing" in result["answer"]
    assert result["items"][0]["url"].startswith("https://www.google.com/maps/search/")


def test_research_uses_active_project_secret_when_shell_value_is_malformed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-usable-shell-value")
    monkeypatch.setattr(
        AionTVResearch,
        "_configured_secret",
        staticmethod(lambda name: "sk-project-file-key" if name == "OPENAI_API_KEY" else ""),
    )

    assert AionTVResearch._api_key() == "sk-project-file-key"


def test_fact_check_fallback_refuses_to_invent_a_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr(AionTVResearch, "_api_key", staticmethod(lambda: None))
    monkeypatch.setattr(AionTVResearch, "_gemini_credentials", staticmethod(lambda: None))
    research = AionTVResearch(tmp_path)
    monkeypatch.setattr(research, "_public_evidence", lambda query, mode: [])
    result = research.search("A current television claim", mode="fact_check")
    assert result["provider"] == "safe_search_handoff"
    assert "cannot give a reliable verdict" in result["answer"]
    assert result["items"][0]["url"].startswith("https://www.google.com/search?")


def test_gemini_fallback_separates_grounded_research_from_json_formatting(tmp_path, monkeypatch):
    grounded = {
        "candidates": [{
            "finishReason": "STOP",
            "content": {"parts": [{"text": "The grounded report supports the claim."}]},
            "groundingMetadata": {"groundingChunks": [{
                "web": {
                    "title": "Official evidence",
                    "uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/test",
                }
            }]},
        }]
    }
    structured_result = {
        "answer": "Supported: authoritative evidence agrees.",
        "verdict": "Supported",
        "confidence": 0.93,
        "claims": [{
            "claim": "The checkable claim.",
            "verdict": "Supported",
            "explanation": "The grounded evidence agrees.",
            "confidence": 0.93,
            "source_indexes": [1],
            "date_scope": "Current",
        }],
        "context_notes": [],
        "items": [{
            "title": "Official evidence",
            "reason": "Grounded source",
            "url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/test",
            "detail": "Current evidence",
        }],
    }
    structured = {
        "candidates": [{
            "finishReason": "STOP",
            "content": {"parts": [{"text": json.dumps(structured_result)}]},
        }]
    }
    responses = iter((_StaticJSONResponse(grounded), _StaticJSONResponse(structured)))
    requests = []

    def urlopen(request, timeout):
        requests.append(json.loads(request.data.decode("utf-8")))
        return next(responses)

    monkeypatch.setattr(AionTVResearch, "_gemini_credentials", staticmethod(lambda: ("gemini-test-key-123456", "gemini-test")))
    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    result = AionTVResearch(tmp_path)._gemini_search(
        "A current claim",
        mode="fact_check",
        schema={"type": "object"},
        instructions="Use authoritative evidence.",
    )

    assert result["provider"] == "gemini_google_search_grounding"
    assert result["verdict"] == "Supported"
    assert result["items"][0]["title"] == "Official evidence"
    assert requests[0]["tools"] == [{"googleSearch": {}}]
    assert "responseMimeType" not in requests[0]["generationConfig"]
    assert "tools" not in requests[1]
    assert requests[1]["generationConfig"]["responseMimeType"] == "application/json"
    assert requests[1]["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}


def test_fact_check_uses_strict_claim_schema_and_does_not_store_provider_response(tmp_path, monkeypatch):
    captured = {}

    def urlopen(request, timeout):
        captured.update(json.loads(request.data.decode("utf-8")))
        return _FactCheckResponse()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-never-persisted")
    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    research = AionTVResearch(tmp_path)
    research.policy.set_mode("boost")
    monkeypatch.setattr(research, "_public_evidence", lambda query, mode: [])
    monkeypatch.setattr(AionTVResearch, "_gemini_credentials", staticmethod(lambda: None))
    result = research.search("A current television claim", mode="fact_check")

    assert captured["store"] is False
    assert captured["include"] == ["web_search_call.action.sources"]
    schema = captured["text"]["format"]["schema"]
    assert {"verdict", "confidence", "claims", "context_notes"}.issubset(schema["required"])
    assert schema["additionalProperties"] is False
    assert result["verdict"] == "Misleading"
    assert result["confidence"] == 0.84
    assert result["claims"][0]["source_indexes"] == [1]
    assert result["raw_response_retained"] is False


def test_latest_migrates_abandoned_fallback_links_back_to_google(tmp_path):
    research = AionTVResearch(tmp_path)
    research.path.write_text(json.dumps({
        "query": "extendable ladders",
        "mode": "general",
        "provider": "safe_search_handoff",
        "items": [{"url": "https://search.brave.com/search?q=extendable+ladders"}],
    }), encoding="utf-8")
    latest = research.latest()
    assert latest is not None
    assert all("search.brave.com" not in item["url"] for item in latest["items"])
    assert any("google.com" in item["url"] for item in latest["items"])


def test_netflix_title_resolver_selects_exact_official_title(tmp_path, monkeypatch):
    search = json.dumps({"search": [{"id": "Q1"}, {"id": "Q2"}]}).encode()
    entities = json.dumps({"entities": {
        "Q1": {
            "labels": {"en": {"value": "The Crowned"}},
            "descriptions": {"en": {"value": "example series"}},
            "claims": {"P1874": [{"mainsnak": {"datavalue": {"value": "99999"}}}]},
        },
        "Q2": {
            "labels": {"en": {"value": "The Crown"}},
            "descriptions": {"en": {"value": "British television series"}},
            "claims": {"P1874": [{"mainsnak": {"datavalue": {"value": "80025678"}}}]},
        },
    }}).encode()
    official = b'''<html><head><meta property="og:title" content="Watch The Crown | Netflix Official Site"></head></html>'''

    class SearchResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, amount=None): return page

    responses = iter((search, entities, official))

    def urlopen(request, timeout):
        response = SearchResponse()
        response.read = lambda amount=None: next(responses)
        return response

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    result = AionTVResearch(tmp_path).resolve_netflix_title("The Crown")
    assert result["title_id"] == "80025678"
    assert result["title"] == "The Crown"
    assert result["url"] == "https://www.netflix.com/title/80025678"
