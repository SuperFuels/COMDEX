from __future__ import annotations

from backend.modules.aion_fabric.intelligence import PilotIntelligencePolicy
from backend.modules.aion_fabric.research import AionTVResearch


EVIDENCE = [{
    "title": "Official current source",
    "url": "https://example.gov/current",
    "summary": "A current primary-source summary.",
}]


def test_native_mode_remains_useful_without_any_paid_provider(tmp_path, monkeypatch):
    research = AionTVResearch(tmp_path)
    research.policy.set_mode("native")
    monkeypatch.setattr(research, "_public_evidence", lambda query, mode: EVIDENCE)
    monkeypatch.setattr(research, "_local_synthesis", lambda *args, **kwargs: None)
    monkeypatch.setattr(research, "_gemini_synthesis", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Gemini must not run")))
    monkeypatch.setattr(research, "_openai_search", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("OpenAI must not run")))

    result = research.search("current official information")

    assert result["provider"] == "bounded_public_evidence"
    assert result["display_label"] == "AION + live public evidence"
    assert result["items"][0]["url"] == EVIDENCE[0]["url"]
    assert result["evidence_verification"]["verified_outside_model"] is True


def test_native_fact_check_is_useful_but_refuses_an_unverified_verdict(tmp_path, monkeypatch):
    research = AionTVResearch(tmp_path)
    research.policy.set_mode("native")
    monkeypatch.setattr(research, "_public_evidence", lambda query, mode: EVIDENCE)
    monkeypatch.setattr(research, "_local_synthesis", lambda *args, **kwargs: None)

    result = research.search("A current claim", mode="fact_check")

    assert result["verdict"] == "Unverifiable"
    assert result["confidence"] == 0.0
    assert result["items"]
    assert "paid AI" not in result["answer"] or result["provider"] == "bounded_public_evidence"


def test_gemini_mode_runs_only_after_local_and_public_routes(tmp_path, monkeypatch):
    research = AionTVResearch(tmp_path)
    research.policy.set_mode("gemini")
    order = []
    monkeypatch.setattr(research, "_public_evidence", lambda query, mode: order.append("public") or EVIDENCE)
    monkeypatch.setattr(research, "_local_synthesis", lambda *args, **kwargs: order.append("local") or None)
    monkeypatch.setattr(
        research,
        "_gemini_synthesis",
        lambda *args, **kwargs: order.append("gemini") or {
            "provider": "gemini_public_evidence_synthesis",
            "display_label": "AION + live public evidence",
            "items": EVIDENCE,
        },
    )
    monkeypatch.setattr(research, "_openai_search", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Boost must remain off")))

    result = research.search("compare current evidence")

    assert order == ["public", "local", "gemini"]
    assert result["provider"] == "gemini_public_evidence_synthesis"


def test_boost_uses_openai_only_after_native_and_gemini_fail(tmp_path, monkeypatch):
    research = AionTVResearch(tmp_path)
    research.policy.set_mode("boost")
    order = []
    monkeypatch.setattr(AionTVResearch, "_api_key", staticmethod(lambda: "sk-test-boost"))
    monkeypatch.setattr(research, "_public_evidence", lambda query, mode: order.append("public") or EVIDENCE)
    monkeypatch.setattr(research, "_local_synthesis", lambda *args, **kwargs: order.append("local") or None)
    monkeypatch.setattr(research, "_gemini_synthesis", lambda *args, **kwargs: order.append("gemini") or None)
    monkeypatch.setattr(
        research,
        "_openai_search",
        lambda *args, **kwargs: order.append("openai") or {"provider": "openai_responses_web_search", "display_label": "Pilot Boost"},
    )

    result = research.search("a difficult current question")

    assert order == ["public", "local", "gemini", "openai"]
    assert result["display_label"] == "Pilot Boost"


def test_policy_persists_without_storing_provider_secrets(tmp_path):
    policy = PilotIntelligencePolicy(tmp_path)
    status = policy.set_mode("gemini", gemini_grounding_enabled=False)

    assert status["mode"] == "gemini"
    assert status["label"] == "AION + Gemini"
    assert "api_key" not in policy.path.read_text(encoding="utf-8")
    assert PilotIntelligencePolicy(tmp_path).mode() == "gemini"


def test_model_cannot_introduce_an_unretrieved_source_url():
    result = AionTVResearch._bind_result_sources(
        {"answer": "Comparison", "items": [{
            "title": "Official current source",
            "reason": "Model explanation",
            "url": "https://invented.example/unsupported",
            "detail": "Detail",
        }]},
        EVIDENCE,
    )

    assert result["items"][0]["url"] == EVIDENCE[0]["url"]
    assert result["items"][0]["source_bound_outside_model"] is True
    assert result["_sources_bound_outside_model"] == 1


def test_recent_verified_research_is_reused_from_aion_memory(tmp_path, monkeypatch):
    research = AionTVResearch(tmp_path)
    research.policy.set_mode("native")
    monkeypatch.setattr(research, "_public_evidence", lambda query, mode: EVIDENCE)
    monkeypatch.setattr(research, "_local_synthesis", lambda *args, **kwargs: None)
    first = research.search("remember this current source")
    monkeypatch.setattr(research, "_public_evidence", lambda query, mode: (_ for _ in ()).throw(AssertionError("Network must not run")))

    second = research.search("remember this current source")

    assert first["items"] == second["items"]
    assert second["memory_reused"] is True
    assert second["route_trace"] == ["deterministic_local", "aion_memory"]
