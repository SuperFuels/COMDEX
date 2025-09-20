# File: backend/modules/glyphnet/glyphnet_crypto.py

import rsa
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from typing import Tuple, Optional, Dict, Any

from backend.modules.glyphnet.ephemeral_key_manager import get_ephemeral_key_manager
from backend.modules.glyphnet.symbolic_key_derivation import SymbolicKeyDerivation

# Optional semantic tagging (QGlyph locks)
try:
    from backend.modules.encryption.encryption_utils import tag_with_qglyph_lock
except ImportError:
    tag_with_qglyph_lock = None  # graceful fallback

# ✅ Persistent symbolic derivation engine
symbolic_key_deriver = SymbolicKeyDerivation()


# ──────────────────────────────────────────────
# 🔑 RSA Key Utilities
# ──────────────────────────────────────────────
def generate_rsa_keypair(bits: int = 2048) -> Tuple[bytes, bytes]:
    """Generate an RSA public/private keypair (PEM-encoded)."""
    pubkey, privkey = rsa.newkeys(bits)
    return pubkey.save_pkcs1(), privkey.save_pkcs1()


def rsa_encrypt(message: bytes, public_key_pem: bytes) -> bytes:
    public_key = rsa.PublicKey.load_pkcs1(public_key_pem)
    return rsa.encrypt(message, public_key)


def rsa_decrypt(ciphertext: bytes, private_key_pem: bytes) -> bytes:
    private_key = rsa.PrivateKey.load_pkcs1(private_key_pem)
    return rsa.decrypt(ciphertext, private_key)


# ──────────────────────────────────────────────
# 🔐 AES Symmetric Encryption
# ──────────────────────────────────────────────
def aes_encrypt(message: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
    """Encrypt message with AES-256 EAX. Returns (nonce, tag, ciphertext)."""
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(message)
    return cipher.nonce, tag, ciphertext


def aes_decrypt(nonce: bytes, tag: bytes, ciphertext: bytes, key: bytes) -> bytes:
    """Decrypt AES-256 EAX payload and verify integrity."""
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)


# ──────────────────────────────────────────────
# 🧩 Utilities
# ──────────────────────────────────────────────
def base64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def base64_decode(data: str) -> bytes:
    return base64.b64decode(data)


# ──────────────────────────────────────────────
# 🌐 Symbolic AES Key Derivation
# ──────────────────────────────────────────────
def generate_aes_key(
    trust_level: float = 0.5,
    emotion_level: float = 0.5,
    identity: Optional[str] = None,
    seed_phrase: Optional[str] = None,
) -> bytes:
    """
    Generate AES key using symbolic derivation as primary method.
    Falls back to random key if derivation fails.
    """
    from time import time
    timestamp = time()
    derived_key = symbolic_key_deriver.derive_key(
        trust_level, emotion_level, timestamp,
        identity=identity, seed_phrase=seed_phrase
    )
    return derived_key or get_random_bytes(32)


# ──────────────────────────────────────────────
# 📦 AES Packet Helpers
# ──────────────────────────────────────────────
def aes_encrypt_packet(packet_dict: dict, aes_key: bytes) -> dict:
    """Encrypt a dict payload with AES."""
    import json
    plaintext = json.dumps(packet_dict).encode("utf-8")
    nonce, tag, ciphertext = aes_encrypt(plaintext, aes_key)
    return {
        "method": "aes",
        "nonce": base64_encode(nonce),
        "tag": base64_encode(tag),
        "ciphertext": base64_encode(ciphertext),
    }


def aes_decrypt_packet(encrypted_dict: dict, aes_key: bytes) -> dict:
    """Decrypt an AES-encrypted packet back to a dict."""
    import json
    nonce = base64_decode(encrypted_dict["nonce"])
    tag = base64_decode(encrypted_dict["tag"])
    ciphertext = base64_decode(encrypted_dict["ciphertext"])
    plaintext = aes_decrypt(nonce, tag, ciphertext, aes_key)
    return json.loads(plaintext.decode("utf-8"))


# ──────────────────────────────────────────────
# ⏳ Ephemeral AES Encryption
# ──────────────────────────────────────────────
def encrypt_with_ephemeral_key(
    packet_dict: dict,
    session_id: str,
    trust_level: float = 0.5,
    emotion_level: float = 0.5,
    seed_phrase: Optional[str] = None,
) -> Optional[dict]:
    """
    Encrypt packet dict with ephemeral AES key derived symbolically.
    Falls back to generated key if missing.
    """
    ephemeral_manager = get_ephemeral_key_manager()
    aes_key = ephemeral_manager.get_key(session_id)
    if aes_key is None:
        aes_key = ephemeral_manager.generate_key(session_id, trust_level, emotion_level, seed_phrase)
    if not aes_key:
        return None
    return aes_encrypt_packet(packet_dict, aes_key)


def decrypt_with_ephemeral_key(encrypted_dict: dict, session_id: str) -> Optional[dict]:
    """Decrypt AES packet with ephemeral key for the given session."""
    ephemeral_manager = get_ephemeral_key_manager()
    aes_key = ephemeral_manager.get_key(session_id)
    return aes_decrypt_packet(encrypted_dict, aes_key) if aes_key else None


