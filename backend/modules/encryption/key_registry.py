import os
from typing import Optional, Tuple
from Crypto.PublicKey import RSA

KEY_DIR = "keys"
DEFAULT_KEY_SIZE = 2048


def ensure_key_folder():
    if not os.path.exists(KEY_DIR):
        os.makedirs(KEY_DIR)


def get_key_paths(identity: str) -> Tuple[str, str]:
    pub_path = os.path.join(KEY_DIR, f"{identity}_public.pem")
    priv_path = os.path.join(KEY_DIR, f"{identity}_private.pem")
    return pub_path, priv_path


def generate_key_pair(identity: str, bits: int = DEFAULT_KEY_SIZE) -> Tuple[bytes, bytes]:
    key = RSA.generate(bits)
    private_pem = key.export_key()
    public_pem = key.publickey().export_key()

    ensure_key_folder()
    pub_path, priv_path = get_key_paths(identity)
    with open(pub_path, "wb") as f:
        f.write(public_pem)
    with open(priv_path, "wb") as f:
        f.write(private_pem)

    return public_pem, private_pem


def load_public_key(identity: str) -> Optional[bytes]:
    pub_path, _ = get_key_paths(identity)
    if not os.path.exists(pub_path):
        return None
    with open(pub_path, "rb") as f:
        return f.read()


def load_private_key(identity: str) -> Optional[bytes]:
    _, priv_path = get_key_paths(identity)
    if not os.path.exists(priv_path):
        return None
    with open(priv_path, "rb") as f:
        return f.read()


def ensure_keys(identity: str) -> Tuple[bytes, bytes]:
    pub_path, priv_path = get_key_paths(identity)
    if os.path.exists(pub_path) and os.path.exists(priv_path):
        return load_public_key(identity), load_private_key(identity)
    return generate_key_pair(identity)