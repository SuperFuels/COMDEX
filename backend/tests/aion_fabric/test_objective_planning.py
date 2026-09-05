from __future__ import annotations

import json
from types import SimpleNamespace

from backend.modules.aion_fabric.planning import AionObjectivePlanner


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, amount=None):
        return self.body if amount is None else self.body[:amount]


class _PlannerModel:
    def __init__(self) -> None:
        self.prompt = ""

    def generate(self, *, prompt, system, options):
        self.prompt = prompt
        content = {
            "title": "Granada Culture Weekend",
            "understanding": "Create a coherent two-day cultural visit rather than a list of links.",
            "summary": "A paced weekend centred on Granada's historic core, with ticketed attractions verified before travel.",
            "assumptions": ["Two adults", "Mid-range preferences"],
            "missing_constraints": ["Travel dates", "Starting point", "Budget"],
            "itinerary": [
                {"period": "Day 1", "plan": "Historic centre and Albaicin", "why": "Groups nearby sights"},
                {"period": "Day 2", "plan": "Timed Alhambra visit", "why": "Requires advance availability check"},
            ],
            "next_steps": ["Confirm dates", "Check official ticket availability"],
            "source_urls_used": ["https://example.org/granada-guide"],
        }
        return SimpleNamespace(response=json.dumps(content), model="test-local-model")


def test_objective_planner_builds_grounded_plan_instead_of_search_handoff(tmp_path):
    rss = b'''<?xml version="1.0"?><rss><channel><item>
    <title>Official Granada guide</title><link>https://example.org/granada-guide</link>
    <description>Visitor information and practical planning.</description></item></channel></rss>'''
    model = _PlannerModel()
    planner = AionObjectivePlanner(
        tmp_path,
        llm_service=model,
        urlopen=lambda request, timeout: _Response(rss),
    )
    result = planner.prepare(
        "plan a weekend in Granada for us",
        perception={"foreground_app_id": "netflix", "volume": 20},
    )
    assert result["destination"] == "Granada"
    assert result["title"] == "Granada Culture Weekend"
    assert len(result["itinerary"]) == 2
    assert result["missing_constraints"] == ["Travel dates", "Starting point", "Budget"]
    assert result["evidence"][0]["url"] == "https://example.org/granada-guide"
    assert result["provider"] == "comdex_local_llm"
    assert "Do not merely suggest a Google search" in model.prompt
    assert "https://example.org/granada-guide" in model.prompt
    assert planner.path.exists()


def test_objective_planner_rejects_non_json_model_output():
    try:
        AionObjectivePlanner._json_object("Here are some search links")
    except ValueError as exc:
        assert "JSON object" in str(exc)
    else:
        raise AssertionError("Unstructured model output must fail closed")
