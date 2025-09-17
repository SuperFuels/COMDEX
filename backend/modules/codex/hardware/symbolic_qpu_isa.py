# ===============================
# 📁 backend/modules/codex/hardware/symbolic_qpu_isa.py
# ===============================
"""
Symbolic QPU ISA for CodexCore
--------------------------------
- Maps symbolic opcodes to Python execution stubs for SQS / GlyphCell
- Entanglement / superposition / collapse primitives
- Prediction forks / mutation / SQI hooks
- Metrics logging and production-ready integration
- YAML-compatible registry
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import time
import yaml
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
from backend.modules.patterns.pattern_trace_engine import record_trace

# -------------------------------
# Global runtime flags & metrics
# -------------------------------
GLOBAL_QPU_FLAGS: Dict[str, bool] = {
    "entangle_enabled": True,
    "collapse_enabled": True,
    "superpose_enabled": True,
    "metrics_enabled": True
}

QPU_METRICS: Dict[str, float] = {
    "ops_executed": 0,
    "entangle_count": 0,
    "collapse_count": 0,
    "superpose_count": 0
}

# -------------------------------
# Helper: Log metrics & timing
# -------------------------------
def log_qpu_op(op_name: str):
    if GLOBAL_QPU_FLAGS["metrics_enabled"]:
        start_time = time.time()
        QPU_METRICS["ops_executed"] += 1
        print(f"[QPU] Executed opcode: {op_name}")
        QPU_METRICS[f"{op_name}_time"] = time.time() - start_time

# -------------------------------
# Core Opcode Implementations
# -------------------------------
def op_AND(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> str:
    log_qpu_op("AND ⊕")
    return " + ".join(map(str, args))

def op_EQ(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> str:
    log_qpu_op("EQUIVALENCE ↔")
    if len(args) < 2:
        return "[EQ ERROR: Need 2 args]"
    context.setdefault("entangled_pairs", []).append((args[0], args[1]))
    QPU_METRICS["entangle_count"] += 1
    cell: Optional[GlyphCell] = context.get("cell")
    if cell:
        cell.append_trace(f"[QPU] Entangled {args[0]} ↔ {args[1]} state={hash(args[0]) ^ hash(args[1])}")
    return f"[Entangled {args[0]} ↔ {args[1]}]"

def op_MUTATE(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("MUTATE ⟲")
    return [f"{a}_mut" for a in args]

def op_DELAY(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> str:
    log_qpu_op("DELAY ⧖")
    return f"[Delayed {args}]"

def op_TRIGGER(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> str:
    log_qpu_op("TRIGGER →")
    target = args[0] if args else "default_trigger"
    context.setdefault("triggered_ops", []).append(target)
    return f"[Triggered {target}]"

def op_COMPRESS(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> str:
    log_qpu_op("COMPRESS ∇")
    return f"[Compressed {args}]"

def op_NEGATE(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("NEGATE ⊗")
    return [f"¬{a}" for a in args]

def op_MILESTONE(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> str:
    log_qpu_op("MILESTONE ✦")
    return f"[Milestone {args}]"

# -------------------------------
# Quantum Primitives (Stubs)
# -------------------------------
def apply_entanglement(cell: GlyphCell) -> bool:
    if GLOBAL_QPU_FLAGS["entangle_enabled"]:
        QPU_METRICS["entangle_count"] += 1
        cell.append_trace("🔗 Entanglement applied")
        return True
    return False

def apply_collapse(cell: GlyphCell) -> bool:
    if GLOBAL_QPU_FLAGS["collapse_enabled"]:
        QPU_METRICS["collapse_count"] += 1
        cell.append_trace("💥 Collapse triggered")
        return True
    return False

def apply_superpose(cell: GlyphCell) -> bool:
    if GLOBAL_QPU_FLAGS["superpose_enabled"]:
        QPU_METRICS["superpose_count"] += 1
        cell.append_trace("🔮 Superposition enabled")
        return True
    return False

# -------------------------------
# Prediction Fork Integration
# -------------------------------
def update_cell_prediction(cell: GlyphCell) -> List[str]:
    forks: List[str] = []
    base = cell.prediction or ""
    emo = (cell.emotion or "neutral").lower()
    if emo in ["curious", "inspired"]:
        forks.append(f"{base} + exploratory")
    elif emo in ["protective", "cautious"]:
        forks.append(f"{base} + conservative")
    else:
        forks.append(base)
    if "if" in (cell.logic or ""):
        forks.append(f"{base} | conditional path")
    cell.prediction_forks = forks
    cell.append_trace(f"🔮 Prediction forks updated: {forks}")
    return forks

# -------------------------------
# Execute a single opcode
# -------------------------------
def execute_qpu_opcode(
    op: str,
    args: List[Any],
    cell: Optional[GlyphCell] = None,
    context: Optional[Dict[str, Any]] = None
) -> Any:
    context = context or {}
    cell = cell or GlyphCell(id="unknown", logic="", position=[0,0,0,0])
    try:
        func = SYMBOLIC_QPU_OPS.get(op)
        if not func:
            return f"[UnknownOpcode {op}]"

        context["cell"] = cell  # Provide cell to op functions for hooks
        result = func(args, context)
        apply_entanglement(cell)
        apply_collapse(cell)
        apply_superpose(cell)
        update_cell_prediction(cell)
        record_trace(cell.id, f"[QPU EXEC] {op}({args}) → {result}")
        return result
    except Exception as e:
        record_trace(cell.id, f"[QPU Error] {op}: {e}")
        return f"[Error {op}: {e}]"

# -------------------------------
# Load opcode registry from YAML (optional)
# -------------------------------
def load_opcode_registry_from_yaml(filepath: str) -> None:
    global SYMBOLIC_QPU_OPS
    try:
        with open(filepath, "r") as f:
            opcodes_yaml = yaml.safe_load(f)
        SYMBOLIC_QPU_OPS = {op["symbol"]: globals().get(f"op_{op['name']}", lambda *a, **k: "[Stub]") 
                            for op in opcodes_yaml}
        print(f"[QPU] Loaded {len(SYMBOLIC_QPU_OPS)} opcodes from {filepath}")
    except Exception as e:
        print(f"[QPU Error] Failed to load YAML opcodes: {e}")

# -------------------------------
# Populate the default opcode registry
# -------------------------------
SYMBOLIC_QPU_OPS = {
    "⊕": op_AND,
    "↔": op_EQ,
    "⟲": op_MUTATE,
    "⧖": op_DELAY,
    "→": op_TRIGGER,
    "∇": op_COMPRESS,
    "⊗": op_NEGATE,
    "✦": op_MILESTONE
}

# -------------------------------
# Reset / Metrics Utilities
# -------------------------------
def reset_qpu_metrics() -> None:
    for key in QPU_METRICS:
        QPU_METRICS[key] = 0

def get_qpu_metrics() -> Dict[str, float]:
    return dict(QPU_METRICS)

# -------------------------------
# Standalone Test
# -------------------------------
if __name__ == "__main__":
    test_cell = GlyphCell(id="cell_001", logic="⊕ ↔ ⟲ → ✦", position=[0,0])
    context: Dict[str, Any] = {}
    print(execute_qpu_opcode("⊕", ["a", "b"], test_cell, context))
    print(execute_qpu_opcode("↔", ["x", "y"], test_cell, context))
    print(get_qpu_metrics())