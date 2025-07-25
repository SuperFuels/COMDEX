# 📁 backend/tests/test_lean_scroll_output.py

from fastapi.testclient import TestClient
from backend.main import app
from backend.modules.consciousness.state_manager import STATE

client = TestClient(app)

def test_lean_scroll_output():
    # Simulate a .dc container imported from Lean
    lean_container = {
        "id": "lean::test.lean",
        "metadata": {
            "origin": "lean_import",
            "logic_type": "lean_math"
        },
        "symbolic_logic": [
            {
                "symbol": "⟦ Theorem ⟧",
                "name": "add_comm",
                "logic": "a + b = b + a",
                "args": [
                    {"type": "Proof", "value": "Nat.add_comm a b"}
                ]
            },
            {
                "symbol": "⟦ Theorem ⟧",
                "name": "zero_add",
                "logic": "0 + n = n",
                "args": [
                    {"type": "Proof", "value": "Nat.zero_add n"}
                ]
            }
        ]
    }

    # Inject container into state
    STATE.set_current_container(lean_container)

    # Call scroll builder route
    response = client.get("/api/build_scroll")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    scroll = data["scroll"]

    # Check formatted Lean theorems
    assert "📘 Theorem add_comm: a + b = b + a" in scroll
    assert "🧠 Proof: Nat.add_comm a b" in scroll
    assert "📘 Theorem zero_add: 0 + n = n" in scroll
    assert "🧠 Proof: Nat.zero_add n" in scroll