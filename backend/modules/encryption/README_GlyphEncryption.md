✅ File: backend/modules/encryption/README_GlyphEncryption.md

# 🔐 Glyph Encryption System (GlyphNet Secure Delivery)

This module provides symbolic encryption and decryption tools used across GlyphNet, GlyphPush, GlyphHub, and `.dc` container export pipelines.

---

## ✨ Features

- ✅ RSA key generation and management (2048-bit)
- ✅ AES-256 fallback for local secure sessions
- ✅ Base64 encoding/decoding utilities
- ✅ High-level packet encryption for GlyphPush
- ✅ Container snapshot export + secure vault transmission
- ✅ Identity-based public key lookup system
- ✅ Seamless integration with `glyphnet_terminal.py`, `vault_exporter.py`, and future GlyphHub pushes

---

## 📂 File Structure

backend/modules/encryption/
│
├── glyphnet_crypto.py          # RSA + AES encryption core
├── glyph_vault.py              # Key storage and identity resolution
├── vault_exporter.py           # Export encrypted container state
├── vault_importer.py           # Re-import container from encrypted vault
└── README_GlyphEncryption.md   # This file

---

## 🔑 RSA Key Usage

```python
from backend.modules.encryption.glyphnet_crypto import generate_rsa_keypair

pub, priv = generate_rsa_keypair()
with open("keys/my_id_public.pem", "wb") as f: f.write(pub)
with open("keys/my_id_private.pem", "wb") as f: f.write(priv)

🔐 Encrypting a .gip Packet
from backend.modules.encryption.glyphnet_crypto import encrypt_packet

payload = {
    "type": "glyph_push",
    "sender": "aion",
    "payload": {"glyph": "⚛", "value": "dream"},
    "timestamp": 1723128499.1
}

encrypted = encrypt_packet(payload, recipient_public_key)
📤 Exporting an Encrypted Vault

from backend.modules.encryption.vault_exporter import export_container_vault

packet = export_container_vault("container_abc", target_id="remote_ai")

📥 Importing an Encrypted Vault

from backend.modules.encryption.vault_importer import import_encrypted_vault

result = import_encrypted_vault({
    "payload": encrypted_payload,
    "sender": "remote_ai"
})

🧪 Tests

Test coverage is provided in:

backend/tests/glyph_encryption_test.py

Run via:

python -m unittest backend/tests/glyph_encryption_test.py


⸻

🧬 Future Enhancements
	•	QGlyph-based symbolic encryption
	•	CodexLang contract-locked delivery
	•	Multi-identity entanglement channels
	•	Signature verification layer
	•	Trusted vault federation and shard delivery

⸻

Maintained by AION CodexCore Team | Phase 1 Complete ✅

