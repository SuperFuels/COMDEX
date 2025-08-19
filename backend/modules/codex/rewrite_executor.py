import copy
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.symbolic_engine.math_logic_kernel import LogicGlyph
from backend.modules.symbolic_engine.rewriters.codex_lang_rewriter import CodexLangRewriter
from backend.modules.symbolic_engine.rewriters.simplifier import suggest_rewrite_candidates
from backend.modules.knowledge_graph.knowledge_trace_utils import inject_into_trace

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
                    break  # Apply only first suggestion

    if mutation_trace:
        inject_into_trace(mutated, {
            "event": "auto_mutation",
            "details": mutation_trace
        })
        CodexMetrics.record_mutation_event(mutated.get("id", "unknown"), mutation_trace)

        print(f"🧬 Auto-mutation applied: {len(mutation_trace)} rewrites")

        if autosave and "id" in mutated:
            import json
            out_path = f"containers/{mutated['id']}.dc.json"
            with open(out_path, "w") as f:
                json.dump(mutated, f, indent=2)
            print(f"📦 Saved auto-mutated container to: {out_path}")
    else:
        print("ℹ️ No rewrites were applicable.")

    return mutated