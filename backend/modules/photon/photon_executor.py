import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────
# 📦 Core Data Structures
# ───────────────────────────────────────────────

class PhotonCapsule:
    def __init__(self, name: str, body: List[Dict[str, Any]]):
        self.name = name
        self.body = body

    def __repr__(self):
        return f"<PhotonCapsule {self.name}, {len(self.body)} instructions>"


# ───────────────────────────────────────────────
# 🔌 Plugin Registry
# ───────────────────────────────────────────────

PLUGIN_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Any]] = {}


def register_plugin(symbol: str, handler: Callable[[Dict[str, Any]], Any]):
    """
    Register a handler for a Photon operator.
    Example: register_plugin("%", handle_knowledge_store)
    """
    PLUGIN_REGISTRY[symbol] = handler
    logger.info(f"[Photon] Registered plugin for {symbol}")


# ───────────────────────────────────────────────
# 🧩 Parser
# ───────────────────────────────────────────────

TOKEN_REGEX = re.compile(r"(\^|⊕|↔|∇|>|%|⟦.*?⟧|\{|\}|[^\s{}]+)")


def tokenize(content: str) -> List[str]:
    return TOKEN_REGEX.findall(content)


def parse(tokens: List[str], i: int = 0) -> (List[Dict[str, Any]], int):
    """
    Recursive descent parser for Photon syntax.
    """
    instructions = []
    while i < len(tokens):
        tok = tokens[i]

        if tok == "}":
            return instructions, i

        if tok in ["^", "⊕", "↔", "∇", ">", "%"]:
            op = tok
            i += 1
            ident = tokens[i] if i < len(tokens) else None
            i += 1

            if i < len(tokens) and tokens[i] == "{":
                block, i = parse(tokens, i + 1)
                instr = {"op": op, "id": ident, "block": block}
                i += 1  # Skip closing }
            else:
                instr = {"op": op, "id": ident, "block": []}

            instructions.append(instr)

        else:
            # Literal or inline expression
            instructions.append({"op": "literal", "value": tok})
            i += 1

    return instructions, i


def parse_photon_file(path: Path) -> List[PhotonCapsule]:
    """
    Load and parse a .phn file into capsules.
    """
    content = path.read_text(encoding="utf-8")
    tokens = tokenize(content)

    capsules = []
    i = 0
    while i < len(tokens):
        if tokens[i] == "^":  # Capsule start
            name = tokens[i + 1]
            block, i = parse(tokens, i + 3)  # Skip ^ name {
            capsule = PhotonCapsule(name, block)
            capsules.append(capsule)
        else:
            i += 1

    return capsules


# ───────────────────────────────────────────────
# ⚡ Executor
# ───────────────────────────────────────────────

def execute_instruction(instr: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
    op = instr.get("op")

    if op == "literal":
        return instr.get("value")

    handler = PLUGIN_REGISTRY.get(op)
    if handler:
        return handler(instr)
    else:
        logger.warning(f"[Photon] No handler for operator {op}, skipping.")
        return None


def execute_capsule(capsule: PhotonCapsule, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    logger.info(f"[Photon] Executing capsule {capsule.name}")
    results = []
    for instr in capsule.body:
        res = execute_instruction(instr, context)
        results.append(res)
    return {"capsule": capsule.name, "results": results}


# ───────────────────────────────────────────────
# 🧪 Example Plugins (stubs for now)
# ───────────────────────────────────────────────

def handle_knowledge(instr: Dict[str, Any]) -> str:
    return f"[KG] Storing: {instr.get('id')} → {instr.get('block')}"


def handle_qwave(instr: Dict[str, Any]) -> str:
    return f"[QWave] Emitting beam with: {instr.get('id')}"


def handle_logic(instr: Dict[str, Any]) -> str:
    return f"[Logic] Executing ⊕ block with id={instr.get('id')}"


# Register defaults
register_plugin("%", handle_knowledge)
register_plugin(">", handle_qwave)
register_plugin("⊕", handle_logic)


# ───────────────────────────────────────────────
# 🏁 CLI Entry Point
# ───────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python photon_executor.py file.phn")
        sys.exit(1)

    path = Path(sys.argv[1])
    capsules = parse_photon_file(path)

    for cap in capsules:
        result = execute_capsule(cap)
        print(json.dumps(result, indent=2, ensure_ascii=False))