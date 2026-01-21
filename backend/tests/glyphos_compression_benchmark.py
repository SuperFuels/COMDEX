# 📁 backend/tests/glyphos_compression_benchmark.py
from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

# -----------------------------
# Config
# -----------------------------
OPS = {"↔", "⊕", "⟲", "->", "⧖"}

# Compact JSON (wire format)
def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    # mtime=0 makes gzip bytes deterministic if you ever decide to lock raw gz bytes later.
    return gzip.compress(b, compresslevel=level, mtime=0)

def _truthy_env(name: str) -> bool:
    v = os.environ.get(name, "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}

def _locked_output_mode() -> bool:
    # If you set GLYPHOS_FIXED_TS you’re explicitly trying to make the output lockable.
    return bool(os.environ.get("GLYPHOS_FIXED_TS", "").strip()) or _truthy_env("GLYPHOS_LOCK_OUTPUT")

# -----------------------------
# Benchmark glyph tree generator
# -----------------------------
def make_glyph_tree(depth_steps: int = 30) -> Dict[str, Any]:
    """
    Creates a compact glyph operator tree with:
      - a small branch showing ⊕ and ⟲
      - a deep sequential branch showing -> plus (↔, ⊕, ⧖, ⟲) mixed in
    """
    branch1 = {
        "⊕": [
            {"⊕": ["A1", "B1"]},
            {"⟲": ["A2", "B2"]},
        ]
    }

    subtree: Any = {"⟲": ["Z3", "Z4"]}
    subtree = {"->": [{"->": ["Z1", "Z2"]}, subtree]}

    for i in range(depth_steps):
        a = f"L{i}_1"
        b = f"L{i}_2"

        mod = i % 5
        if mod == 0:
            left = {"↔": [a, b]}
        elif mod == 1:
            left = {"⊕": [a, b]}
        elif mod == 2:
            left = {"⧖": [a, b]}
        elif mod == 3:
            left = {"⟲": [a, b]}
        else:
            left = {"->": [a, b]}

        subtree = {"->": [left, subtree]}

    return {"↔": [branch1, subtree]}

# -----------------------------
# Token counting + internal structural score (heuristic)
# -----------------------------
def estimate_tree_tokens(node: Any) -> int:
    if isinstance(node, dict):
        total = 0
        for k, v in node.items():
            total += 1
            total += estimate_tree_tokens(v)
        return total
    if isinstance(node, list):
        return sum(estimate_tree_tokens(x) for x in node)
    if isinstance(node, str):
        return 1
    return 0

def score_glyph_tree_internal(tree: Any) -> int:
    score = 0

    def traverse(n: Any, depth: int = 1):
        nonlocal score
        score += depth
        if isinstance(n, dict):
            for k, v in n.items():
                if k in OPS:
                    score += 3
                traverse(v, depth + 1)
        elif isinstance(n, list):
            for item in n:
                traverse(item, depth + 1)

    traverse(tree, 1)
    return score

# -----------------------------
# Baseline A: Verbose AST (metadata-heavy) -- DETERMINISTIC
# -----------------------------
def _stable_id(seed: str) -> str:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"n{int(h[:8], 16) % 10_000_000}"

def make_verbose_ast(
    node: Any,
    path: str = "$",
    parent_id: str = "root",
    *,
    created_at: str,
) -> Dict[str, Any]:
    if isinstance(node, dict):
        for k, v in node.items():
            child_path = f"{path}.{k}"
            child_id = _stable_id(child_path)

            domain = (
                "quantum" if k in {"↔"} else
                "logic" if k in {"⊕"} else
                "control" if k in {"->", "⟲"} else
                "temporal" if k in {"⧖"} else
                "unknown"
            )

            opname = {
                "↔": "entangle",
                "⊕": "superpose",
                "⟲": "loop",
                "->": "sequence",
                "⧖": "schedule",
            }.get(k, "op")

            children: List[Dict[str, Any]] = []
            if isinstance(v, list):
                for i, item in enumerate(v):
                    children.append(
                        make_verbose_ast(
                            item,
                            path=f"{child_path}[{i}]",
                            parent_id=child_id,
                            created_at=created_at,
                        )
                    )
            else:
                children.append(
                    make_verbose_ast(
                        v,
                        path=f"{child_path}[0]",
                        parent_id=child_id,
                        created_at=created_at,
                    )
                )

            return {
                "node_type": "instruction_node",
                "id": child_id,
                "parent_id": parent_id,
                "path": child_path,
                "span": {"start": 0, "end": 0},
                "domain": domain,
                "opcode": {"name": opname},
                "symbol": k,
                "policy": {
                    "mode": "default",
                    "trace": True,
                    "allow_mutation": False,
                    "observer_constraints": ["public_benchmark"],
                },
                "telemetry": {
                    "container_id": "benchmark_container",
                    "trace_id": "trace_public_bench",
                    "observer": "public_benchmark",
                    "cost_hint": 0.0,
                    "version": "v1",
                    "created_at": created_at,
                },
                "tags": ["baseline", "verbose_ast"],
                "children": children,
            }

    if isinstance(node, list):
        return {
            "node_type": "list",
            "id": _stable_id(path),
            "parent_id": parent_id,
            "path": path,
            "policy": {"trace": True},
            "children": [
                make_verbose_ast(x, path=f"{path}[{i}]", parent_id=parent_id, created_at=created_at)
                for i, x in enumerate(node)
            ],
        }

    if isinstance(node, str):
        return {
            "node_type": "literal",
            "id": _stable_id(path + ":" + node),
            "parent_id": parent_id,
            "path": path,
            "datatype": "string",
            "value": node,
            "telemetry": {"trace": True},
        }

    return {
        "node_type": "literal",
        "id": _stable_id(path + ":null"),
        "parent_id": parent_id,
        "path": path,
        "datatype": "unknown",
        "value": None,
        "telemetry": {"trace": True},
    }

# -----------------------------
# Baseline B: Expanded instruction stream (flat IR)
# -----------------------------
def make_expanded_instructions(tree: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    reg_counter = 0

    def new_reg() -> str:
        nonlocal reg_counter
        r = f"r{reg_counter}"
        reg_counter += 1
        return r

    def emit(domain: str, op: str, symbol: str, args: List[str], value: Any = None) -> str:
        res = new_reg()
        instr = {
            "pc": len(out),
            "domain": domain,
            "op": op,
            "symbol": symbol,
            "args": args,
            "argc": len(args),
            "result": res,
            "trace": True,
            "policy": {"trace": True},
        }
        if value is not None:
            instr["value"] = value
        out.append(instr)
        return res

    def walk(node: Any) -> str:
        if isinstance(node, str):
            return emit("lit", "lit", "lit", [], value=node)

        if isinstance(node, list):
            regs = [walk(x) for x in node]
            return emit("control", "list", "[]", regs)

        if isinstance(node, dict):
            for k, v in node.items():
                domain = (
                    "quantum" if k == "↔" else
                    "logic" if k == "⊕" else
                    "control" if k in {"->", "⟲"} else
                    "temporal" if k == "⧖" else
                    "unknown"
                )
                opname = {
                    "↔": "entangle",
                    "⊕": "superpose",
                    "⟲": "loop",
                    "->": "sequence",
                    "⧖": "schedule",
                }.get(k, "op")

                child_regs = [walk(x) for x in v] if isinstance(v, list) else [walk(v)]
                return emit(domain, opname, k, child_regs)

        return emit("lit", "lit", "lit", [], value=None)

    walk(tree)
    return out

# -----------------------------
# Result schema
# -----------------------------
@dataclass
class BenchResult:
    timestamp: str
    depth_steps: int
    glyph_tree_bytes: int
    glyph_tree_gzip_bytes: int
    baseline_verbose_ast_bytes: int
    baseline_verbose_ast_gzip_bytes: int
    baseline_expanded_instr_bytes: int
    baseline_expanded_instr_gzip_bytes: int
    compression_x_vs_verbose_ast: float
    compression_x_vs_expanded_instr: float
    compression_x_vs_verbose_ast_gzip: float
    compression_x_vs_expanded_instr_gzip: float
    tree_token_count_est: int
    expanded_instruction_count: int
    structural_score_internal: int
    runtime_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

def _fixed_or_now_ts() -> str:
    fixed = os.environ.get("GLYPHOS_FIXED_TS", "").strip()
    if fixed:
        return fixed
    return datetime.now(timezone.utc).isoformat()

def run_benchmark(depth_steps: int = 30) -> BenchResult:
    t0 = time.perf_counter()

    tree = make_glyph_tree(depth_steps=depth_steps)

    glyph_wire = to_wire_json_bytes(tree)
    glyph_gz = gzip_bytes(glyph_wire)

    ts = _fixed_or_now_ts()
    verbose_ast = make_verbose_ast(tree, created_at=ts)
    baseA_wire = to_wire_json_bytes(verbose_ast)
    baseA_gz = gzip_bytes(baseA_wire)

    expanded = make_expanded_instructions(tree)
    baseB_wire = to_wire_json_bytes(expanded)
    baseB_gz = gzip_bytes(baseB_wire)

    compA = (len(baseA_wire) / len(glyph_wire)) if len(glyph_wire) else 0.0
    compB = (len(baseB_wire) / len(glyph_wire)) if len(glyph_wire) else 0.0
    compA_gz = (len(baseA_gz) / len(glyph_gz)) if len(glyph_gz) else 0.0
    compB_gz = (len(baseB_gz) / len(glyph_gz)) if len(glyph_gz) else 0.0

    tokens = estimate_tree_tokens(tree)
    structural = score_glyph_tree_internal(tree)
    dur_ms = (time.perf_counter() - t0) * 1000.0

    return BenchResult(
        timestamp=datetime.now(timezone.utc).isoformat(),
        depth_steps=int(depth_steps),
        glyph_tree_bytes=len(glyph_wire),
        glyph_tree_gzip_bytes=len(glyph_gz),
        baseline_verbose_ast_bytes=len(baseA_wire),
        baseline_verbose_ast_gzip_bytes=len(baseA_gz),
        baseline_expanded_instr_bytes=len(baseB_wire),
        baseline_expanded_instr_gzip_bytes=len(baseB_gz),
        compression_x_vs_verbose_ast=round(compA, 4),
        compression_x_vs_expanded_instr=round(compB, 4),
        compression_x_vs_verbose_ast_gzip=round(compA_gz, 4),
        compression_x_vs_expanded_instr_gzip=round(compB_gz, 4),
        tree_token_count_est=int(tokens),
        expanded_instruction_count=int(len(expanded)),
        structural_score_internal=int(structural),
        runtime_ms=round(dur_ms, 3),
    )

def main() -> None:
    depth_steps = int(os.environ.get("GLYPHOS_BENCH_DEPTH", "30"))
    res = run_benchmark(depth_steps=depth_steps)

    lock_mode = _locked_output_mode()

    print("\n=== ✅ GlyphOS Compression Benchmark (Defensible) ===")
    print(f"Depth steps used:              {res.depth_steps}\n")

    print(f"Glyph (wire JSON):              {res.glyph_tree_bytes} bytes")
    print(f"Glyph (wire JSON, gzip):        {res.glyph_tree_gzip_bytes} bytes\n")

    print(f"Baseline A (verbose AST):       {res.baseline_verbose_ast_bytes} bytes")
    print(f"Baseline A (verbose AST, gzip): {res.baseline_verbose_ast_gzip_bytes} bytes")
    print(f"✅ Compression vs A (raw):       {res.compression_x_vs_verbose_ast}x  (baseline/glyph)")
    print(f"✅ Compression vs A (gzip):      {res.compression_x_vs_verbose_ast_gzip}x\n")

    print(f"Baseline B (expanded instr):       {res.baseline_expanded_instr_bytes} bytes")
    print(f"Baseline B (expanded instr, gzip): {res.baseline_expanded_instr_gzip_bytes} bytes")
    print(f"✅ Compression vs B (raw):          {res.compression_x_vs_expanded_instr}x  (baseline/glyph)")
    print(f"✅ Compression vs B (gzip):         {res.compression_x_vs_expanded_instr_gzip}x\n")

    print(f"Tree token estimate:            {res.tree_token_count_est}")
    print(f"Expanded instruction count:     {res.expanded_instruction_count}")
    print(f"Structural score (internal):    {res.structural_score_internal}")

    if lock_mode:
        # Keep stdout deterministic for tee/sha256 locks.
        print("Runtime:                        (suppressed for lock)")
        # Still show the real runtime for humans without breaking lock output.
        print(f"[runtime] {res.runtime_ms} ms", file=sys.stderr)
    else:
        print(f"Runtime:                        {res.runtime_ms} ms")

    out_dir = "./benchmarks"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "glyphos_compression_latest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"Saved:                          {out_path}\n")

if __name__ == "__main__":
    main()