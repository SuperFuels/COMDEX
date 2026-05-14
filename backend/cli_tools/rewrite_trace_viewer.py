# cli_tools/rewrite_trace_viewer.py

import sys
import json
from pathlib import Path
from rich.console import Console
from rich.tree import Tree
from rich.table import Table

from backend.modules.dna_chain.dc_handler import load_dc_container
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.rewrite.rewrite_executor import suggest_rewrites

console = Console()


def extract_ast(container: dict):
    if "ast" in container:
        return container["ast"]
    elif "glyph_grid" in container:
        return {
            "type": "glyph_program",
            "nodes": container["glyph_grid"]
        }
    elif "electrons" in container:
        return {
            "type": "glyph_program",
            "nodes": [
                glyph for e in container["electrons"] for glyph in e.get("glyphs", [])
            ]
        }
    else:
        raise ValueError("No AST or glyph structure found in container.")


def render_ast_tree(ast_node, parent_tree=None):
    label = ast_node.get("label", ast_node.get("type", "node"))

    if isinstance(ast_node, dict):
        current = Tree(f"[cyan]{label}[/]")
        for k, v in ast_node.items():
            if isinstance(v, (dict, list)):
                continue
            current.add(f"[white]{k}[/]: [green]{v}[/]")

        if parent_tree:
            parent_tree.add(current)

        # Handle children
        if "children" in ast_node:
            for child in ast_node["children"]:
                render_ast_tree(child, current)
        elif "nodes" in ast_node:
            for child in ast_node["nodes"]:
                render_ast_tree(child, current)

        return current
    else:
        return Tree(f"[red]Invalid AST node: {ast_node}[/]")


def view_prediction_summary(container: dict):
    prediction = container.get("prediction", {})
    if not prediction:
        console.print("[yellow]⚠ No prediction metadata found.[/]")
        return

    table = Table(title="🧠 Prediction Summary", show_header=True, header_style="bold magenta")
    table.add_column("Status")
    table.add_column("Confidence", justify="right")
    table.add_column("Entropy", justify="right")
    table.add_column("Suggested", justify="left")

    table.add_row(
        prediction.get("status", "unknown"),
        str(prediction.get("confidence", "-")),
        str(prediction.get("entropy", "-")),
        str(prediction.get("suggestion", "-"))
    )

    console.print(table)


def main(container_path: str):
    container_id = Path(container_path).stem
    container = load_dc_container(container_id)

    console.rule(f"[bold green]AST Viewer: {container_id}[/]")

    try:
        ast = extract_ast(container)
    except Exception as e:
        console.print(f"[red]❌ Error extracting AST:[/] {e}")
        return

    console.print("[blue]🔍 Rendering AST structure...[/]")
    ast_tree = render_ast_tree(ast)
    console.print(ast_tree)

    view_prediction_summary(container)

    # Ask if user wants to see rewrites
    if console.input("\n[yellow]🔁 Show Codex rewrite suggestion? (y/n): [/]").strip().lower() == "y":
        rewrites = suggest_rewrites(container)
        if rewrites:
            console.print("\n[bold green]✅ Codex Rewrite Suggestion:[/]")
            for idx, glyph in enumerate(rewrites):
                console.print(f"[cyan]{idx + 1}.[/] {json.dumps(glyph, indent=2)}\n")
        else:
            console.print("[red]❌ No rewrite suggestion available.[/]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("Usage: python cli_tools/rewrite_trace_viewer.py <path_to_dc.json>")
        sys.exit(1)

    container_file = sys.argv[1]
    main(container_file)