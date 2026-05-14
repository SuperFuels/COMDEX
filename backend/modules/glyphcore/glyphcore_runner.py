# backend/modules/glyphcore/glyphcore_runner.py

from backend.modules.glyphcore.glyphcore_action_switch import ActionSwitch
from backend.modules.glyphcore.action_context_builder import build_action_context
from backend.modules.symbolic.symbolic_executor import execute_symbolic_logic  # Replace if actual path differs
from backend.modules.codex.codex_logger import log_symbolic_event  # Optional: log engine
from backend.modules.glyphwave.holographic.ghx_replay_broadcast import emit_gwave_replay  # 🧠 NEW: Emit GHX replay

from backend.modules.glyphwave.core.wave_state_store import WaveStateStore  # Needed to fetch wave
from typing import Dict, Optional

# You may have a shared store instance - adjust as needed
_wave_store = WaveStateStore()


async def run_symbolic_action(
    op_code: str,
    sender_id: str,
    recipient_id: str,
    payload: Dict,
    wave_id: Optional[str] = None,
    trace_signature: Optional[str] = None,
    override_policies: bool = False,
) -> Dict:
    """
    Runs a symbolic action through GlyphCore, applying enforcement logic before executing.
    """

    # 🧱 Step 1: Build full context (sender, recipient, QKD, roles, entropy)
    context = build_action_context(
        sender_id=sender_id,
        recipient_id=recipient_id,
        wave_id=wave_id,
        trace_signature=trace_signature,
    )

    # ⚖️ Step 2: Run ActionSwitch enforcement (fail closed if not allowed)
    if not override_policies:
        ActionSwitch.enforce(op_code=op_code, context=context)

    # 🚀 Step 3: Execute actual symbolic logic (e.g., symbolic rewrite, KG inject, etc.)
    result = await execute_symbolic_logic(
        op_code=op_code,
        sender=sender_id,
        recipient=recipient_id,
        payload=payload,
        metadata=context,
    )

    # 🌊 Step 3.5: Emit GHX replay trace if wave is known
    if wave_id:
        wave = _wave_store.get_wave(wave_id)
        if wave:
            emit_gwave_replay(wave)

    # 📜 Step 4: Optionally log event for auditing
    log_symbolic_event(
        event="symbolic_action_executed",
        sender=sender_id,
        op_code=op_code,
        metadata=context,
    )

    return {
        "status": "success",
        "result": result,
        "enforced": not override_policies,
        "context": context,
    }