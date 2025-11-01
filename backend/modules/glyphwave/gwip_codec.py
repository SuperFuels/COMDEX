"""
🌀 GWIP (GlyphWave Interchange Protocol) Codec - SRK-9
Encodes and decodes GlyphWave Information Packets (GWIP) between symbolic and binary domains.

Integrates:
 - Compression (photon/compressor.py)
 - Encryption / signing (qkd/gkey_encryptor.py)
 - Integrity verification (protocol/gwip_schema.py)
 - Quantum Key Distribution (QKD) handshake verification
"""

import json
import hashlib
import time
import asyncio
from typing import Dict, Any, Optional

from backend.photon.compressor import PhotonCompressor as Compressor
from backend.modules.glyphwave.qkd.gkey_encryptor import GWaveEncryptor as GKeyEncryptor
from backend.modules.glyphwave.protocol.gwip_schema import validate_gwip_schema
from backend.modules.glyphwave.constants import (
    DEFAULT_FREQ_HZ,
    DEFAULT_PHASE_RAD,
    DEFAULT_COHERENCE,
)


class GWIPCodec:
    """Handles encoding, decoding, signing, and QKD verification for GWIP packets."""

    schema_version = 2

    def __init__(self, encryptor: Optional[GKeyEncryptor] = None):
        self.encryptor = encryptor or GKeyEncryptor(
            gkey_pair={"collapse_hash": "default-gwave-key"}
        )
        self.compressor = Compressor()

    # ────────────────────────────────────────────────────────────────
    def _hash_payload(self, payload: bytes) -> str:
        """Compute deterministic SHA3-512 hash."""
        return hashlib.sha3_512(payload).hexdigest()

    # ────────────────────────────────────────────────────────────────
    def encode(self, gip: Dict[str, Any], sign: bool = True) -> Dict[str, Any]:
        """
        Encode a standard GIP packet into a GWIP envelope.

        Args:
            gip: The input GIP packet.
            sign: Whether to sign the packet cryptographically.

        Returns:
            Fully-formed GWIP dictionary.
        """
        envelope = {
            "freq": gip.get("freq", DEFAULT_FREQ_HZ),
            "phase": gip.get("phase", DEFAULT_PHASE_RAD),
            "coherence": gip.get("coherence", DEFAULT_COHERENCE),
            "tags": gip.get("tags", []),
            "timestamp": time.time(),
        }

        # Compress + serialize payload
        payload_json = json.dumps(gip, separators=(",", ":")).encode("utf-8")
        compressed = self.compressor.compress_basic(payload_json.decode("utf-8"))

        # Hash + optional signature
        payload_bytes = json.dumps(str(compressed)).encode("utf-8")
        digest = self._hash_payload(payload_bytes)
        signature = self.encryptor.encrypt_payload({"digest": digest}) if sign else None

        gwip = {
            "type": "gwip",
            "schema": self.schema_version,
            "envelope": envelope,
            "payload": payload_bytes.hex(),
            "hash": digest,
            "signature": signature,
        }

        # Validate against schema
        validate_gwip_schema(gwip)
        return gwip

    # ────────────────────────────────────────────────────────────────
    async def encode_with_qkd(
        self,
        gip: Dict[str, Any],
        sender_id: str,
        receiver_id: str,
        wave,
        sign: bool = True,
    ) -> Dict[str, Any]:
        """
        Encode a GIP packet, then verify and secure it using a QKD handshake.

        This combines symbolic encoding with quantum-verifiable authentication.
        """
        packet = self.encode(gip, sign=sign)

        # 🔁 Lazy import to break circular dependency
        from backend.modules.glyphwave.qkd.qkd_crypto_handshake import initiate_qkd_handshake

        verified = await initiate_qkd_handshake(sender_id, receiver_id, wave)
        packet["qkd_verified"] = verified
        packet["verified_at"] = time.time()

        if not verified:
            packet["tamper_flag"] = True
            packet["status"] = "qkd_failed"
        else:
            packet["status"] = "qkd_verified"

        return packet

    # ────────────────────────────────────────────────────────────────
    def decode(self, gwip: Dict[str, Any], verify: bool = True) -> Dict[str, Any]:
        """
        Decode a GWIP back into its GIP representation.

        Args:
            gwip: The encoded GWIP packet.
            verify: Whether to verify integrity and signature.

        Returns:
            Original GIP dict.
        """
        if gwip.get("type") != "gwip":
            return gwip  # fallback for plain GIP

        validate_gwip_schema(gwip)
        payload_bytes = bytes.fromhex(gwip["payload"])

        if verify:
            computed = self._hash_payload(payload_bytes)
            if computed != gwip.get("hash"):
                raise ValueError("GWIP integrity check failed (hash mismatch)")
            if gwip.get("signature") and not gwip["signature"].get("qkd_encrypted", False):
                raise ValueError("GWIP signature verification failed (not encrypted)")
            if gwip.get("qkd_verified") is False:
                raise ValueError("QKD handshake verification failed")

        decompressed_str = gwip["payload"]
        gip = json.loads(bytes.fromhex(decompressed_str).decode("utf-8"))
        return gip

    # ────────────────────────────────────────────────────────────────
    def upgrade(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure packet is encoded as GWIP."""
        return self.encode(packet) if packet.get("type") != "gwip" else packet

    def downgrade(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Extract raw GIP from a GWIP packet."""
        return self.decode(packet)