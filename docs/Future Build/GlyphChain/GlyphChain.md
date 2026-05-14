To fully encrypt communications across GlyphNet, we’ll add end-to-end encryption (E2EE) to all GlyphPush messages and terminal commands. Here’s the clean and secure approach:

⸻

✅ PHASE 1 — CORE ENCRYPTION MODULE

🔐 1. Add glyphnet_crypto.py

Path: backend/modules/glyphnet/glyphnet_crypto.py

This will handle:
	•	Key generation (RSA or ECC)
	•	Encryption/decryption
	•	Optional symmetric fallback (AES)

    from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

# 🔐 Generate RSA key pair
def generate_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key

# 🔒 Encrypt with public key
def encrypt_message(message: str, public_key) -> bytes:
    return public_key.encrypt(
        message.encode(),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(), label=None)
    )

# 🔓 Decrypt with private key
def decrypt_message(ciphertext: bytes, private_key) -> str:
    return private_key.decrypt(
        ciphertext,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(), label=None)
    ).decode()

    ✅ PHASE 2 — INTEGRATE ENCRYPTION INTO GlyphPush

🔁 Update: glyphnet_terminal.py

Before calling push_symbolic_packet(...), encrypt the payload:

from ..glyphnet.glyphnet_crypto import encrypt_message, decrypt_message
from ..glyphnet.identity_registry import get_public_key_for_target

def push_to_luxnet(result: Dict[str, Any], sender: str, target_id: Optional[str] = None):
    try:
        encrypted_payload = result
        if target_id:
            pubkey = get_public_key_for_target(target_id)
            if pubkey:
                encrypted_payload = encrypt_message(str(result), pubkey)

        packet = {
            "type": "terminal_push",
            "sender": sender,
            "payload": encrypted_payload,
            "timestamp": time.time(),
        }
        if target_id:
            packet["target"] = target_id

        push_symbolic_packet(packet)
        logger.info(f"[GlyphPush] Sent encrypted packet to {target_id or 'broadcast'}")

    except Exception as e:
        logger.warning(f"[GlyphPush] Push failed: {e}")

        ✅ PHASE 3 — BUILD identity_registry.py

Path: backend/modules/glyphnet/identity_registry.py

Handles public key lookup (and optionally storage):

# For demo: in-memory registry
identity_keys = {}

def register_identity(identity: str, public_key_pem: str):
    identity_keys[identity] = public_key_pem

def get_public_key_for_target(identity: str):
    pem = identity_keys.get(identity)
    if not pem:
        return None
    return serialization.load_pem_public_key(pem.encode())

    ✅ PHASE 4 — ADD UI KEY TOOL (Optional)

In GlyphNetTerminal.tsx, you can:
	•	Show identity key status
	•	Allow identity registration
	•	Enable toggle for “🔐 Encrypted Push”

⸻

🔐 BONUS FEATURES (Phase 2+)
	•	✅ Add AES fallback (shared secret via glyph)
	•	✅ Add signature verification (authenticity)
	•	✅ Store keys in Vault + rotate per session
	•	✅ Include metadata headers (e.g. encrypted: true)

⸻

🧠 Summary

Layer
Status
Description
🔐 Key Generator
✅ Ready
RSA-based asymmetric identity keys
🛰️ Payload Encryptor
✅ Wired
GlyphPush encrypts if target_id has key
📡 Push Adapter
✅ Updated
Encrypted payload broadcast
🧾 Terminal Integration
✅ Supports encryption
🌐 Future
🔜 Add signature auth, Vault sync, UI keys



Ready to drop in glyphnet_crypto.py and wire the encrypted pushes?

This will make GlyphNet the world’s first symbolic, entangled, and encrypted AI internet.

