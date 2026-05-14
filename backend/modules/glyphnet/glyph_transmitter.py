import logging
import time
from typing import List, Literal, Dict, Optional

import numpy as np

from backend.modules.glyphnet.glyphwave_encoder import glyphs_to_waveform, save_wavefile
from backend.modules.glyphwave.carrier.carrier_scheduler import CarrierScheduler

try:
    import sounddevice as sd
except ImportError:
    sd = None

# 🔐 QKD + Encryption Imports (Q1f/Q1g)
from backend.modules.glyphwave.qkd_handshake import GKeyStore
from backend.modules.glyphwave.qkd.gkey_encryptor import GWaveEncryptor
from backend.modules.glyphwave.qkd.qkd_policy_enforcer import QKDPolicyEnforcer
from backend.modules.exceptions.tampered_payload import TamperedPayloadError
from backend.modules.glyphwave.telemetry_handler import log_beam

# 🔭 Holographic Projection (H7)
from backend.modules.glyphwave.holographic_projection import generate_ghx_projection

logger = logging.getLogger(__name__)

CHANNEL = Literal["audio", "led", "rf"]

# ──────────────────────────────────────────────
# 🎙️ Symbolic Glyph Transmission (raw channel)
# ──────────────────────────────────────────────
def transmit_glyphs(
    symbols: List[str],
    channel: CHANNEL = "audio",
    gain: float = 0.7,
    duration: float = 2.0
) -> Dict[str, any]:
    """
    Transmit symbolic glyphs through a selected physical channel.
    """
    try:
        waveform = glyphs_to_waveform(symbols)

        response = {"status": "ok", "channel": channel}

        if channel == "audio":
            if sd:
                sd.play(waveform, samplerate=44100)
                sd.wait()
                response["details"] = "Audio transmitted"
            else:
                response["error"] = "sounddevice not available"

        elif channel == "led":
            logger.info("[LED] Symbolic LED transmission not implemented in software mode.")
            response["warning"] = "LED not active in current environment"

        elif channel == "rf":
            logger.info("[RF] Symbolic RF transmission not implemented in current env.")
            response["warning"] = "RF hardware not active"

        else:
            return {"status": "error", "error": f"Unknown channel {channel}"}

        return response

    except Exception as e:
        logger.exception("[Transmitter] Failed to transmit glyphs")
        return {"status": "error", "error": str(e)}

# ──────────────────────────────────────────────
# 📡 QKD-Protected Wave Transmission
# ──────────────────────────────────────────────
def push_wave(wave_packet: dict, max_retries: int = 1) -> dict:
    """
    Push a symbolic wave packet using QKD encryption, with auto-renegotiation on failure.
    Also selects optimal carrier/modulation before transmission.
    Emits telemetry via log_beam().
    """
    sender = wave_packet.get("sender_id")
    recipient = wave_packet.get("recipient_id")
    payload = wave_packet.get("payload", {})
    channel = wave_packet.get("channel", "audio")
    gain = wave_packet.get("gain", 0.7)
    duration = wave_packet.get("duration", 2.0)

    # 🧠 Carrier Selection
    carrier_type, modulation = CarrierScheduler.select(
        payload=payload,
        sender_id=sender,
        recipient_id=recipient,
        context=wave_packet.get("context", {})
    )

    # Inject carrier metadata
    wave_packet["carrier"] = {
        "type": carrier_type.name,
        "modulation": modulation
    }

    # 🔭 H7: Inject GHX projection beam if container is present
    container = payload.get("container")
    if container:
        ghx_beam = generate_ghx_projection(container)
        wave_packet["ghx_beam"] = ghx_beam

    # 🔐 QKD Enforcement
    qkd_enforcer = QKDPolicyEnforcer()

    if not qkd_enforcer.enforce_policy(wave_packet):
        logger.warning("[QKD] Policy enforcement failed - wave blocked")
        log_beam("blocked", signal_power=0.0, noise_power=1e-4, meta={"sender": sender, "recipient": recipient})
        return {
            "status": "blocked",
            "reason": "QKD policy violation",
            "qkd_used": False
        }

    if not qkd_enforcer.is_qkd_required(wave_packet):
        # QKD not required: transmit raw glyphs
        symbols = payload.get("symbols", [])
        transmit_result = transmit_glyphs(symbols, channel=channel, gain=gain, duration=duration)

        log_beam(
            "emitted",
            signal_power=0.03,
            noise_power=1e-5,
            meta={
                "qkd_used": False,
                "sender": sender,
                "recipient": recipient,
                "carrier": carrier_type.name,
                "modulation": modulation
            }
        )

        return {
            "status": transmit_result.get("status", "ok"),
            "qkd_used": False,
            "carrier_type": carrier_type.name,
            "modulation": modulation,
            "transmitted_payload": payload
        }

    # ✅ QKD Required: encrypt + retry if tampered
    gkey_store = GKeyStore()
    attempts = 0
    while attempts <= max_retries:
        gkey_pair = gkey_store.get_key_pair(sender, recipient)
        if not gkey_pair:
            logger.error(f"[QKD] No GKey found for {sender} -> {recipient}")
            log_beam("error", signal_power=0.0, noise_power=1e-4, meta={"error": "Missing GKey", "sender": sender})
            return {
                "status": "error",
                "error": "Missing GKey",
                "qkd_used": False
            }

        encryptor = GWaveEncryptor(gkey_pair)
        encrypted_blob = encryptor.encrypt_payload(payload)

        wrapped_payload = {
            "encrypted": encrypted_blob,
            "qkd_encrypted": True,
            "original_sender": sender,
            "qkd_metadata": {
                "sender": sender,
                "recipient": recipient
            },
            "carrier": {
                "type": carrier_type.name,
                "modulation": modulation
            }
        }

        try:
            # Test decryption (simulate receiver validation)
            _ = encryptor.decrypt_payload({"encrypted": encrypted_blob})
            logger.info(f"[QKD] Payload encrypted successfully for {sender} -> {recipient}")

            log_beam(
                "emitted",
                signal_power=0.07,
                noise_power=1e-6,
                meta={
                    "qkd_used": True,
                    "sender": sender,
                    "recipient": recipient,
                    "carrier": carrier_type.name,
                    "modulation": modulation
                }
            )

            return {
                "status": "ok",
                "qkd_used": True,
                "carrier_type": carrier_type.name,
                "modulation": modulation,
                "transmitted_payload": wrapped_payload
            }

        except TamperedPayloadError:
            logger.warning(f"[QKD] Decryption failed - triggering renegotiation attempt {attempts + 1}/{max_retries}")
            gkey_store.renegotiate(sender, recipient)
            attempts += 1
            time.sleep(2 ** attempts)

    # ❌ Max attempts failed
    log_beam(
        "failed",
        signal_power=0.0,
        noise_power=5e-4,
        meta={
            "qkd_used": True,
            "error": "QKD renegotiation failed",
            "sender": sender,
            "recipient": recipient,
            "attempts": attempts
        }
    )

    return {
        "status": "error",
        "error": "QKD renegotiation failed",
        "qkd_used": True,
        "attempts": attempts
    }