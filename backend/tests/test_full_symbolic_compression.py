import os
import json
import logging
from typing import Optional

from backend.modules.codex.codexlang_parser import parse_codexlang_to_ast
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.symbolic.symbol_tree_generator import build_symbolic_tree_from_container
from backend.modules.codex.codex_metrics import estimate_compression_stats, log_benchmark_result

# === Path to the raw CodexLang input file ===
SOURCE_FILE = "backend/tests/test_glyphlogic_module.codex"
CONTAINER_ID = "test_compression_container"
OUTPUT_PATH = f"backend/modules/dimensions/containers/{CONTAINER_ID}.dc.json"
RESULTS_LOG = "backend/tests/compression_results.jsonl"

def run_full_symbolic_compression_test(to_file: Optional[str] = RESULTS_LOG):
    print(f"📥 Reading source file: {SOURCE_FILE}")
    if not os.path.exists(SOURCE_FILE):
        print("❌ Source file does not exist!")
        return

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        source_code = f.read()

    if not source_code.strip():
        print("❌ Source file is empty. Aborting compression.")
        return

    print(f"📘 Step 1: Convert to CodexAST")
    ast_nodes = []
    for i, line in enumerate(source_code.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            parsed = parse_codexlang_to_ast(line)
            if isinstance(parsed, list):
                ast_nodes.extend(parsed)
            else:
                ast_nodes.append(parsed)
        except Exception as e:
            print(f"⚠️  Line {i} parse failed: {e} | Content: {line}")

    if not ast_nodes:
        print("❌ No valid AST nodes parsed.")
        return

    print(f"🔤 Step 2: Encode to Glyphs")
    glyphs = []
    for i, ast in enumerate(ast_nodes, 1):
        try:
            encoded = encode_codex_ast_to_glyphs(ast)
            glyphs.extend(encoded)
        except Exception as encode_err:
            print(f"⚠️  Failed to encode AST #{i}: {ast}. Error: {encode_err}")

    if not glyphs:
        print("❌ No glyphs were successfully encoded.")
        return

    print(f"🌳 Step 3: Build Symbolic Tree")
    try:
        ast_dicts = [ast.to_dict() if hasattr(ast, "to_dict") else ast for ast in ast_nodes]
        glyph_dicts = [g.to_dict() if hasattr(g, "to_dict") else g for g in glyphs]

        container = {
            "id": CONTAINER_ID,
            "format": "codexlang",
            "source": source_code,
            "ast": ast_dicts,
            "glyphs": glyph_dicts,
            "trace": {},
        }

        tree = build_symbolic_tree_from_container(container)
        container["symbolic_tree"] = tree.to_dict()

    except Exception as tree_err:
        print(f"❌ Tree build failed: {tree_err}")
        return

    print(f"📊 Step 4: Estimate Compression Stats")
    try:
        stats = estimate_compression_stats(container)

        # Safely convert compression_ratio if numeric
        raw_ratio = stats.get("compression_ratio", 0)
        try:
            compression_ratio = float(raw_ratio)
        except (TypeError, ValueError):
            compression_ratio = "N/A"
            print(f"⚠️  Compression ratio was not numeric: {raw_ratio}")

        stats.update({
            "container_id": CONTAINER_ID,
            "source_file": SOURCE_FILE,
            "glyph": f"[CodexLang:{CONTAINER_ID}]",
            "qglyph_id": "[not used]",
            "depth_classical": None,
            "depth_qglyph": stats.get("symbolic_depth", None),
            "classical_time": "N/A",
            "qglyph_time": "N/A",
            "compression_ratio": compression_ratio,
            "speedup_ratio": "N/A",
        })

        # ✅ Save to benchmark log file
        log_benchmark_result(stats, to_file=to_file)

        print("📈 Compression Stats:")
        for k, v in stats.items():
            try:
                print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
            except Exception as fmt_err:
                print(f"  {k}: {v}  ⚠️ Format error: {fmt_err}")

        print(f"📝 Stats logged to: {to_file}")

    except Exception as stats_err:
        print(f"⚠️  Compression stats failed: {stats_err}")

    print(f"💾 Step 5: Save Container to: {OUTPUT_PATH}")
    try:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(container, f, indent=2)
        print("✅ Compression test complete.")
    except Exception as save_err:
        print(f"❌ Failed to save container: {save_err}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_full_symbolic_compression_test()