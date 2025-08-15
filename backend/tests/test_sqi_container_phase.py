from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_allocate_materialize_and_lookup():
    r = client.post("/sqi/allocate", json={"kind":"fact","domain":"physics.em","name":"maxwell_core"})
    assert r.status_code == 200
    cid = r.json()["entry"]["id"]
    r2 = client.post(f"/sqi/materialize/{cid}")
    assert r2.status_code == 200
    r3 = client.get("/sqi/lookup/physics.em")
    assert cid in r3.json()["containers"]

def test_search_and_kg_payload():
    client.post("/sqi/allocate", json={"kind":"note","domain":"math.calculus","name":"diff_sin"})
    r = client.get("/sqi/search", params={"q":"diff", "domain":"math.calculus"})
    assert r.status_code == 200 and r.json()["results"]
    cid = r.json()["results"][0]["id"]
    kg = client.get(f"/sqi/kg-payload/{cid}")
    assert kg.status_code == 200
    node = kg.json()["node"]
    assert "address" in node and "ghx" in node