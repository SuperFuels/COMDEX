import pytest
from backend.modules.knowledge_graph.indexes import curiosity_index
from backend.modules.state_manager import reset_container_state, get_active_container


@pytest.fixture(autouse=True)
def reset_container():
    # Ensure fresh container for each test
    reset_container_state()


def test_add_inferred_skill_basic():
    container = get_active_container()
    assert "curiosity_index" not in container.get("indexes", {})

    curiosity_index.add_inferred_skill(
        title="visual storytelling",
        tag="creativity",
        inferred_from="design thinking"
    )

    index = container["indexes"]["curiosity_index"]
    assert len(index) == 1

    entry = index[0]
    assert entry["type"] == "curiosity"
    assert entry["metadata"]["tag"] == "creativity"
    assert entry["metadata"]["inferred_from"] == "design thinking"
    assert entry["content"] == "visual storytelling"


def test_multiple_inferred_skills():
    curiosity_index.add_inferred_skill("emotional regulation", "emotion", "empathy")
    curiosity_index.add_inferred_skill("negotiation", "communication", "public speaking")

    index = get_active_container()["indexes"]["curiosity_index"]
    assert len(index) == 2

    tags = [e["metadata"]["tag"] for e in index]
    contents = [e["content"] for e in index]

    assert "emotion" in tags
    assert "communication" in tags
    assert "negotiation" in contents
    assert "emotional regulation" in contents


def test_index_structure_compliance():
    curiosity_index.add_inferred_skill("rhetoric", "language", "storytelling")
    entry = get_active_container()["indexes"]["curiosity_index"][0]

    assert "id" in entry
    assert "timestamp" in entry
    assert "hash" in entry
    assert "tags" in entry
    assert isinstance(entry["tags"], list)
    assert entry["plugin"] == "curiosity_engine"