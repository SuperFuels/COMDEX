import unittest
import json
import time

from backend.modules.containers.container_runtime import create_test_container, get_container_by_id
from backend.modules.encryption.vault_exporter import export_container_vault
from backend.modules.encryption.vault_importer import import_encrypted_vault
from backend.modules.encryption.glyph_vault import GlyphVault


class GlyphEncryptionTestCase(unittest.TestCase):

    def setUp(self):
        # Setup a test container with basic state
        self.container_id = f"test_container_{int(time.time())}"
        self.target_id = "test_recipient"
        self.sender_id = "vault_exporter"

        # Simulate container
        create_test_container(self.container_id, initial_state={"value": 42})
        vault = GlyphVault(self.container_id)
        vault.generate_keys()  # Generate keypair for sender
        vault.generate_keys(identity=self.target_id)  # Generate recipient keypair

    def test_encrypted_export_and_import(self):
        # Export encrypted vault
        result = export_container_vault(self.container_id, target_id=self.target_id)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["encrypted"])
        encrypted_payload = result["payload"]

        # Import vault using recipient key
        import_result = import_encrypted_vault({
            "payload": encrypted_payload,
            "sender": self.sender_id
        })

        self.assertEqual(import_result["status"], "ok")
        imported_id = import_result["container_id"]
        imported_container = get_container_by_id(imported_id)
        self.assertIsNotNone(imported_container)
        self.assertEqual(imported_container.state.get("value"), 42)

    def test_export_without_encryption(self):
        result = export_container_vault(self.container_id)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["encrypted"])
        self.assertIn("payload", result)

    def tearDown(self):
        # Optionally clean up keys or state
        pass


if __name__ == '__main__':
    unittest.main()