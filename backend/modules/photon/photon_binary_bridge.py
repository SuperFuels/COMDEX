"""
🔶 PhotonBinaryBridge — Adaptive Symbolic ↔ Binary Bridge Layer (SRK-10 → SRK-16)
Bridges GlyphWave Information Packets (GWIP) with Photon Capsules.

Final SRK-11 → SRK-16 integration:
 • Adds QKDPolicyEnforcer for entanglement-key compliance.
 • Adds DynamicCoherenceOptimizer for live photon-wave stabilization.
 • Adds PhotonMemoryGrid persistence (SRK-12).
 • Adds QTS layer — QuantumPolicyEngine + EncryptedPhotonChannel (SRK-16).
 • Supports runtime mode switching (photon / binary / auto).
"""
import os
import time
import json
import uuid
import hashlib
import asyncio
from typing import Dict, Any, Optional
from base64 import b64encode
# ────────────────────────────────────────────────────────────────
# Internal imports
# ----------------------------------------------------------------
from backend.modules.glyphwave.protocol.gwip_schema import validate_gwip_schema
from backend.modules.glyphwave.qkd.qkd_crypto_handshake import initiate_qkd_handshake
from backend.modules.glyphwave.qkd.qkd_policy_enforcer import QKDPolicyEnforcer
from backend.modules.glyphwave.core.coherence_optimizer import DynamicCoherenceOptimizer
from backend.modules.photon.photon_capsule_validator import validate_photon_capsule
from backend.modules.photon.memory.photon_memory_grid import PhotonMemoryGrid  # 🆕 SRK-12
from backend.modules.codex.collapse_trace_exporter import log_soullaw_event    # 🆕 telemetry

# 🛰 SRK-16 — Quantum Transport Security (QTS)
from backend.qts.encrypted_photon_channel import EncryptedPhotonChannel
from backend.qts.quantum_policy_engine import QuantumPolicyEngine


