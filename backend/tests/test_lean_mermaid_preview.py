import os
import tempfile
from backend.modules.lean.lean_proofviz import mermaidify, write_mermaid

# Minimal mock container for testing
MOCK_CONTAINER = {
    "type": "dc",
    "id": "test123",
    "symbolic_logic": [
        {
            "name": "A",
            "symbol": "⊢",
            "logic": "True",
            "depends_on": ["B"],
        },
        {
            "name": "B",
            "symbol": "⊢",
            "logic": "False",
            "depends_on": [],
        },
    ],
}

def test_mermaidify_returns_graph():
    mmd = mermaidify(MOCK_CONTAINER)
    assert isinstance(mmd, str)
    # Mermaid diagrams should start with "graph" or "flowchart"
    assert mmd.strip().startswith(("graph", "flowchart", "```mermaid"))

def test_write_mermaid_to_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "graph.mmd")
        mmd = write_mermaid(MOCK_CONTAINER, path)
        # Content returned matches content written
        with open(path, "r", encoding="utf-8") as f:
            written = f.read()
        assert mmd.strip() == written.strip()
        assert "graph" in written or "flowchart" in written

def test_mermaidify_includes_nodes():
    mmd = mermaidify(MOCK_CONTAINER)
    # Ensure nodes A and B appear in the output graph
    assert "A" in mmd
    assert "B" in mmd