# 📁 backend/modules/codex/ops/op_trigger.py

from typing import Any, Dict, List
from backend.modules.codex.virtual.virtual_registers import VirtualRegisters

def op_trigger(args: List[Any], registers: VirtualRegisters, context: Dict[str, Any]) -> str:
    """
    Execute a symbolic trigger within the Codex CPU runtime.

    This may activate dreams, spawn goals, mutate glyphs, or initiate container events.

    Args:
        args (List[Any]): Arguments passed to the trigger op (first is target).
        registers (VirtualRegisters): Virtual register state (unused here).
        context (Dict[str, Any]): Current execution context.

    Returns:
        str: Trigger confirmation message.
    """
    target = args[0] if args else "default_trigger"
    log = f"🚨 Trigger activated: {target}"
    print(log)

    # Store log in runtime trace
    if "trigger_log" not in context:
        context["trigger_log"] = []
    context["trigger_log"].append(log)

    # Optionally mark that trigger occurred
    context["triggered"] = True
    context["last_trigger"] = target

    return log