class PhotonBinaryBridge:
    """
    🌉 PhotonBinaryBridge — Adaptive translation layer.
    SRK-11 integrates QKD enforcement + dynamic coherence stabilization.
    SRK-12 adds persistent photon memory storage for traceability.
    SRK-16 adds Quantum Transport Security for policy-based encryption.
    """

    schema_version = 1

    def __init__(self, mode: str = "auto"):
        self.mode = mode.lower()
        self._active_mode = None
        self._resolve_mode()

        # SRK-11 core modules
        self.qkd_enforcer = QKDPolicyEnforcer()
        self.coherence_optimizer = DynamicCoherenceOptimizer()

        # SRK-12 addition
        self.memory_grid = PhotonMemoryGrid()

        # SRK-16 additions
        self.qpe = QuantumPolicyEngine()
        self.feature_flag_photon_mode = os.getenv("ENABLE_PHOTON_MODE", "1") == "1"

    # ────────────────────────────────────────────────────────────────
    def _resolve_mode(self):
        """Detect operational mode automatically if 'auto'."""
        if self.mode == "auto":
            try:
                from backend.modules.glyphwave.core.coherence_engine import is_photon_context_active
                self._active_mode = "photon" if is_photon_context_active() else "binary"
            except Exception:
                self._active_mode = "binary"
        else:
            self._active_mode = self.mode
        print(f"[PhotonBinaryBridge] ✅ Operating in {self._active_mode.upper()} mode")

    # ────────────────────────────────────────────────────────────────
    # Mode Control Utilities — SRK-11 Feature Flag
    # ----------------------------------------------------------------
    def toggle_mode(self, enable_photon: bool):
        """Manually toggle bridge operation mode."""
        self.feature_flag_photon_mode = enable_photon
        mode = "Photon" if enable_photon else "Binary"
        print(f"[PhotonBinaryBridge] ⚙️  Mode switched to {mode}")

    def is_photon_mode(self) -> bool:
        """Return True if photon-mode is active via flag or context."""
        if self.mode == "auto":
            return self.feature_flag_photon_mode and self._active_mode == "photon"
        return self.feature_flag_photon_mode and self._active_mode == "photon"

    def _determine_mode_label(self) -> str:
        """Human-readable label for diagnostics."""
        return "Photon" if self.is_photon_mode() else "Binary"
    # ────────────────────────────────────────────────────────────────
    async def gwip_to_photon_capsule(
        self,
        gwip_packet: Dict[str, Any],
        sender_id: str,
        receiver_id: str,
        wave: Any,
        include_qkd: bool = True,
    ) -> Dict[str, Any]:
        """
        Convert a GWIP packet into a Photon Capsule.

        Pipeline:
         1️⃣ Validate GWIP schema
         2️⃣ Enforce QKD policy
         3️⃣ Optimize coherence
         4️⃣ Perform QKD handshake (optional)
         5️⃣ Build and validate Photon Capsule
         6️⃣ Persist capsule to PhotonMemoryGrid (SRK-12)
         7️⃣ Apply QTS security (SRK-16)
        """
        if not self.is_photon_mode():
            return self._simulate_binary_capsule(gwip_packet)

        # Step 1 — Schema validation
        validate_gwip_schema(gwip_packet)
        envelope = gwip_packet.get("envelope", {})

        # Step 2 — QKD policy enforcement
        self.qkd_enforcer.enforce_policy({
            "sender_id": sender_id,
            "recipient_id": receiver_id,
            "wave_id": envelope.get("packet_id"),
            "qkd_policy": {"require_qkd": include_qkd},
        })

        # Step 3 — Dynamic coherence optimization
        try:
            self.coherence_optimizer.optimize_if_needed(wave)
        except Exception as e:
            print(f"[PhotonBinaryBridge] ⚠️ Coherence optimization failed: {e}")

        # Step 4 — Optional QKD handshake
        qkd_verified = False
        if include_qkd:
            qkd_verified = await initiate_qkd_handshake(
                sender_id=sender_id,
                receiver_id=receiver_id,
                wave=wave,
            )

        # Step 5 — Payload parsing
        payload_raw = gwip_packet.get("payload")
        try:
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw or {}
        except Exception:
            payload = {"raw": payload_raw}

        # Step 6 — Photon Capsule assembly
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

        # Step 7 — Validate Photon Capsule
        validate_photon_capsule(capsule)

        # Step 8 — Persist capsule to PhotonMemoryGrid (non-blocking)
        asyncio.create_task(
            self.memory_grid.store_capsule_state(
                capsule["name"],
                {
                    "final_wave": wave,
                    "meta": capsule["glyphs"][0]["meta"],
                    "timestamp": time.time(),
                }
            )
        )

        # Step 9 — Log event to SoulLaw
        log_soullaw_event({
            "type": "capsule_generated",
            "capsule_name": capsule["name"],
            "sender": sender_id,
            "receiver": receiver_id,
            "coherence": envelope.get("coherence"),
            "qkd_verified": qkd_verified,
            "timestamp": time.time(),
        }, glyph=None)

        # Step 🔟 — Apply QTS secure transport encryption
        try:
            encrypted = await self.secure_transmit(gwip_packet)
            capsule["encrypted_payload"] = encrypted.decode() if isinstance(encrypted, bytes) else encrypted
        except Exception as e:
            print(f"[PhotonBinaryBridge] ⚠️ QTS encryption failed: {e}")

        return capsule

    # ────────────────────────────────────────────────────────────────
    async def secure_transmit(self, gwip_packet: Dict[str, Any]) -> str:
        """
        Apply SRK-16 Quantum Transport Security (QTS) to a GWIP packet:
         • Policy enforcement via QuantumPolicyEngine
         • AES–QKD hybrid encryption via EncryptedPhotonChannel
         • Always returns Base64-encoded ciphertext for transport safety
        """
        meta = gwip_packet.get("meta", gwip_packet.get("envelope", {}))
        self.qpe = getattr(self, "qpe", QuantumPolicyEngine())  # ensure QPE exists

        if not self.qpe.enforce(meta):
            raise PermissionError("[QTS] Policy enforcement failed")

        qkd_key = meta.get("qkd_key") or meta.get("gkey_id") or "default_key"
        epc = EncryptedPhotonChannel(qkd_key)

        # 🔒 Single encryption pass, deterministic base64 output
        raw_bytes = str(gwip_packet).encode("utf-8")
        encrypted_bytes = epc.encrypt(raw_bytes)
        encrypted_b64 = b64encode(encrypted_bytes).decode("ascii")

        return encrypted_b64
    # ────────────────────────────────────────────────────────────────
    def photon_capsule_to_gwip(
        self,
        capsule: Dict[str, Any],
        base_envelope: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convert a Photon Capsule back into a GWIP packet.
        Supports both symbolic (photon) and emulated binary modes.
        """
        # ──────────────────────────────────────────────
        # 🧩 Handle non-photon modes (AUTO or BINARY)
        # ──────────────────────────────────────────────
        if not self.is_photon_mode():
            # Return structured emulation wrapper with minimal envelope
            envelope = {
                "packet_id": f"emu_{uuid.uuid4().hex[:8]}",
                "source_container": capsule.get("name", "unknown_src"),
                "target_container": "gwip_emulator",
                "coherence": 1.0,
                "timestamp": time.time(),
            }
            return {
                "emulation": True,
                "mode": getattr(self, "mode", "auto"),
                "envelope": envelope,
                "payload": {
                    "type": "gwip",
                    "schema": 3,
                    "payload": capsule,
                },
            }

        # ──────────────────────────────────────────────
        # ☀️ Normal symbolic-to-GWIP conversion path
        # ──────────────────────────────────────────────
        validate_photon_capsule(capsule)
        capsule_name = capsule.get("name", f"capsule_{int(time.time())}")

        envelope = base_envelope or {}
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

        payload_json = json.dumps(capsule, separators=(",", ":"))
        payload_hash = hashlib.sha3_512(payload_json.encode()).hexdigest()

        gwip_packet = {
            "type": "gwip",
            "schema": 3,
            "envelope": envelope,
            "payload": payload_json,
            "hash": payload_hash,
            "signature": None,
        }

        validate_gwip_schema(gwip_packet)
        return gwip_packet

    # ────────────────────────────────────────────────────────────────
    # Binary Fallbacks
    # ----------------------------------------------------------------
    def _simulate_binary_capsule(self, gwip_packet):
        return {"emulation": True, "payload": gwip_packet, "timestamp": time.time(), "mode": "binary"}

    def _simulate_binary_to_gwip(self, capsule):
        return capsule.get("payload", {})