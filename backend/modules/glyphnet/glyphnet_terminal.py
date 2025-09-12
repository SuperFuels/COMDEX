# File: backend/modules/glyphnet/glyphnet_terminal.py

import time
import logging
from typing import Dict, Any, List, Optional

from ..glyphos.glyph_logic import parse_glyph_packet
from ..glyphos.glyph_executor import execute_glyph_logic
from ..codex.codex_context_adapter import CodexContextAdapter
from ..codex.codex_metrics import record_execution_metrics
from ..hexcore.memory_engine import store_memory
from ..codex.codex_trace import CodexTrace
from ..glyphos.codexlang_translator import run_codexlang_string
from ..glyphos.symbolic_entangler import entangle_glyphs
from ..glyphnet.glyphnet_packet import push_symbolic_packet
from ..glyphnet.glyphnet_crypto import encrypt_packet
from ..encryption.glyph_vault import GlyphVault
from ..glyphnet.ephemeral_key_manager import get_ephemeral_key_manager
from ..glyphnet.symbolic_key_derivation import symbolic_key_deriver

logger = logging.getLogger(__name__)

# Log buffers
command_history: List[str] = []
last_result: Dict[str, Any] = {}
_log_history: List[Dict[str, Any]] = []

AUTHORIZED_TOKENS = {"root_token", "aion_admin", "dev_override"}


def validate_identity(token: str) -> bool:
    return token in AUTHORIZED_TOKENS


