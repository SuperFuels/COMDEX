# backend/modules/codex/tests/glyph_compression_benchmark.py
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

from backend.modules.codex.codex_metrics import score_glyph_tree

# Reuse your existing benchmark tree by importing it (or paste it here)
from backend.modules.codex.tests.google_benchmark_runner import compressed_qglyph_tree


OP_KEYS = {"↔", "⧖", "⟲", "⊕", "->"}


def expand_tree_to_tokens(node: Any, out: List[str]) -> None:
    """
    Deterministic 'expanded' representation:
      - operator keys become tokens
      - leaf strings become tokens
    This approximates an uncompressed instruction stream.
    """
    if isinstance(node, dict):
        for k, v in node.items():
            if k in OP_KEYS:
                out.append(k)
            else:
                out.append(f"key:{k}")
            expand_tree_to_tokens(v, out)
    elif isinstance(node, list):
        for item in node:
            expand_tree_to_tokens(item, out)
    else:
        # leaf atom (string/int/etc.)
        out.append(str(node))


def bytes_of_json(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def run(tree: Dict[str, Any], out_dir: str = "./benchmarks") -> Dict[str, Any]:
    t0 = time.perf_counter()

    # 1) "Compressed" representation (your glyph tree JSON)
    glyph_tree_bytes = bytes_of_json(tree)

    # 2) "Expanded" representation (token stream approximating classic instruction list)
    tokens: List[str] = []
    expand_tree_to_tokens(tree, tokens)
    expanded_text = " ".join(tokens)
    expanded_bytes = len(expanded_text.encode("utf-8"))

    # 3) Extra metrics (useful, but keep claims honest)
    structural_score = score_glyph_tree(tree)
    token_count = len(tokens)

    dt_ms = (time.perf_counter() - t0) * 1000

    # Compression ratios (defensible)
    # - If > 1.0, glyph tree is smaller than expanded representation
    compression_ratio_bytes = round(expanded_bytes / max(glyph_tree_bytes, 1), 4)
    compression_ratio_tokens = round(token_count / max(len(json.dumps(tree)), 1), 6)  # optional “density”, not marketing

    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "kind": "GLYPH_COMPRESSION_BENCHMARK",
        "glyph_tree_bytes": glyph_tree_bytes,
        "expanded_bytes": expanded_bytes,
        "compression_ratio_bytes": compression_ratio_bytes,
        "expanded_token_count": token_count,
        "structural_score": structural_score,
        "runtime_ms": round(dt_ms, 2),
    }

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "glyph_compression_latest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("\n=== ✅ GlyphOS Compression Benchmark ===")
    print(f"Glyph tree bytes:      {glyph_tree_bytes}")
    print(f"Expanded bytes:        {expanded_bytes}")
    print(f"Compression (bytes):   {compression_ratio_bytes}x  (expanded / glyph_tree)")
    print(f"Expanded token count:  {token_count}")
    print(f"Structural score:      {structural_score}  (internal heuristic)")
    print(f"Runtime:               {dt_ms:.2f} ms")
    print(f"Saved:                 {out_path}\n")

    return payload


if __name__ == "__main__":
    run(compressed_qglyph_tree)
