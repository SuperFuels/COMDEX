# 📁 backend/modules/codex/ops/op_trigger.py

from typing import Any, Dict, List, Optional
from backend.modules.codex.virtual.virtual_registers import VirtualRegisters

def _log_trigger(target: str, context: Dict[str, Any]) -> str:
    log = f"🚨 Trigger activated: {target}"
    print(log)
    context.setdefault("trigger_log", []).append(log)
    context["triggered"] = True
    context["last_trigger"] = target
    return log

def op_trigger(*args, **kwargs) -> str:
    """
    Flexible trigger op adapter.

    Supports legacy and new call shapes:
      A) op_trigger(args: List[Any], registers: VirtualRegisters, context: Dict[str, Any])
      B) op_trigger(context=..., target="foo")
      C) op_trigger(target="foo", context={...})
      D) op_trigger(context=...)  # no target -> "default_trigger"

    Always returns a string summary and never raises on signature mismatches.
    """
    # --- Keyword-only path first (newer callers) ---
    if "context" in kwargs or "target" in kwargs:
        context: Dict[str, Any] = kwargs.get("context") or {}
        target: str = kwargs.get("target") or "default_trigger"
        return _log_trigger(target, context)

    # --- Positional legacy path: (args, registers, context) ---
    target: Optional[str] = None
    context: Dict[str, Any] = {}

    try:
        if len(args) >= 3:
            # Legacy: args[0]=List[Any], args[1]=VirtualRegisters, args[2]=context
            arg_list = args[0] if isinstance(args[0], list) else []
            context = args[2] if isinstance(args[2], dict) else {}
            target = arg_list[0] if arg_list else None
        elif len(args) == 2:
            # Sometimes registers omitted: (args_list, context)
            arg_list = args[0] if isinstance(args[0], list) else []
            context = args[1] if isinstance(args[1], dict) else {}
            target = arg_list[0] if arg_list else None
        elif len(args) == 1 and isinstance(args[0], dict):
            # Just a context dict
            context = args[0]
    except Exception:
        # Fall back safely
        context = kwargs.get("context", {}) or {}

    if not target:
        target = "default_trigger"

    return _log_trigger(str(target), context)