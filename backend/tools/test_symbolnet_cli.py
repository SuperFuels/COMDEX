# File: backend/tools/test_symbolnet_cli.py

import argparse
from rich import print
from rich.panel import Panel
from rich.console import Console

from backend.modules.symbolnet.symbolnet_plugin import SymbolNetPlugin
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.symbolnet.symbolnet_bridge import SymbolNetBridge
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph, SymbolGlyph
from backend.modules.symbolic.symbolic_parser import (
    parse_raw_input_to_ast,
    parse_codexlang_to_ast
)

console = Console()

SKIP_GLYPHS = {"∀", "→", "∧", "∨", "¬", "∅", "=", "≠", "<", ">", "≥", "≤"}

def test_symbolnet_enrichment(input_text: str, sources: list[str]):
    """
    Full enrichment pipeline:
    1. Parse input → CodexAST (raw input or CodexLang)
    2. Convert to CodexLang for canonical normalization
    3. Parse CodexLang → CodexAST → LogicGlyphs
    4. Enrich each glyph using SymbolNetPlugin
    5. If parsing fails, fallback to symbolic glyph creation
    """
    glyphs = []

    try:
        # Step 1a: Try natural language or dict input
        ast = parse_raw_input_to_ast(input_text)
        rewriter = CodexLangRewriter()
        codex_lang = rewriter.simplify(rewriter.ast_to_codexlang(ast))
        codex_ast = parse_codexlang_to_ast(codex_lang)
        glyph_dicts = encode_codex_ast_to_glyphs(codex_ast.to_dict())
        glyphs = [LogicGlyph.from_dict(gd) for gd in glyph_dicts]

    except Exception:
        try:
            # Step 1b: Try direct CodexLang fallback
            codex_ast = parse_codexlang_to_ast(input_text)
            glyph_dicts = encode_codex_ast_to_glyphs(codex_ast.to_dict())
            glyphs = [LogicGlyph.from_dict(gd) for gd in glyph_dicts]
        except Exception:
            # Step 1c: Fallback to freeform glyph (e.g., "photon")
            stripped = input_text.strip()
            if stripped:
                console.print(f"\n[bold yellow]⚠️ Parsing failed — treating as symbolic glyph:[/bold yellow] '[white]{stripped}[/white]'\n")
                glyphs = [SymbolGlyph.from_dict({
                    "type": "symbol",
                    "symbol": stripped,
                    "metadata": {}
                })]
            else:
                console.print(f"\n[bold red]❌ Failed to parse input as natural language or CodexLang:[/bold red] '[white]{input_text}[/white]'")
                console.print_exception()
                return

    # Step 2: Enrich using SymbolNet
    plugin = SymbolNetPlugin(enabled_sources=sources)
    enriched_count = 0
    skipped_count = 0

    for glyph in glyphs:
        # Safe label extraction
        label = (
            getattr(glyph, "symbol", None)
            or getattr(glyph, "operator", None)
            or glyph.get("symbol")
            or glyph.get("operator")
            or glyph.get("metadata", {}).get("symbol")
            or "∅"
        )

        if label in SKIP_GLYPHS:
            skipped_count += 1
            continue

        before = dict(getattr(glyph, "metadata", {})) if hasattr(glyph, "metadata") else dict(glyph.get("metadata", {}))
        plugin.apply(glyph)
        after = getattr(glyph, "metadata", {}) if hasattr(glyph, "metadata") else glyph.get("metadata", {})

        new_keys = set(after) - set(before)

        if new_keys:
            enriched_count += 1
            diff_data = {k: after[k] for k in new_keys}
            console.print(Panel.fit(
                f"[bold cyan]Glyph:[/bold cyan] {label}\n\n"
                f"[bold yellow]→ New Metadata:[/bold yellow]\n{diff_data}",
                title="🧠 Enriched Glyph",
                subtitle=", ".join(sources),
                border_style="green"
            ))
        else:
            console.print(Panel.fit(
                f"[bold cyan]Glyph:[/bold cyan] {label}\n\n"
                f"[dim]No enrichment found from sources: {sources}[/dim]",
                title="🟡 Unchanged Glyph",
                border_style="grey50"
            ))

    # Final summary
    console.print(f"\n[bold green]✅ Enriched {enriched_count} glyph(s)[/bold green], "
                  f"[blue]Skipped {skipped_count} glyph(s)[/blue] "
                  f"from input: '[white]{input_text}[/white]'\n")


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("text", type=str, help="Symbolic or natural language input")
    argp.add_argument("--sources", nargs="+", default=["conceptnet", "wikidata"],
                      help="SymbolNet sources to use (e.g. conceptnet, wikidata, wordnet)")
    args = argp.parse_args()
    test_symbolnet_enrichment(args.text, args.sources)