# ──────────────────────────────────────────────
# ✍️ RSA Signing / Verification
# ──────────────────────────────────────────────
def sign_message(message: str, private_key_pem: bytes) -> str:
    private_key = rsa.PrivateKey.load_pkcs1(private_key_pem)
    signature = rsa.sign(message.encode("utf-8"), private_key, "SHA-256")
    return base64.b64encode(signature).decode("utf-8")


def verify_signature(message: str, signature_b64: str, public_key_pem: bytes) -> bool:
    public_key = rsa.PublicKey.load_pkcs1(public_key_pem)
    signature = base64.b64decode(signature_b64)
    try:
        rsa.verify(message.encode("utf-8"), signature, public_key)
        return True
    except rsa.VerificationError:
        return False


def encrypt_and_sign_packet(packet_dict: dict, private_key_pem: bytes, public_key_pem: bytes) -> str:
    """Encrypt packet with RSA and attach signature wrapper."""
    import json
    plaintext = json.dumps(packet_dict)
    signature = sign_message(plaintext, private_key_pem)
    encrypted = rsa_encrypt(plaintext.encode("utf-8"), public_key_pem)
    return json.dumps({
        "encrypted_payload": base64_encode(encrypted),
        "signature": signature,
    })


def decrypt_and_verify_packet(encrypted_wrapper_json: str, private_key_pem: bytes, sender_public_key_pem: bytes) -> dict:
    """Decrypt RSA packet and verify attached signature."""
    import json
    wrapper = json.loads(encrypted_wrapper_json)
    encrypted_payload_b64 = wrapper.get("encrypted_payload")
    signature = wrapper.get("signature")
    decrypted = rsa_decrypt(base64_decode(encrypted_payload_b64), private_key_pem).decode("utf-8")
    if not verify_signature(decrypted, signature, sender_public_key_pem):
        raise ValueError("Signature verification failed")
    return json.loads(decrypted)


# ──────────────────────────────────────────────
# 🚀 High-Level GlyphNet Crypto Helpers
# ──────────────────────────────────────────────
def encrypt_packet(
    packet: Dict[str, Any],
    *,
    session_id: Optional[str] = None,
    trust_level: float = 0.5,
    emotion_level: float = 0.5,
    seed_phrase: Optional[str] = None,
    rsa_public_key_pem: Optional[bytes] = None,
    sign_private_key_pem: Optional[bytes] = None,
    qglyph_tag_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Encrypt a packet dict.
    Priority:
      1) AES ephemeral (if session_id provided)
      2) RSA (optionally signed)
    """
    # Semantic tag injection (best-effort)
    if qglyph_tag_key and tag_with_qglyph_lock:
        try:
            packet = tag_with_qglyph_lock(dict(packet), qglyph_tag_key)
        except Exception:
            pass

    # AES ephemeral path
    if session_id:
        encrypted = encrypt_with_ephemeral_key(
            packet, session_id,
            trust_level=trust_level, emotion_level=emotion_level,
            seed_phrase=seed_phrase,
        )
        if not encrypted:
            raise ValueError("Ephemeral key unavailable for session")
        encrypted.setdefault("method", "aes")
        encrypted.setdefault("session_id", session_id)
        return encrypted

    # RSA path
    if rsa_public_key_pem:
        import json
        plaintext = json.dumps(packet)
        if sign_private_key_pem:
            return {"method": "rsa+sig", "wrapper": encrypt_and_sign_packet(packet, sign_private_key_pem, rsa_public_key_pem)}
        ciphertext_b64 = base64_encode(rsa_encrypt(plaintext.encode("utf-8"), rsa_public_key_pem))
        return {"method": "rsa", "ciphertext": ciphertext_b64}

    raise ValueError("No encryption method available: provide session_id or rsa_public_key_pem")


def decrypt_packet(
    payload: Dict[str, Any],
    *,
    session_id: Optional[str] = None,
    rsa_private_key_pem: Optional[bytes] = None,
    sender_public_key_pem: Optional[bytes] = None,
) -> Dict[str, Any]:
    """
    Decrypt packet produced by encrypt_packet().
    Supports:
      - AES ephemeral (requires session_id)
      - RSA
      - RSA + signature
    """
    method = payload.get("method")

    # AES path
    if method == "aes" or all(k in payload for k in ("nonce", "tag", "ciphertext")):
        session_id = session_id or payload.get("session_id")
        if not session_id:
            raise ValueError("Missing session_id for AES decryption")
        return decrypt_with_ephemeral_key(payload, session_id)

    # RSA + signature path
    if method == "rsa+sig" and "wrapper" in payload:
        if not rsa_private_key_pem or not sender_public_key_pem:
            raise ValueError("RSA private key and sender public key required for rsa+sig")
        return decrypt_and_verify_packet(payload["wrapper"], rsa_private_key_pem, sender_public_key_pem)

    # RSA path
    if method == "rsa" and "ciphertext" in payload:
        if not rsa_private_key_pem:
            raise ValueError("RSA private key required for rsa")
        import json
        decrypted = rsa_decrypt(base64_decode(payload["ciphertext"]), rsa_private_key_pem)
        return json.loads(decrypted.decode("utf-8"))

    raise ValueError("Unsupported or malformed encrypted payload")