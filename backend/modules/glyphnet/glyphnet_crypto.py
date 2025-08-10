# File: backend/modules/glyphnet/glyphnet_crypto.py
import rsa
import base64
import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from typing import Tuple, Optional, Dict, Any

from backend.modules.glyphnet.ephemeral_key_manager import get_ephemeral_key_manager
from backend.modules.glyphnet.symbolic_key_derivation import SymbolicKeyDerivation

# Optional semantic tagging (QGlyph locks)
try:
    from backend.modules.encryption.encryption_utils import tag_with_qglyph_lock
except Exception:
    tag_with_qglyph_lock = None  # graceful fallback

# ✅ Instantiate once so generate_aes_key() can use it
symbolic_key_deriver = SymbolicKeyDerivation()

# --- RSA Key Generation ---
def generate_rsa_keypair(bits: int = 2048) -> Tuple[bytes, bytes]:
    pubkey, privkey = rsa.newkeys(bits)
    return pubkey.save_pkcs1(), privkey.save_pkcs1()

# --- RSA Encryption / Decryption ---
def rsa_encrypt(message: bytes, public_key_pem: bytes) -> bytes:
    public_key = rsa.PublicKey.load_pkcs1(public_key_pem)
    return rsa.encrypt(message, public_key)

def rsa_decrypt(ciphertext: bytes, private_key_pem: bytes) -> bytes:
    private_key = rsa.PrivateKey.load_pkcs1(private_key_pem)
    return rsa.decrypt(ciphertext, private_key)