def get_public_key_for_identity(identity: str) -> Optional[bytes]:
    try:
        with open(f"keys/{identity}_public.pem", "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


def push_to_glyphnet(result: Dict[str, Any], sender: str, target_id: Optional[str] = None, encrypt: bool = False):
    try:
        packet = {
            "type": "glyph_push",
            "sender": sender,
            "payload": result,
            "timestamp": time.time(),
        }
        if target_id:
            packet["target"] = target_id

        push_mode = "plain"

        if encrypt and target_id:
            key = get_public_key_for_identity(target_id)
            if key:
                encrypted_packet = encrypt_packet(packet, key)
                push_symbolic_packet({
                    "type": "glyph_push_encrypted",
                    "sender": sender,
                    "target": target_id,
                    "payload": encrypted_packet,
                    "timestamp": time.time(),
                })
                push_mode = "rsa"
                logger.info(f"[GlyphPush🔐] Encrypted via RSA: {sender} → {target_id}")
            else:
                ephemeral_manager = get_ephemeral_key_manager()
                seed_phrase = f"GlyphPush:{sender}->{target_id}"
                symbolic_trust = 0.7
                symbolic_emotion = 0.5

                aes_key = ephemeral_manager.get_key(target_id) or ephemeral_manager.generate_key(
                    target_id,
                    trust_level=symbolic_trust,
                    emotion_level=symbolic_emotion,
                    seed_phrase=seed_phrase
                )

                if aes_key:
                    from ..glyphnet.glyphnet_crypto import aes_encrypt_packet
                    encrypted_packet = aes_encrypt_packet(packet, aes_key)
                    push_symbolic_packet({
                        "type": "glyph_push_encrypted_ephemeral",
                        "sender": sender,
                        "target": target_id,
                        "payload": encrypted_packet,
                        "timestamp": time.time(),
                    })
                    push_mode = "aes"
                    logger.info(f"[GlyphPush🔐] Encrypted via AES: {sender} → {target_id}")
                else:
                    logger.warning(f"[GlyphPush] No AES key available for {target_id}. Skipping encryption.")

        if push_mode == "plain":
            push_symbolic_packet(packet)
            logger.info(f"[GlyphPush] Sent unencrypted packet: {sender} → {target_id or 'broadcast'}")

        result["push_mode"] = push_mode

    except Exception as e:
        logger.warning(f"[GlyphPush❌] Delivery failed: {e}")


def run_symbolic_command(command: str, token: str = "", push: bool = False, target_id: Optional[str] = None, encrypt: bool = False) -> Dict[str, Any]:
    if not validate_identity(token):
        return {"status": "unauthorized", "message": "Invalid token"}

    start = time.time()
    try:
        result = run_codexlang_string(command) or {}
        duration = round(time.time() - start, 4)

        command_history.append(command)
        global last_result
        last_result = result

        entry = {
            "type": "symbolic_command",
            "command": command,
            "result": result,
            "duration": duration,
            "timestamp": time.time(),
            "token": token,
        }
        store_log(entry)

        if push:
            push_to_glyphnet(entry, sender=token, target_id=target_id, encrypt=encrypt)

        return {
            "status": "ok",
            "output": result,
            "duration": duration,
            "history_count": len(command_history)
        }

    except Exception as e:
        logger.exception("[Terminal❌] CodexLang execution failed")
        return {
            "status": "error",
            "message": str(e),
            "history_count": len(command_history)
        }


def execute_terminal_command(command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        token = payload.get("token", "")
        if not validate_identity(token):
            return {"status": "unauthorized", "error": "Invalid token"}

        trace_id = payload.get("trace_id")
        enable_push = payload.get("enable_push", False)
        target_id = payload.get("target_id")
        encrypt = payload.get("encrypt", False)

        if command == "execute_glyph":
            glyph_data = payload.get("glyph_data")
            if not glyph_data:
                return {"status": "error", "error": "Missing glyph_data"}

            logic_tree = parse_glyph_packet(glyph_data)
            context = payload.get("context", {})

            result = execute_glyph_logic(logic_tree, context)
            store_memory(result.get("memory"))
            record_execution_metrics("terminal_execute", result)

            if trace_id:
                CodexTrace.log_event("terminal_glyph_executed", {
                    "trace_id": trace_id,
                    "glyph": glyph_data.get("glyph", "[no-glyph]"),
                    "result": result
                })

            log_entry = {
                "type": "glyph_execution",
                "glyph": glyph_data.get("glyph", "[unknown]"),
                "result": result,
                "context": context,
                "timestamp": time.time(),
                "token": token,
            }
            store_log(log_entry)

            if enable_push:
                push_to_glyphnet(log_entry, sender=token, target_id=target_id, encrypt=encrypt)

            return {"status": "ok", "result": result}

        elif command == "entangle_glyphs":
            g1 = payload.get("g1")
            g2 = payload.get("g2")
            if not g1 or not g2:
                return {"status": "error", "error": "Missing glyphs to entangle"}

            link_result = entangle_glyphs(g1, g2)

            log_entry = {
                "type": "entanglement",
                "g1": g1,
                "g2": g2,
                "result": link_result,
                "timestamp": time.time(),
                "token": token,
            }
            store_log(log_entry)

            if enable_push:
                push_to_glyphnet(log_entry, sender=token, target_id=target_id, encrypt=encrypt)

            return {"status": "ok", "entangled": link_result}

        elif command == "unlock_glyphvault":
            container_id = payload.get("container_id")
            avatar_state = payload.get("avatar_state")
            if not container_id or not avatar_state:
                return {"status": "error", "error": "Missing container_id or avatar_state"}

            vault = GlyphVault(container_id)
            unlock_result = vault.decrypt(avatar_state)

            log_entry = {
                "type": "vault_unlock",
                "container": container_id,
                "result": unlock_result,
                "avatar": avatar_state,
                "timestamp": time.time(),
                "token": token,
            }
            store_log(log_entry)

            if enable_push:
                push_to_glyphnet(log_entry, sender=token, target_id=target_id, encrypt=encrypt)

            return {"status": "ok", "unlocked": unlock_result}

        else:
            return {"status": "error", "error": f"Unknown terminal command: {command}"}

    except Exception as e:
        logger.exception("[Terminal❌] Execution failed")
        return {"status": "error", "error": str(e)}


def get_last_result() -> Dict[str, Any]:
    return last_result


def get_command_history(n: int = 10) -> List[str]:
    return command_history[-n:]


def store_log(entry: Dict[str, Any]):
    _log_history.append(entry)
    if len(_log_history) > 200:
        _log_history.pop(0)


def get_recent_logs() -> List[Dict[str, Any]]:
    return _log_history[-200:]