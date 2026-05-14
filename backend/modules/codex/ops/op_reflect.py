 # 📄 backend/modules/codex/ops/op_reflect.py

from typing import Any, Dict
import datetime

def op_reflect(args: list, registers: Any, context: Dict[str, Any]) -> str:
    """
    Store a symbolic reflection or internal thought trace into memory.

    Args:
        args (list): [thought, [optional metadata]]
        registers: Virtual CPU registers
        context (dict): Execution context

    Returns:
        str: Log confirmation
    """
    thought = args[0] if args else "empty_thought"
    timestamp = datetime.datetime.utcnow().isoformat()

    reflection = {
        "thought": thought,
        "timestamp": timestamp,
        "source": context.get("source", "op_reflect"),
        "container": context.get("container"),
        "extra": args[1] if len(args) > 1 else None
    }

    # Store to context
    if "reflections" not in context:
        context["reflections"] = []
    context["reflections"].append(reflection)

    return f"🧠 Reflection stored: {thought}"