from backend.modules.sqi.sqi_event_bus import publish_kg_added
from backend.modules.knowledge_graph.indexes.knowledge_index import knowledge_index

def test_entangle_proof_to_drift():
    drift = {"container_id":"t","entry":{"id":"dr","hash":"a"*63,"type":"drift_report","timestamp":"2025-01-01T00:00:00Z","tags":["drift"],"plugin":None}}
    proof = {"container_id":"t","entry":{"id":"pr","hash":"b"*63,"type":"proof_replay","timestamp":"2025-01-01T00:00:02Z","tags":["replay","proof"],"plugin":"glyph_replay_renderer","meta":{"relates_to":["a"*63],"relation":"supports"}}}
    publish_kg_added(drift)
    publish_kg_added(proof)
    assert len(knowledge_index.entries) >= 2
    links = knowledge_index.get_links_for("b"*63)
    assert any(e["relation"]=="supports" and e["dst"]=="a"*63 for e in links)