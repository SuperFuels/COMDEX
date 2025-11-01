"""
🔐 Encrypted Photon Channel (EPC-1 Layer) - SRK-16 B3
Performs AES-QKD hybrid encryption for photonic transmissions.
"""

import base64, hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class EncryptedPhotonChannel:
    def __init__(self, qkd_key: str):
        self._session_key = hashlib.sha3_256(qkd_key.encode()).digest()[:32]

    def encrypt(self, data: bytes) -> bytes:
        iv = get_random_bytes(12)
        cipher = AES.new(self._session_key, AES.MODE_GCM, nonce=iv)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return base64.b64encode(iv + tag + ciphertext)

    def decrypt(self, payload: bytes) -> bytes:
        raw = base64.b64decode(payload)
        iv, tag, ciphertext = raw[:12], raw[12:28], raw[28:]
        cipher = AES.new(self._session_key, AES.MODE_GCM, nonce=iv)
        return cipher.decrypt_and_verify(ciphertext, tag)