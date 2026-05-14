import json
import base64
from typing import Dict, Tuple, Optional

from backend.modules.encryption.key_registry import (
    load_public_key,
    load_private_key,
    ensure_keys,
)
from backend.modules.glyphnet.glyphnet_crypto import (
    rsa_encrypt,
    rsa_decrypt,
    aes_encrypt,
    aes_decrypt,
    generate_aes_key,
    base64_encode,
    base64_decode,
)


def encrypt_packet_for_identity(packet: Dict, identity: str, use_aes_fallback: bool = False) -> Dict:
    """
    Encrypts a .gip packet for the target identity using RSA or optional AES fallback.
    """
    plaintext = json.dumps(packet).encode("utf-8")

    if use_aes_fallback:
        aes_key = generate_aes_key()
        nonce, tag, ciphertext = aes_encrypt(plaintext, aes_key)

        return {
            "type": "gip_encrypted",
            "method": "aes",
            "key": base64_encode(aes_key),
            "nonce": base64_encode(nonce),
            "tag": base64_encode(tag),
            "ciphertext": base64_encode(ciphertext),
            "target": identity,
        }

    public_key = load_public_key(identity)
    if not public_key:
        raise ValueError(f"No public key found for identity: {identity}")

    ciphertext = rsa_encrypt(plaintext, public_key)
    return {
        "type": "gip_encrypted",
        "method": "rsa",
        "ciphertext": base64_encode(ciphertext),
        "target": identity,
    }


def decrypt_packet_from_identity(payload: Dict, identity: str) -> Dict:
    """
    Decrypts a `.gip_encrypted` packet intended for this identity.
    Supports RSA and AES fallback.
    """
    private_key = load_private_key(identity)
    if not private_key:
        raise ValueError(f"No private key available for identity: {identity}")

    if payload["method"] == "rsa":
        ciphertext = base64_decode(payload["ciphertext"])
        decrypted = rsa_decrypt(ciphertext, private_key)
        return json.loads(decrypted.decode("utf-8"))

    elif payload["method"] == "aes":
        aes_key = base64_decode(payload["key"])
        nonce = base64_decode(payload["nonce"])
        tag = base64_decode(payload["tag"])
        ciphertext = base64_decode(payload["ciphertext"])

        decrypted = aes_decrypt(nonce, tag, ciphertext, aes_key)
        return json.loads(decrypted.decode("utf-8"))

    else:
        raise ValueError(f"Unsupported encryption method: {payload.get('method')}")