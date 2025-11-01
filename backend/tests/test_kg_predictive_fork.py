# File: backend/tests/test_kg_predictive_fork.py
import asyncio
import types

from backend.modules.prediction.predictive_glyph_composer import PredictiveGlyphComposer, get_publish_kg_added

def test_predictive_fork_publish_and_relations(monkeypatch):
    # capture bus publishes
    published = {"calls": []}

    def fake_publish(payload: dict) -> bool:
        published["calls"].append(payload)
        return True  # simulate "published, not deduped"

    # monkeypatch the module-level getter to return our fake publisher
    monkeypatch.setattr(
        "backend.modules.prediction.predictive_glyph_composer.get_publish_kg_added",
        lambda: fake_publish,
        raising=True,
    )

    comp = PredictiveGlyphComposer(container_id="kg_pred_demo")

    # call the async commit helper via asyncio.run
    fork_id = "fork-123"
    relates_to = ["hash-drift-abc"]
    ok = asyncio.run(comp._commit_predictive_fork_to_kg(fork_id=fork_id, relates_to=relates_to))
    assert ok is True
    assert len(published["calls"]) == 1

    payload = published["calls"][0]
    assert payload["container_id"] == "kg_pred_demo"
    e = payload["entry"]
    assert e["id"] == fork_id
    assert e["type"] == "predictive_fork"
    assert "predictive" in e["tags"] and "fork" in e["tags"]
    # relation wiring
    assert e["meta"]["relates_to"] == relates_to
    assert e["meta"]["relation"] == "predicts"
    # deterministic hash formed from container|type|fork_id
    assert len(e["hash"]) == 64  # sha256 hex