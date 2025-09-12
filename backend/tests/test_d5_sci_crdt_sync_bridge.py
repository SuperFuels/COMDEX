# File: backend/tests/test_d5_sci_crdt_sync_bridge.py

import unittest
from backend.modules.sci.sci_crdt_sync_bridge import SessionCRDTState

class TestSessionCRDTState(unittest.TestCase):

    def setUp(self):
        self.crdt = SessionCRDTState()

    def test_apply_node_update(self):
        node = {"id": "n1", "label": "glyph()"}
        update = {"type": "node", "payload": node}
        result = self.crdt.apply_update(update)
        self.assertTrue(result)
        self.assertIn("n1", self.crdt.nodes)
        self.assertEqual(self.crdt.nodes["n1"]["label"], "glyph()")

    def test_apply_link_update(self):
        link = {"id": "l1", "source": "n1", "target": "n2"}
        update = {"type": "link", "payload": link}
        result = self.crdt.apply_update(update)
        self.assertTrue(result)
        self.assertIn("l1", self.crdt.links)

    def test_apply_invalid_update_type(self):
        update = {"type": "unknown", "payload": {"id": "x1"}}
        result = self.crdt.apply_update(update)
        self.assertFalse(result)

    def test_state_version_increments(self):
        update1 = {"type": "node", "payload": {"id": "n1", "label": "glyph()"}}
        update2 = {"type": "glyph", "payload": {"id": "g1", "type": "symbol"}}
        self.crdt.apply_update(update1)
        self.crdt.apply_update(update2)
        self.assertEqual(self.crdt.version, 2)

    def test_get_state_snapshot(self):
        node = {"id": "n1", "label": "start()"}
        self.crdt.apply_update({"type": "node", "payload": node})
        snapshot = self.crdt.get_state()
        self.assertIn("nodes", snapshot)
        self.assertEqual(snapshot["nodes"][0]["label"], "start()")
        self.assertIn("version", snapshot)
        self.assertGreaterEqual(snapshot["timestamp"], 0)

if __name__ == '__main__':
    unittest.main()