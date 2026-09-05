from __future__ import annotations

from backend.modules.aion_fabric.entertainment import EntertainmentIntelligence


class FakeResearcher:
    def search(self, query, *, mode):
        assert mode == "streaming"
        assert "Spain region" in query
        return {
            "answer": "Two current provider pages were found.",
            "provider": "test_current_evidence",
            "items": [
                {"title": "Official Netflix result", "url": "https://www.netflix.com/title/123", "reason": "Exact title", "detail": "Netflix"},
                {"title": "Catalogue result", "url": "https://example.org/title", "reason": "Check availability", "detail": "Catalogue"},
            ],
        }


def test_cross_service_discovery_labels_provider_evidence(tmp_path):
    intelligence = EntertainmentIntelligence(tmp_path, researcher=FakeResearcher())
    result = intelligence.discover("Where can we watch Dune Part Two?", minutes=150)
    assert result["items"][0]["provider"] == "Netflix"
    assert result["items"][0]["availability"] == "provider_or_catalogue_page_found"
    assert result["items"][1]["availability"] == "requires_current_provider_confirmation"
    assert result["criteria"]["region"] == "ES"


def test_watch_memory_is_persistent_and_deduplicated(tmp_path):
    intelligence = EntertainmentIntelligence(tmp_path, researcher=FakeResearcher())
    intelligence.remember("The Crown", "watched")
    intelligence.remember("the crown", "avoid")
    snapshot = EntertainmentIntelligence(tmp_path, researcher=FakeResearcher()).snapshot()
    assert snapshot["history_count"] == 1
    assert snapshot["preferred_services"] == ["Netflix", "Prime Video", "Disney+", "YouTube"]

