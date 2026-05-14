# File: backend/modules/encryption/crypto_core.py

import base64
import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from typing import Tuple


class AES256Cipher:
    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES-256")
        self.key = key

    def encrypt(self, plaintext: str) -> Tuple[str, str]:
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        ct_bytes = cipher.encrypt(pad(plaintext.encode('utf-8'), AES.block_size))
        ciphertext = base64.b64encode(ct_bytes).decode('utf-8')
        iv_encoded = base64.b64encode(iv).decode('utf-8')
        return ciphertext, iv_encoded

    def decrypt(self, ciphertext: str, iv: str) -> str:
        ct_bytes = base64.b64decode(ciphertext)
        iv_bytes = base64.b64decode(iv)
        cipher = AES.new(self.key, AES.MODE_CBC, iv_bytes)
        pt = unpad(cipher.decrypt(ct_bytes), AES.block_size)
        return pt.decode('utf-8')


class Base64Codec:
    @staticmethod
    def encode(data: bytes) -> str:
        return base64.b64encode(data).decode('utf-8')

    @staticmethod
    def decode(data_str: str) -> bytes:
        return base64.b64decode(data_str)


class NonceGenerator:
    @staticmethod
    def generate_nonce(length: int = 16) -> str:
        return base64.b64encode(os.urandom(length)).decode('utf-8')