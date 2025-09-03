# File: backend/modules/glyphvault/waveglyph_signer.py

import base64
import json
import logging
from typing import Dict

from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.PublicKey import RSA

from backend.modules.encryption.key_registry import load_private_key, load_public_key
from backend.modules.glyphvault.key_manager import key_manager

logger = logging.getLogger(__name__)


def sign_waveglyph(glyph: Dict, private_key_pem: bytes) -> Dict:
    """
    Signs a WaveGlyph using the given private RSA key.
    Returns the glyph with an embedded signature_block.
    """
    try:
        message = json.dumps(glyph, sort_keys=True).encode("utf-8")
        key = RSA.import_key(private_key_pem)
        h = SHA256.new(message)
        signature = pkcs1_15.new(key).sign(h)
        sig_b64 = base64.b64encode(signature).decode("utf-8")

        # ✅ Use identity from KeyManager
        vault_origin_id = key_manager.public_id

        glyph["signature_block"] = {
            "sig": sig_b64,
            "signed_by": vault_origin_id,  # ✅ Vault ID injected
            "algorithm": "RSA-SHA256"
        }

        return glyph

    except Exception as e:
        logger.exception("[WaveGlyphSigner] ❌ Failed to sign glyph")
        raise e


def verify_waveglyph_signature(glyph: Dict, public_key_pem: bytes) -> bool:
    """
    Verifies the signature of a signed WaveGlyph using the sender's public RSA key.
    Returns True if valid, False otherwise.
    """
    try:
        sig_block = glyph.get("signature_block", {})
        signature = base64.b64decode(sig_block.get("sig", ""))
        clean_glyph = glyph.copy()
        clean_glyph.pop("signature_block", None)

        message = json.dumps(clean_glyph, sort_keys=True).encode("utf-8")
        key = RSA.import_key(public_key_pem)
        h = SHA256.new(message)

        pkcs1_15.new(key).verify(h, signature)
        return True

    except (ValueError, TypeError):
        return False
    except Exception as e:
        logger.exception("[WaveGlyphSigner] ❌ Signature verification failed")
        return False