import re
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional
from backend.modules.photon.photon_to_codex import photon_to_codex

logger = logging.getLogger(__name__)
# ───────────────────────────────────────────────
# 🌊 Symatics Bridge (Symbolic Operator Binding)
# ───────────────────────────────────────────────
try:
    from backend.modules.photon.symatics_bridge import run_symatics_wavecapsule
except Exception:
    # Safe fallback stub if symatics not present
    def run_symatics_wavecapsule(spec):
        return {"status": "stub", "detail": f"Symatics stub executed: {spec}"}
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


def execute_capsule(
    capsule: PhotonCapsule,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes a Photon capsule. Handles both normal Photon instructions
    and direct Symatics symbolic operators (⊕, ↔, μ, ⟲, π).
    Cleans stray literals, normalizes schema for photon_to_codex,
    and returns a full symbolic execution envelope with scroll render.
    """
    logger.info(f"[Photon] Executing capsule {capsule.name}")
    results: List[Any] = []

    # ──────────────────────────────
    # 🔧 Clean + normalize capsule body
    # ──────────────────────────────
    cleaned_body: List[Dict[str, Any]] = []
    for g in capsule.body:
        op = g.get("op") or g.get("operator")
        if not op or op == "literal":
            # Skip stray literal glyphs
            continue
        cleaned_body.append({
            "operator": op,
            "name": g.get("name") or g.get("id") or "",
            "args": g.get("args") or g.get("block") or [],
            "logic": g.get("logic", ""),
            "meta": g.get("meta", {}),
        })
    capsule.body = cleaned_body

    # ──────────────────────────────
    # 🧠 Execute symbolic + photon ops
    # ──────────────────────────────
    for instr in capsule.body:
        op = instr.get("operator")
        args = instr.get("args", [])

        # 🧠 Symbolic operator hand-off (⊕, ↔, μ, ⟲, π)
        if op in {"⊕", "↔", "μ", "⟲", "π"}:
            try:
                from backend.symatics.symatics_dispatcher import evaluate_symatics_expr
                sym_result = evaluate_symatics_expr({"op": op, "args": args})

                # Ensure non-null symbolic results
                if sym_result is None:
                    sym_result = {
                        "op": op,
                        "args": args,
                        "result": f"{' '.join(map(str, args))} {op}"
                    }

                results.append(sym_result)
                continue

            except Exception as sym_err:
                logger.warning(f"[Photon:Symatics] Failed symbolic handoff for {op}: {sym_err}")
                results.append({
                    "op": op,
                    "args": args,
                    "error": str(sym_err)
                })
                continue

        # ⚡ Default Photon instruction execution
        try:
            res = execute_instruction(instr, context)
            if isinstance(res, dict) and "status" in res:
                logger.info(f"[Photon:Symatics] {op} → {res.get('status')}")
            results.append(res)
        except Exception as exec_err:
            logger.error(f"[Photon] Execution error on {op}: {exec_err}")
            results.append({"op": op, "error": str(exec_err)})

    # ──────────────────────────────
    # 🧾 Fallback for empty result sets
    # ──────────────────────────────
    if not any(results):
        results = [
            {
                "op": g.get("operator"),
                "args": g.get("args", []),
                "result": f"{' '.join(map(str, g.get('args', [])))} {g.get('operator')}"
            }
            for g in capsule.body
        ]

    # ──────────────────────────────
    # 🌀 Build Codex scroll (for GHX/QFC replay)
    # ──────────────────────────────
    try:
        from backend.modules.photon.photon_to_codex import render_photon_scroll
        scroll = render_photon_scroll([
            type("LG", (), g)() if isinstance(g, dict) else g for g in capsule.body
        ])
    except Exception as e:
        logger.warning(f"[Photon] Scroll render failed: {e}")
        scroll = ""

    # ──────────────────────────────
    # ✅ Final envelope
    # ──────────────────────────────
    status = "success"
    for r in results:
        if isinstance(r, dict) and "error" in r:
            status = "error"
            break

    return {
        "status": status,
        "engine": "symatics",
        "capsule": capsule.name,
        "glyphs": capsule.body,
        "execution": results,
        "scroll": scroll or "symbolic-direct",
    }

# ───────────────────────────────────────────────
# 🧪 Example Plugins (stubs for now)
# ───────────────────────────────────────────────

def handle_knowledge(instr: Dict[str, Any]) -> str:
    return f"[KG] Storing: {instr.get('id')} → {instr.get('block')}"


def handle_qwave(instr: Dict[str, Any]) -> str:
    return f"[QWave] Emitting beam with: {instr.get('id')}"


def handle_logic(instr: Dict[str, Any]) -> str:
    return f"[Logic] Executing ⊕ block with id={instr.get('id')}"

def handle_superposition(instr: Dict[str, Any]) -> str:
    spec = {"opcode": "⊕", "args": instr.get("block") or [instr.get("id")]}
    return run_symatics_wavecapsule(spec)

def handle_entanglement(instr: Dict[str, Any]) -> str:
    spec = {"opcode": "↔", "args": instr.get("block") or [instr.get("id")]}
    return run_symatics_wavecapsule(spec)

def handle_collapse(instr: Dict[str, Any]) -> str:
    spec = {"opcode": "∇", "args": instr.get("block") or [instr.get("id")]}
    return run_symatics_wavecapsule(spec)

def handle_measurement(instr: Dict[str, Any]) -> str:
    spec = {"opcode": "μ", "args": instr.get("block") or [instr.get("id")]}
    return run_symatics_wavecapsule(spec)

# Register defaults + Symatics core ops
register_plugin("%", handle_knowledge)
register_plugin(">", handle_qwave)
register_plugin("⊕", handle_superposition)
register_plugin("↔", handle_entanglement)
register_plugin("∇", handle_collapse)
register_plugin("μ", handle_measurement)
register_plugin("⊕", handle_logic)

# ───────────────────────────────────────────────
# 🌐 Public API for Integration (tests use this)
# ───────────────────────────────────────────────

def execute_photon_capsule(
    capsule: str | Path | Dict[str, Any],
    *,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute a Photon capsule (.phn file or dict) through the Symatics / Photon pipeline.

    Accepts:
      • Path or string ending in .phn
      • dict with {"engine": "...", "body" or "glyphs": [...]}

    Returns a standardized execution envelope:
      {
        "status": "success" | "error",
        "engine": "symatics" | "symbolic" | "codex",
        "capsule": "CapsuleName",
        "glyphs": [...],
        "execution": [...],
        "scroll": "..."
      }
    """
    try:
        # ──────────────────────────────
        # 🗂️ 1. Load capsule
        # ──────────────────────────────
        if isinstance(capsule, (str, Path)) and str(capsule).endswith(".phn"):
            path = Path(capsule)
            capsules = parse_photon_file(path)
            if not capsules:
                raise ValueError(f"No capsules found in {path}")
            capsule_obj = capsules[0]
            engine = "symatics"

        elif isinstance(capsule, dict):
            engine = capsule.get("engine", "symatics")

            raw_body = capsule.get("body") or capsule.get("glyphs") or []
            normalized_body: List[Dict[str, Any]] = []
            for g in raw_body:
                op = g.get("op") or g.get("operator") or "⊕"
                name = g.get("name") or g.get("id") or "unknown"
                args = g.get("args") or g.get("block") or []
                meta = g.get("meta", {})

                if "value" in g and not args:
                    args = [g["value"]]
                if op == "literal":
                    op = "μ"
                if not isinstance(args, list):
                    args = [args]

                normalized_body.append({
                    "operator": op,
                    "name": name,
                    "args": args,
                    "meta": meta,
                })

            capsule_obj = PhotonCapsule(
                capsule.get("name", "unnamed"),
                normalized_body,
            )
        else:
            raise TypeError(f"Unsupported capsule type: {type(capsule)}")

        # ──────────────────────────────
        # 🧠 2. Symbolic fallback route
        # ──────────────────────────────
        spec = capsule if isinstance(capsule, dict) else {}
        if spec.get("engine") == "symbolic":
            from backend.symatics.symatics_dispatcher import evaluate_symatics_expr
            symbolic_results = []
            for g in capsule_obj.body:
                try:
                    res = evaluate_symatics_expr({"op": g["operator"], "args": g["args"]})
                    if res is None:
                        # ensure visible symbolic form
                        res = {
                            "op": g["operator"],
                            "args": g["args"],
                            "result": f"{' '.join(map(str, g['args']))} {g['operator']}"
                        }
                    symbolic_results.append(res)
                except Exception as e:
                    symbolic_results.append({
                        "op": g["operator"],
                        "args": g["args"],
                        "error": str(e)
                    })

            return {
                "status": "success",
                "engine": "symatics",
                "capsule": capsule_obj.name,
                "glyphs": capsule_obj.body,
                "execution": symbolic_results,
                "scroll": "symbolic-direct",
            }

        # ──────────────────────────────
        # ⚡ 3. Execute Photon capsule
        # ──────────────────────────────
        result = execute_capsule(capsule_obj, context=context)

        # ──────────────────────────────
        # 🔗 4. Photon → Codex Bridge
        # ──────────────────────────────
        glyphs_info = photon_to_codex(
            {
                "name": capsule_obj.name,
                "engine": engine,
                "glyphs": capsule_obj.body,
            },
            capsule_id=context.get("capsule_id", "test_capsule") if context else "test_capsule"
        )

        glyphs = [
            g.to_dict() if hasattr(g, "to_dict") else g for g in glyphs_info.get("glyphs", [])
        ]
        scroll = glyphs_info.get("scroll", "") or result.get("scroll", "")

        # ──────────────────────────────
        # 🪶 5. Photon Memory Grid Snapshot
        # ──────────────────────────────
        try:
            from backend.modules.photon_memory.photon_memory_entry import PhotonMemoryEntry
            from backend.modules.photon_memory.photon_memory_grid import PHOTON_MEMORY_GRID
            import time

            exec_results = result.get("execution", [])
            coherence = 0.8 + 0.2 * (len(exec_results) / 10.0)
            entropy = max(0.0, 1.0 - coherence)

            entry = PhotonMemoryEntry(
                wave_id=f"{capsule_obj.name}_{int(time.time())}",
                amplitude=1.0,
                phase=0.5,
                coherence=coherence,
                entropy=entropy,
                operator=capsule_obj.body[0]["operator"] if capsule_obj.body else "?",
                metadata={
                    "capsule_name": capsule_obj.name,
                    "results": exec_results,
                    "engine": engine,
                },
            )
            PHOTON_MEMORY_GRID.record(entry)
        except Exception as pmg_err:
            logger.warning(f"[Photon] PMG record skipped: {pmg_err}")

        # ──────────────────────────────
        # 🧩 Auto-append measurement μ if missing (Lightwave normalization)
        # ──────────────────────────────
        has_symbolic = any(g.get("operator") in {"⊕", "↔", "μ", "⟲", "π"} for g in capsule_obj.body)
        has_measure = any(g.get("operator") == "μ" for g in capsule_obj.body)
        if has_symbolic and not has_measure:
            auto_mu = {"operator": "μ", "name": "auto_measure", "args": ["ψ_auto"], "meta": {}}
            capsule_obj.body.append(auto_mu)
            result["execution"].append({"op": "μ", "args": ["ψ_auto"], "result": "measurement(ψ_auto)"})

        # ──────────────────────────────
        # 🧾 6. Return normalized result
        # ──────────────────────────────
        return {
            "status": result.get("status", "success"),
            "engine": engine,
            "capsule": capsule_obj.name,
            "glyphs": glyphs,
            "execution": result.get("execution", []),
            "scroll": scroll or "symbolic-direct",
        }

    except Exception as e:
        logger.exception("[Photon] Capsule execution failed")
        return {"status": "error", "detail": str(e)}

        # ───────────────────────────────────────────────
        # 🧠 Log resonance snapshot into Photon Memory Grid
        # ───────────────────────────────────────────────
        try:
            from backend.modules.photon_memory.photon_memory_entry import PhotonMemoryEntry
            from backend.modules.photon_memory.photon_memory_grid import PHOTON_MEMORY_GRID

            # Approximate values (later replaced by actual wave data)
            coherence = 0.8 + 0.2 * len(result["results"]) / 10.0
            entropy = max(0.0, 1.0 - coherence)
            entry = PhotonMemoryEntry(
                wave_id=f"{capsule_obj.name}_{int(time.time())}",
                amplitude=1.0,
                phase=0.5,
                coherence=coherence,
                entropy=entropy,
                operator=capsule_obj.body[0]["op"] if capsule_obj.body else "?",
                metadata={
                    "capsule_name": capsule_obj.name,
                    "results": result["results"],
                    "engine": engine,
                }
            )
            PHOTON_MEMORY_GRID.record(entry)
        except Exception as pmg_err:
            logger.warning(f"[Photon] PMG record skipped: {pmg_err}")

        return {
            "status": "success",
            "engine": engine,
            "capsule": capsule_obj.name,
            "glyphs": glyphs,
            "execution": result["results"],
            "scroll": scroll,
        }

    except Exception as e:
        logger.exception("[Photon] Capsule execution failed")
        return {"status": "error", "detail": str(e)}
        
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


__all__ = [
    "PhotonCapsule",
    "parse_photon_file",
    "execute_capsule",
    "execute_photon_capsule",
]