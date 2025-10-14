"""
🔶 PhotonBinaryBridge — Symbolic ↔ Binary Bridge Layer (SRK-10)
Bridges GlyphWave Information Packets (GWIP) with Photon Capsules.

This component establishes the final data handoff between:
 • The binary transport domain (GWIP)
 • The symbolic photon computation domain (Photon Capsule)

Integrates:
 - GWIP → Photon translation
 - QKD handshake verification
 - Capsule schema validation
 - Optional coherence and entropy tagging
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional

from backend.modules.glyphwave.protocol.gwip_schema import validate_gwip_schema
from backend.modules.glyphwave.qkd.qkd_crypto_handshake import initiate_qkd_handshake
from backend.modules.photon.photon_capsule_validator import validate_photon_capsule


class PhotonBinaryBridge:
    """
    🌉 Converts between validated GWIP packets and Photon Capsules.
    """

    schema_version = 1

    # ────────────────────────────────────────────────────────────────
    async def gwip_to_photon_capsule(
        self,
        gwip_packet: Dict[str, Any],
        sender_id: str,
        receiver_id: str,
        wave: Any,
        include_qkd: bool = True
    ) -> Dict[str, Any]:
        """
        Convert a GWIP packet into a Photon Capsule.

        Performs:
         • GWIP validation
         • Optional QKD handshake
         • Symbolic capsule generation
         • Capsule schema validation

        Returns:
            dict: Validated Photon Capsule
        """
        # Step 1 — Validate GWIP structure
        validate_gwip_schema(gwip_packet)
        envelope = gwip_packet.get("envelope", {})

        # Step 2 — Optional QKD handshake
        qkd_verified = False
        if include_qkd:
            qkd_verified = await initiate_qkd_handshake(
                sender_id=sender_id,
                receiver_id=receiver_id,
                wave=wave
            )

        # Step 3 — Parse payload safely
        payload_raw = gwip_packet.get("payload")
        if isinstance(payload_raw, str):
            try:
                payload = json.loads(payload_raw)
            except Exception:
                payload = {"raw": payload_raw}
        else:
            payload = payload_raw or {}

        # Step 4 — Build Photon Capsule (schema-compliant)
        capsule = {
            "name": envelope.get("packet_id", f"capsule_{int(time.time())}"),
            "version": f"1.0-schema-{self.schema_version}",
            "glyphs": [
                {
                    "name": envelope.get("source_container", "unknown_src"),
                    "operator": "⊕",
                    "logic": "wave→photon",
                    "args": [envelope.get("freq"), envelope.get("phase")],
                    "meta": {
                        "coherence": envelope.get("coherence"),
                        "qkd_verified": qkd_verified,
                        "timestamp": envelope.get("timestamp", time.time()),
                        "origin": "PhotonBinaryBridge",
                        "status": "qkd_verified" if qkd_verified else "unverified",
                    },
                }
            ],
        }

        # Step 5 — Validate Photon Capsule (against JSON schema)
        validate_photon_capsule(capsule)

        return capsule

    # ────────────────────────────────────────────────────────────────
    def photon_capsule_to_gwip(
        self,
        capsule: Dict[str, Any],
        base_envelope: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert a Photon Capsule back into a GWIP packet.

        Args:
            capsule: Valid Photon Capsule.
            base_envelope: Optional envelope template.

        Returns:
            dict: GWIP-formatted dictionary.
        """
        # Step 1 — Validate capsule
        validate_photon_capsule(capsule)

        # Step 2 — Construct envelope if not provided
        import uuid

        capsule_name = capsule.get("name", f"capsule_{int(time.time())}")
        envelope = base_envelope or {}

        # Ensure required GWIP schema fields are present
        envelope.update({
            "packet_id": envelope.get("packet_id", f"gwip_{uuid.uuid4().hex[:8]}"),
            "source_container": envelope.get("source_container", capsule_name),
            "target_container": envelope.get("target_container", "photon_core"),
            "carrier_type": envelope.get("carrier_type", "SIMULATED"),
            "freq": envelope.get("freq", 0.0),
            "phase": envelope.get("phase", 0.0),
            "coherence": envelope.get("coherence", 1.0),
            "timestamp": envelope.get("timestamp", time.time()),
        })

        # Step 3 — Serialize capsule payload
        payload_json = json.dumps(capsule, separators=(",", ":"))

        # Step 4 — Compute secure SHA3-512 hash (128 hex chars)
        payload_hash = hashlib.sha3_512(payload_json.encode()).hexdigest()

        # Step 5 — Assemble GWIP packet
        gwip_packet = {
            "type": "gwip",
            "schema": 3,
            "envelope": envelope,
            "payload": payload_json,
            "hash": payload_hash,
            "signature": None,
        }

        # Step 6 — Validate GWIP packet
        validate_gwip_schema(gwip_packet)

        return gwip_packet