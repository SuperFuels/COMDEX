import json
from pathlib import Path

from backend.modules.hexcore.continuous_knowledge_entanglement import run


def test_entanglement_discovers_prerequisite_chain_without_merging_claims(tmp_path: Path):
    competency = {
        "subjects": {
            "mathematics": {"name": "Mathematics", "group": "math", "subskills": ["probability"]},
            "investing": {"name": "Business investing", "group": "business", "subskills": ["valuation"]},
            "hedge_funds": {"name": "Hedge funds", "group": "finance", "subskills": ["portfolio"]},
            "poetry": {"name": "Poetry", "group": "creative", "subskills": ["metre"]},
        }, "evidence": [],
    }
    curriculum = {
        "subjects": {
            "mathematics": {"prerequisites": []},
            "investing": {"prerequisites": ["mathematics"]},
            "hedge_funds": {"prerequisites": ["investing"]},
            "poetry": {"prerequisites": []},
        },
        "cross_domain_bridges": [],
    }
    competency_path, curriculum_path = tmp_path / "competency.json", tmp_path / "curriculum.json"
    competency_path.write_text(json.dumps(competency), encoding="utf-8")
    curriculum_path.write_text(json.dumps(curriculum), encoding="utf-8")
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps({"containers": [], "shared": []}), encoding="utf-8")
    result = run(
        competency_state_path=competency_path, curriculum_path=curriculum_path,
        state_path=tmp_path / "state.json", container_path=tmp_path / "associations.json",
        index_path=index_path, result_path=tmp_path / "result.json", now=100,
    )
    relationships = json.loads((tmp_path / "state.json").read_text())["relationships"].values()
    assert any(row["source"] == "mathematics" and row["target"] == "hedge_funds"
               and row["relation"] == "TRANSITIVELY_ENABLES" for row in relationships)
    assert not any("poetry" in {row["source"], row["target"]} for row in relationships)
    assert result["summary"]["competence_awarded"] is False
    assert json.loads((tmp_path / "associations.json").read_text())["causal_claims_awarded"] is False
