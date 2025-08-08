# tests/test_kg_bus_ingest.py
from backend.modules.sqi.sqi_event_bus import publish_kg_added
from backend.modules.knowledge_graph.indexes.knowledge_index import knowledge_index
import uuid, time

def test_bus_ingests_once():
    h = uuid.uuid4().hex
    payload = {
        "container_id": "ucs_ephemeral",
        "entry": {
            "id": "x",
            "hash": h,
            "type": "approval",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tags": ["📜","🧠","✅"],
            "plugin": None,
        },
    }
    n0 = len(knowledge_index.entries)
    assert publish_kg_added(payload) is True
    assert knowledge_index.get_by_hash(h) is not None
    assert len(knowledge_index.entries) == n0 + 1
    # re-publish same hash → no new entry
    publish_kg_added(payload)
    assert len(knowledge_index.entries) == n0 + 1