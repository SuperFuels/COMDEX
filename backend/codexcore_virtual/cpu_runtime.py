# 📁 backend/codexcore_virtual/cpu_runtime.py

from typing import List, Dict, Any
from backend.codexcore_virtual.instruction_parser import parse_codex_instructions
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.core.registry_bridge import registry_bridge


class VirtualCPU:
    def __init__(self, mode: str = "raw"):
        """
        Virtual CPU runtime.
        mode = "symatics" (default) or "photon"
        """
        self.mode = mode  # "raw" | "symatics" | "photon"
        self.registers: Dict[str, Any] = {}
        self.stack: List[Any] = []
        self.output: List[str] = []
        self.metrics = CodexMetrics()

    def reset(self):
        self.registers.clear()
        self.stack.clear()
        self.output.clear()

    def execute_instruction(self, instr: Dict[str, Any]) -> Any:
        opcode = instr.get("opcode", "")
        args = instr.get("args", [])

        try:
            # --- Photon / Symatics mode switch ---
            if self.mode == "photon":
                if not opcode.startswith("photon:"):
                    opcode = f"photon:{opcode}"
            elif self.mode == "symatics":
                if not opcode.startswith("symatics:"):
                    opcode = f"symatics:{opcode}"

            # --- Dispatch via registry bridge ---
            result = registry_bridge.resolve_and_execute(
                opcode,
                *args,
                ctx={"mode": self.mode, "cpu": self}
            )

            if result is not None:
                if isinstance(result, dict):
                    if "result" in result:
                        val = result["result"]
                        if self.mode == "photon":
                            from backend.photon_algebra.renderer import render_photon
                            self.output.append(render_photon(val))
                        else:
                            self.output.append(str(val))
                    else:
                        # fallback for dict without explicit 'result'
                        if self.mode == "photon":
                            from backend.photon_algebra.renderer import render_photon
                            self.output.append(render_photon(result))
                        else:
                            self.output.append(str(result))
                else:
                    self.output.append(str(result))

            self.metrics.record_execution()

        except Exception as e:
            self.output.append(f"Execution error in {opcode}: {e}")
            self.metrics.record_error()

    def execute_instruction_list(self, instructions: List[Dict[str, Any]]) -> List[str]:
        self.reset()
        for instr in instructions:
            self.execute_instruction(instr)
        return self.output

# ─── Expression Renderer ──────────────────────────────────────────────

def render_expr(expr: Any) -> str:
    """
    Recursively pretty-print instruction dicts into glyph expressions.
    - Dict with {"opcode": X, "args": [...]} → formatted glyph expression
    - List → join elements with commas
    - Fallback: str(expr)
    """
    if isinstance(expr, dict):
        op = expr.get("opcode", "")
        args = expr.get("args", [])

        # Extract glyph part if opcode looks like "domain:⊕"
        glyph = op.split(":")[-1] if ":" in op else op

        if not args:
            return glyph

        rendered_args = [render_expr(a) for a in args]
        if glyph in {"⊕", "→", "↔", "⟲", "⧖", "⊗"} and len(rendered_args) == 2:
            return f"({rendered_args[0]} {glyph} {rendered_args[1]})"
        elif glyph in {"⟲"} and len(rendered_args) == 1:
            return f"⟲({rendered_args[0]})"
        else:
            return f"{glyph}({', '.join(rendered_args)})"

    elif isinstance(expr, list):
        return ", ".join(render_expr(e) for e in expr)
    else:
        return str(expr)


# 🔁 Example runner (remove in prod)
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VirtualCPU smoke test")
    parser.add_argument(
        "--mode",
        choices=["raw", "symatics", "photon"],
        default="raw",
        help="execution backend to use",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="run both symatics and photon on the same input",
    )
    parser.add_argument(
        "code",
        nargs="?",
        default="Memory:Dream → Plan => ⟲(Think)",
        help="CodexLang input (default sample if omitted)",
    )
    args = parser.parse_args()

    def run(mode: str, code: str):
        cpu = VirtualCPU(mode=mode)
        instrs = parse_codex_instructions(code)
        out = cpu.execute_instruction_list(instrs)
        print(f"--- {mode} ---")
        print("\n".join(out))
        print()

    if args.compare:
        # Compare both backends on the same program
        for m in ("symatics", "photon"):
            run(m, args.code)
    else:
        run(args.mode, args.code)