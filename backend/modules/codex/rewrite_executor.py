import copy
import json
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.symbolic_engine.math_logic_kernel import LogicGlyph
from backend.modules.codex.codexlang_rewriter import (
    CodexLangRewriter,
    suggest_rewrite_candidates,
)
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer


def auto_mutate_container(container: dict, autosave: bool = False) -> dict:
    """
    Suggests and applies symbolic rewrites to logic in a container.
    Injects updated glyphs and trace logs into the container.
    Returns the modified container.
    """
    if not container:
        print("⚠️ Empty container passed to auto_mutate_container.")
        return container

    mutated = copy.deepcopy(container)
    mutation_trace = []

    # Check multiple sections where glyphs may exist
    sections = ["glyphs", "glyph_grid", "electrons"]

    for section in sections:
        items = mutated.get(section, [])
        for item in items:
            glyphs = item.get("glyphs") if isinstance(item.get("glyphs"), list) else [item]

            for glyph in glyphs:
                logic = glyph.get("logic")
                if not logic:
                    continue

                try:
                    ast = LogicGlyph.from_string(logic).to_ast()
                except Exception as e:
                    print(f"⚠️ Failed to parse logic in glyph: {e}")
                    continue

                suggestions = suggest_rewrite_candidates(ast)
                if not suggestions:
                    continue

                for suggestion in suggestions:
                    new_ast = suggestion["rewrite"]
                    codex_form = CodexLangRewriter.ast_to_codexlang(new_ast)

                    glyph["logic"] = codex_form
                    mutation_trace.append({
                        "section": section,
                        "original": logic,
                        "rewritten": codex_form,
                        "reason": suggestion.get("reason", "unspecified")
                    })
                    break  # Apply only the first suggestion

    if mutation_trace:
        get_kg_writer().inject_trace_event(mutated, {
            "event": "auto_mutation",
            "details": mutation_trace
        })

        CodexMetrics.record_mutation_event(mutated.get("id", "unknown"), mutation_trace)

        print(f"🧬 Auto-mutation applied: {len(mutation_trace)} rewrites")

        if autosave and "id" in mutated:
            out_path = f"containers/{mutated['id']}.dc.json"
            with open(out_path, "w") as f:
                json.dump(mutated, f, indent=2)
            print(f"📦 Saved auto-mutated container to: {out_path}")
    else:
        print("i️ No rewrites were applicable.")

    return mutated


def apply_rewrite(glyph: LogicGlyph, goal_context=None):
    """
    Attempt a symbolic rewrite on the given glyph.
    Uses CodexLangRewriter and simplifier utilities.

    Args:
        glyph: LogicGlyph to mutate or simplify.
        goal_context: Optional goal alignment context (for scoring).

    Returns:
        A tuple of (rewritten_glyph, trace_entry)
    """
    rewriter = CodexLangRewriter()
    candidates = suggest_rewrite_candidates(glyph)

    if not candidates:
        return glyph, {
            "type": "rewrite",
            "status": "no_candidates",
            "original": glyph.to_dict()
        }

    # Use first candidate
    new_glyph = rewriter.apply_rewrite(glyph, candidates[0])

    trace_entry = {
        "type": "rewrite",
        "original": glyph.to_dict(),
        "candidate": candidates[0],
        "rewritten": new_glyph.to_dict(),
        "status": "success"
    }

    return new_glyph, trace_entry