# --- AES Fallback Encryption ---
def aes_encrypt(message: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(message)
    return cipher.nonce, tag, ciphertext

def aes_decrypt(nonce: bytes, tag: bytes, ciphertext: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)

# --- Utilities ---
def base64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode('utf-8')

def base64_decode(data: str) -> bytes:
    return base64.b64decode(data)

# --- Updated AES Key Generation using Symbolic Derivation ---
def generate_aes_key(
    trust_level: float = 0.5,
    emotion_level: float = 0.5,
    identity: Optional[str] = None,
    seed_phrase: Optional[str] = None
) -> bytes:
    """
    Generate AES key with symbolic key derivation as primary method.
    Falls back to random key if derivation fails.
    """
    from time import time
    timestamp = time()
    # ✅ use instantiated symbolic_key_deriver
    derived_key = symbolic_key_deriver.derive_key(
        trust_level, emotion_level, timestamp,
        identity=identity, seed_phrase=seed_phrase
    )
    if derived_key is None:
        # fallback to random key
        derived_key = get_random_bytes(32)
    return derived_key

# --- AES Packet Encryption for Session Keys ---
def aes_encrypt_packet(packet_dict: dict, aes_key: bytes) -> dict:
    import json
    plaintext = json.dumps(packet_dict).encode('utf-8')
    nonce, tag, ciphertext = aes_encrypt(plaintext, aes_key)
    return {
        "method": "aes",
        "nonce": base64_encode(nonce),
        "tag": base64_encode(tag),
        "ciphertext": base64_encode(ciphertext)
    }

def aes_decrypt_packet(encrypted_dict: dict, aes_key: bytes) -> dict:
    import json
    nonce = base64_decode(encrypted_dict["nonce"])
    tag = base64_decode(encrypted_dict["tag"])
    ciphertext = base64_decode(encrypted_dict["ciphertext"])
    plaintext = aes_decrypt(nonce, tag, ciphertext, aes_key)
    return json.loads(plaintext.decode('utf-8'))

# --- Ephemeral AES Encryption with EphemeralKeyManager and Symbolic Derivation ---
def encrypt_with_ephemeral_key(
    packet_dict: dict,
    session_id: str,
    trust_level: float = 0.5,
    emotion_level: float = 0.5,
    seed_phrase: Optional[str] = None
) -> Optional[dict]:
    """
    Encrypt packet dict with ephemeral AES key derived symbolically.
    Returns encrypted dict or None if key unavailable.
    """
    ephemeral_manager = get_ephemeral_key_manager()
    # Generate or retrieve symbolic ephemeral key for this session with semantic params
    aes_key = ephemeral_manager.get_key(session_id)
    if aes_key is None:
        # Generate key with symbolic derivation if not present
        aes_key = ephemeral_manager.generate_key(session_id, trust_level, emotion_level, seed_phrase)
    if not aes_key:
        return None  # No key available
    return aes_encrypt_packet(packet_dict, aes_key)

def decrypt_with_ephemeral_key(encrypted_dict: dict, session_id: str) -> Optional[dict]:
    """
    Decrypt packet dict with ephemeral AES key from EphemeralKeyManager.
    Returns decrypted dict or None if key unavailable.
    """
    ephemeral_manager = get_ephemeral_key_manager()
    aes_key = ephemeral_manager.get_key(session_id)
    if not aes_key:
        return None
    return aes_decrypt_packet(encrypted_dict, aes_key)

# --- PHASE 5: Signature Verification ---

# --- Message Signing ---
def sign_message(message: str, private_key_pem: bytes) -> str:
    private_key = rsa.PrivateKey.load_pkcs1(private_key_pem)
    signature = rsa.sign(message.encode('utf-8'), private_key, 'SHA-256')
    return base64.b64encode(signature).decode('utf-8')

def verify_signature(message: str, signature_b64: str, public_key_pem: bytes) -> bool:
    public_key = rsa.PublicKey.load_pkcs1(public_key_pem)
    signature = base64.b64decode(signature_b64)
    try:
        rsa.verify(message.encode('utf-8'), signature, public_key)
        return True
    except rsa.VerificationError:
        return False

# --- Encrypt and Sign Packet ---
def encrypt_and_sign_packet(packet_dict: dict, private_key_pem: bytes, public_key_pem: bytes) -> str:
    import json
    plaintext = json.dumps(packet_dict)
    signature = sign_message(plaintext, private_key_pem)
    encrypted = rsa_encrypt(plaintext.encode('utf-8'), public_key_pem)
    wrapper = {
        "encrypted_payload": base64.b64encode(encrypted).decode('utf-8'),
        "signature": signature
    }
    return json.dumps(wrapper)

# --- Decrypt and Verify Packet ---
def decrypt_and_verify_packet(encrypted_wrapper_json: str, private_key_pem: bytes, sender_public_key_pem: bytes) -> dict:
    import json
    wrapper = json.loads(encrypted_wrapper_json)
    encrypted_payload_b64 = wrapper.get("encrypted_payload")
    signature = wrapper.get("signature")
    decrypted = rsa_decrypt(base64.b64decode(encrypted_payload_b64), private_key_pem).decode('utf-8')
    if not verify_signature(decrypted, signature, sender_public_key_pem):
        raise ValueError("Signature verification failed")
    return json.loads(decrypted)

# ───────────────────────────────────────────────────────────
# ✅ High-level helpers used by GlyphNet terminal / routes
# ───────────────────────────────────────────────────────────
def encrypt_packet(
    packet: Dict[str, Any],
    *,
    # Prefer AES ephemeral if provided:
    session_id: Optional[str] = None,
    trust_level: float = 0.5,
    emotion_level: float = 0.5,
    seed_phrase: Optional[str] = None,
    # Or fall back to RSA:
    rsa_public_key_pem: Optional[bytes] = None,
    # Optional signing (RSA):
    sign_private_key_pem: Optional[bytes] = None,
    # Optional symbolic tag for QGlyph semantics:
    qglyph_tag_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Encrypt a packet dict.
    Priority:
      1) If session_id provided → AES ephemeral encryption
      2) Else if rsa_public_key_pem provided → RSA (optionally signed)
    """
    # Optional: attach QGlyph semantic tag before encryption
    if qglyph_tag_key and tag_with_qglyph_lock:
        try:
            packet = tag_with_qglyph_lock(dict(packet), qglyph_tag_key)
        except Exception:
            # Tagging is best-effort; continue on failure
            pass

    # 1) Ephemeral AES path
    if session_id:
        encrypted = encrypt_with_ephemeral_key(
            packet, session_id,
            trust_level=trust_level,
            emotion_level=emotion_level,
            seed_phrase=seed_phrase
        )
        if encrypted is None:
            raise ValueError("Ephemeral key unavailable for session")
        # Include method and session marker for routing clarity
        encrypted.setdefault("method", "aes")
        encrypted.setdefault("session_id", session_id)
        return encrypted

    # 2) RSA path
    if rsa_public_key_pem:
        import json
        plaintext = json.dumps(packet)
        if sign_private_key_pem:
            # Return a standard wrapper field so decrypt can detect this
            wrapper_json = encrypt_and_sign_packet(packet, sign_private_key_pem, rsa_public_key_pem)
            return {
                "method": "rsa+sig",
                "wrapper": wrapper_json,
            }
        # Unsigned RSA
        ciphertext_b64 = base64.b64encode(
            rsa_encrypt(plaintext.encode("utf-8"), rsa_public_key_pem)
        ).decode("utf-8")
        return {
            "method": "rsa",
            "ciphertext": ciphertext_b64,
        }

    raise ValueError("No encryption method available: provide session_id or rsa_public_key_pem")

def decrypt_packet(
    payload: Dict[str, Any],
    *,
    # For AES ephemeral:
    session_id: Optional[str] = None,
    # For RSA:
    rsa_private_key_pem: Optional[bytes] = None,
    sender_public_key_pem: Optional[bytes] = None
) -> Dict[str, Any]:
    """
    Decrypt a packet produced by encrypt_packet().
    Supports:
      - AES ephemeral (requires session_id)
      - RSA (ciphertext only)
      - RSA + signature (wrapper)
    """
    method = payload.get("method")

    # AES path
    if method == "aes" or all(k in payload for k in ("nonce", "tag", "ciphertext")):
        if not session_id:
            session_id = payload.get("session_id")  # allow payload to carry it
        if not session_id:
            raise ValueError("Missing session_id for AES decryption")
        return decrypt_with_ephemeral_key(payload, session_id)

    # RSA + signature path
    if method == "rsa+sig" and "wrapper" in payload:
        if not rsa_private_key_pem or not sender_public_key_pem:
            raise ValueError("RSA private key and sender public key required for rsa+sig")
        return decrypt_and_verify_packet(payload["wrapper"], rsa_private_key_pem, sender_public_key_pem)

    # RSA (ciphertext only) path
    if method == "rsa" and "ciphertext" in payload:
        if not rsa_private_key_pem:
            raise ValueError("RSA private key required for rsa")
        import json
        decrypted = rsa_decrypt(base64.b64decode(payload["ciphertext"]), rsa_private_key_pem)
        return json.loads(decrypted.decode("utf-8"))

    raise ValueError("Unsupported or malformed encrypted payload")