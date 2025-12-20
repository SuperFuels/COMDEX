# backend/modules/p2p/crypto_ed25519.py
from __future__ import annotations

import binascii
import json
from typing import Any, Dict, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature


def _hx(b: bytes) -> str:
    return b.hex()


def _unhex(s: str) -> bytes:
    ss = (s or "").strip().lower()
    return binascii.unhexlify(ss.encode("utf-8"))


def stable_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_p2p_sign_bytes(*, msg_type: str, chain_id: str, payload: Dict[str, Any]) -> bytes:
    """
    Canonical sign-bytes for P2P payload signatures.

    IMPORTANT:
      - strips payload["sig_hex"] so signature is over the unsigned content
      - includes msg_type + chain_id to prevent cross-lane replay
    """
    p = dict(payload or {})
    p.pop("sig_hex", None)
    return stable_json_bytes({"type": str(msg_type or ""), "chain_id": str(chain_id or ""), "payload": p})


def canonical_hello_sign_bytes(
    *, chain_id: str, node_id: str, val_id: str | None, base_url: str, pubkey_hex: str
) -> bytes:
    """
    Self-signed HELLO: the peer proves control of pubkey and binds identity fields to it.
    """
    return stable_json_bytes(
        {
            "type": "HELLO",
            "chain_id": str(chain_id or ""),
            "node_id": str(node_id or ""),
            "val_id": (str(val_id or "") or None),
            "base_url": str(base_url or ""),
            "pubkey_hex": str(pubkey_hex or "").strip().lower(),
        }
    )


def sign_ed25519(privkey_hex: str, msg: bytes) -> str:
    sk = Ed25519PrivateKey.from_private_bytes(_unhex(privkey_hex))
    sig = sk.sign(msg)
    return _hx(sig)


def pubkey_from_priv(privkey_hex: str) -> str:
    sk = Ed25519PrivateKey.from_private_bytes(_unhex(privkey_hex))
    pk = sk.public_key()
    return _hx(pk.public_bytes_raw())


def verify_ed25519(pubkey_hex: str, sig_hex: str, msg: bytes) -> bool:
    try:
        pk = Ed25519PublicKey.from_public_bytes(_unhex(pubkey_hex))
        pk.verify(_unhex(sig_hex), msg)
        return True
    except (ValueError, InvalidSignature, binascii.Error):
        return False
    except Exception:
        return False