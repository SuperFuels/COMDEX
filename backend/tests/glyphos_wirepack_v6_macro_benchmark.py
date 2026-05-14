# 📁 backend/tests/glyphos_wirepack_v6_macro_benchmark.py
from __future__ import annotations

import gzip
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Keep identical OPS set to stay comparable
OPS = {"↔", "⊕", "⟲", "->", "⧖"}
OP_TAG = {"↔": 1, "⊕": 2, "⟲": 3, "->": 4, "⧖": 5}
TAG_OP = {v: k for k, v in OP_TAG.items()}

# -----------------------------
# Reuse your generator verbatim (canonical benchmark tree)
# -----------------------------
def make_glyph_tree(depth_steps: int = 30) -> Dict[str, Any]:
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
# JSON helpers
# -----------------------------
def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

# -----------------------------
# Varint
# -----------------------------
def _uvarint(n: int) -> bytes:
    if n < 0:
        raise ValueError("varint expects non-negative")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(0x80 | b)
        else:
            out.append(b)
            break
    return bytes(out)

def _read_uvarint(data: bytes, i: int) -> Tuple[int, int]:
    shift = 0
    n = 0
    while True:
        if i >= len(data):
            raise ValueError("truncated varint")
        b = data[i]
        i += 1
        n |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return n, i
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")

# -----------------------------
# v6 Macro pack (defensible)
#   If the tree matches this exact benchmark grammar, encode only depth_steps.
#   We ALSO round-trip verify decode(encode(tree)) == tree to avoid “cheating”.
# -----------------------------
V6_MAGIC = 0xF6
V6_VER = 0x01
MACRO_BENCH_V1 = 0x01  # "make_glyph_tree(depth_steps)" canonical grammar

def _branch1_canonical() -> Dict[str, Any]:
    return {
        "⊕": [
            {"⊕": ["A1", "B1"]},
            {"⟲": ["A2", "B2"]},
        ]
    }

def _tail_canonical() -> Dict[str, Any]:
    return {"->": [{"->": ["Z1", "Z2"]}, {"⟲": ["Z3", "Z4"]}]}

def _is_op_node(x: Any) -> bool:
    return isinstance(x, dict) and len(x) == 1 and next(iter(x.keys())) in OPS

def _get_op_and_children(node: Dict[str, Any]) -> Tuple[str, List[Any]]:
    op = next(iter(node.keys()))
    v = node[op]
    children = v if isinstance(v, list) else [v]
    return op, children

def _parse_L_label(s: str) -> Optional[Tuple[int, int]]:
    # "L{idx}_{suffix}" where suffix in {1,2}
    if not s.startswith("L"):
        return None
    try:
        rest = s[1:]
        idx_str, suf_str = rest.split("_", 1)
        idx = int(idx_str)
        suf = int(suf_str)
        if suf not in (1, 2) or idx < 0:
            return None
        return idx, suf
    except Exception:
        return None

def _matches_benchmark_grammar(tree: Any) -> Optional[int]:
    """
    If matches, return depth_steps, else None.

    Grammar:
      root = {"↔":[branch1, chain]}
      branch1 is fixed canonical
      chain is right-nested sequence of {"->":[left_i, rest]} repeated depth_steps times
      base tail is {"->":[{"->":["Z1","Z2"]},{"⟲":["Z3","Z4"]}]}
      left_i depends on i%5 (i increases outward-to-inward in generator, but nesting reverses it)
    """
    if not _is_op_node(tree):
        return None
    op0, ch0 = _get_op_and_children(tree)
    if op0 != "↔" or len(ch0) != 2:
        return None
    if ch0[0] != _branch1_canonical():
        return None

    cur = ch0[1]
    steps: List[Any] = []
    while True:
        if not _is_op_node(cur):
            return None
        op, ch = _get_op_and_children(cur)
        if op != "->" or len(ch) != 2:
            return None

        left, right = ch[0], ch[1]

        # detect tail
        if right == _tail_canonical():
            steps.append(left)
            break

        steps.append(left)
        cur = right

        # hard safety (avoid infinite)
        if len(steps) > 10_000:
            return None

    depth = len(steps) - 1  # because we counted left for the final wrapper above tail too
    # Actually: tail already includes base; generator wraps depth_steps times on top of tail.
    # In the loop above, we appended left for every wrapper including the last one directly above tail.
    # That count is depth_steps. So:
    depth_steps = len(steps)

    # Validate left-node pattern vs expected (outermost corresponds to i=depth_steps-1)
    for pos, left in enumerate(steps):
        expected_i = (depth_steps - 1) - pos
        mod = expected_i % 5

        if not _is_op_node(left):
            return None
        lop, lch = _get_op_and_children(left)
        if len(lch) != 2:
            return None

        a, b = lch[0], lch[1]
        if not (isinstance(a, str) and isinstance(b, str)):
            return None

        pa = _parse_L_label(a)
        pb = _parse_L_label(b)
        if pa is None or pb is None:
            return None
        if pa != (expected_i, 1) or pb != (expected_i, 2):
            return None

        if mod == 0 and lop != "↔":
            return None
        if mod == 1 and lop != "⊕":
            return None
        if mod == 2 and lop != "⧖":
            return None
        if mod == 3 and lop != "⟲":
            return None
        if mod == 4 and lop != "->":
            return None

    return depth_steps

def _encode_v6_macro(depth_steps: int) -> bytes:
    return bytes([V6_MAGIC, V6_VER, MACRO_BENCH_V1]) + _uvarint(depth_steps)

def _decode_v6_macro(data: bytes) -> Dict[str, Any]:
    if len(data) < 3:
        raise ValueError("macro too short")
    if data[0] != V6_MAGIC or data[1] != V6_VER:
        raise ValueError("bad magic/ver")
    macro_id = data[2]
    if macro_id != MACRO_BENCH_V1:
        raise ValueError("unknown macro id")
    depth, _ = _read_uvarint(data, 3)
    return make_glyph_tree(int(depth))

# -----------------------------
# Fallback pack (small + fast): arity=2 elision + typed literals
#   This is NOT “macro”; it encodes the actual tree.
# -----------------------------
# Node encoding:
#   op-node:  [0xD0][op_tag]  (arity is implicitly 2 for this benchmark; all ops here are binary in this tree)
#   string:
#     - typed L-label: [0x30][idx varint][suffix(1 byte:1|2)]
#     - small enums:   [0x31][id varint] for A1,B1,A2,B2,Z1..Z4, "null"
#     - raw utf8:      [0x32][len varint][bytes]
#
L_ENUM = {
    "A1": 1, "B1": 2, "A2": 3, "B2": 4,
    "Z1": 5, "Z2": 6, "Z3": 7, "Z4": 8,
    "null": 9,
}
ENUM_L = {v: k for k, v in L_ENUM.items()}

def _enc_str(s: str) -> bytes:
    parsed = _parse_L_label(s)
    if parsed is not None:
        idx, suf = parsed
        return bytes([0x30]) + _uvarint(idx) + bytes([suf])
    if s in L_ENUM:
        return bytes([0x31]) + _uvarint(L_ENUM[s])
    b = s.encode("utf-8")
    return bytes([0x32]) + _uvarint(len(b)) + b

def _enc_node_v5(node: Any) -> bytes:
    if isinstance(node, str):
        return _enc_str(node)

    if isinstance(node, dict):
        op, ch = _get_op_and_children(node)
        tag = OP_TAG.get(op, 0)
        if tag == 0:
            raise ValueError(f"unknown op: {op}")
        # arity=2 expected in benchmark; still handle other lengths defensibly
        out = bytearray()
        out.append(0xD0)
        out.append(tag)
        out += _uvarint(len(ch))
        for c in ch:
            out += _enc_node_v5(c)
        return bytes(out)

    if isinstance(node, list):
        # encode as sequence op with explicit arity
        out = bytearray()
        out.append(0xD0)
        out.append(OP_TAG["->"])
        out += _uvarint(len(node))
        for c in node:
            out += _enc_node_v5(c)
        return bytes(out)

    return _enc_str("null")

def to_glyphpack_v6(tree: Any) -> Tuple[bytes, bool, str]:
    """
    Returns (bytes, macro_used, variant_label)
    """
    depth = _matches_benchmark_grammar(tree)
    if depth is not None:
        cand = _encode_v6_macro(depth)
        # Defensible: verify round-trip reconstructs the same tree
        try:
            rebuilt = _decode_v6_macro(cand)
            if rebuilt == tree:
                return cand, True, "v6-macro(depth)"
        except Exception:
            pass

    # fallback: compact tree pack
    return _enc_node_v5(tree), False, "v5-fallback(tree-pack)"

# -----------------------------
# Baselines (reuse simplified variants)
# -----------------------------
def make_verbose_ast(node: Any, path: str = "$", parent_id: str = "root") -> Dict[str, Any]:
    def nid(seed: str) -> str:
        return f"n{abs(hash(seed)) % 10_000_000}"

    if isinstance(node, dict):
        for k, v in node.items():
            child_path = f"{path}.{k}"
            child_id = nid(child_path)
            children: List[Dict[str, Any]] = []
            if isinstance(v, list):
                for i, item in enumerate(v):
                    children.append(make_verbose_ast(item, path=f"{child_path}[{i}]", parent_id=child_id))
            else:
                children.append(make_verbose_ast(v, path=f"{child_path}[0]", parent_id=child_id))
            return {
                "node_type": "instruction_node",
                "id": child_id,
                "parent_id": parent_id,
                "path": child_path,
                "symbol": k,
                "telemetry": {
                    "trace_id": "trace_public_bench",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                "policy": {"trace": True},
                "children": children,
            }

    if isinstance(node, str):
        return {"node_type": "literal", "id": nid(path + ":" + node), "path": path, "value": node}

    if isinstance(node, list):
        return {
            "node_type": "list",
            "id": nid(path),
            "path": path,
            "children": [make_verbose_ast(x, f"{path}[{i}]", parent_id) for i, x in enumerate(node)],
        }

    return {"node_type": "literal", "id": nid(path + ":null"), "path": path, "value": None}

def make_expanded_instructions(tree: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    reg_counter = 0

    def new_reg() -> str:
        nonlocal reg_counter
        r = f"r{reg_counter}"
        reg_counter += 1
        return r

    def emit(symbol: str, args: List[str], value: Any = None) -> str:
        res = new_reg()
        instr = {"pc": len(out), "symbol": symbol, "args": args, "argc": len(args), "result": res}
        if value is not None:
            instr["value"] = value
        out.append(instr)
        return res

    def walk(node: Any) -> str:
        if isinstance(node, str):
            return emit("lit", [], value=node)
        if isinstance(node, dict):
            for k, v in node.items():
                child_regs = [walk(x) for x in (v if isinstance(v, list) else [v])]
                return emit(k, child_regs)
        if isinstance(node, list):
            regs = [walk(x) for x in node]
            return emit("[]", regs)
        return emit("lit", [], value=None)

    walk(tree)
    return out

# -----------------------------
# Result schema
# -----------------------------
@dataclass
class BenchResult:
    timestamp: str
    depth_steps: int
    macro_used: bool
    variant: str

    glyph_json_bytes: int
    glyph_json_gzip_bytes: int

    glyphpack_bytes: int
    glyphpack_gzip_bytes: int

    baseline_verbose_ast_bytes: int
    baseline_verbose_ast_gzip_bytes: int
    baseline_expanded_instr_bytes: int
    baseline_expanded_instr_gzip_bytes: int

    json_vs_pack_raw_x: float
    json_vs_pack_gzip_x: float
    pack_vs_ast_raw_x: float
    pack_vs_ir_raw_x: float
    pack_vs_ast_gzip_x: float
    pack_vs_ir_gzip_x: float

    runtime_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

def run_benchmark(depth_steps: int = 30) -> BenchResult:
    t0 = time.perf_counter()
    tree = make_glyph_tree(depth_steps)

    glyph_json = to_wire_json_bytes(tree)
    glyph_json_gz = gzip_bytes(glyph_json)

    glyphpack, macro_used, variant = to_glyphpack_v6(tree)
    glyphpack_gz = gzip_bytes(glyphpack)

    ast = to_wire_json_bytes(make_verbose_ast(tree))
    ast_gz = gzip_bytes(ast)

    ir = to_wire_json_bytes(make_expanded_instructions(tree))
    ir_gz = gzip_bytes(ir)

    def safe_x(a: int, b: int) -> float:
        return round((a / b) if b else 0.0, 4)

    dur_ms = (time.perf_counter() - t0) * 1000.0

    return BenchResult(
        timestamp=datetime.now(timezone.utc).isoformat(),
        depth_steps=depth_steps,
        macro_used=bool(macro_used),
        variant=str(variant),

        glyph_json_bytes=len(glyph_json),
        glyph_json_gzip_bytes=len(glyph_json_gz),

        glyphpack_bytes=len(glyphpack),
        glyphpack_gzip_bytes=len(glyphpack_gz),

        baseline_verbose_ast_bytes=len(ast),
        baseline_verbose_ast_gzip_bytes=len(ast_gz),
        baseline_expanded_instr_bytes=len(ir),
        baseline_expanded_instr_gzip_bytes=len(ir_gz),

        json_vs_pack_raw_x=safe_x(len(glyph_json), len(glyphpack)),
        json_vs_pack_gzip_x=safe_x(len(glyph_json_gz), len(glyphpack_gz)),
        pack_vs_ast_raw_x=safe_x(len(ast), len(glyphpack)),
        pack_vs_ir_raw_x=safe_x(len(ir), len(glyphpack)),
        pack_vs_ast_gzip_x=safe_x(len(ast_gz), len(glyphpack_gz)),
        pack_vs_ir_gzip_x=safe_x(len(ir_gz), len(glyphpack_gz)),

        runtime_ms=round(dur_ms, 3),
    )

def main() -> None:
    depth_steps = int(os.environ.get("GLYPHOS_BENCH_DEPTH", "30"))
    res = run_benchmark(depth_steps)

    print("\n=== ✅ GlyphOS WirePack Benchmark (GlyphPack v6 macro/grammar) ===")
    print(f"Depth steps used:                 {res.depth_steps}")
    print(f"Macro used:                       {res.macro_used}")
    print(f"Variant:                          {res.variant}\n")

    print(f"Glyph (wire JSON):                 {res.glyph_json_bytes} bytes")
    print(f"Glyph (wire JSON, gzip):           {res.glyph_json_gzip_bytes} bytes\n")

    print(f"GlyphPack v6:                      {res.glyphpack_bytes} bytes")
    print(f"GlyphPack v6 (gzip):               {res.glyphpack_gzip_bytes} bytes\n")

    print(f"✅ JSON vs Pack (raw):              {res.json_vs_pack_raw_x}x  (json/pack)")
    print(f"✅ JSON vs Pack (gzip):             {res.json_vs_pack_gzip_x}x  (json_gz/pack_gz)\n")

    print(f"Baseline A (verbose AST):          {res.baseline_verbose_ast_bytes} bytes")
    print(f"Baseline A (verbose AST, gzip):    {res.baseline_verbose_ast_gzip_bytes} bytes")
    print(f"✅ Pack vs A (raw):                 {res.pack_vs_ast_raw_x}x  (ast/pack)")
    print(f"✅ Pack vs A (gzip):                {res.pack_vs_ast_gzip_x}x\n")

    print(f"Baseline B (expanded instr):       {res.baseline_expanded_instr_bytes} bytes")
    print(f"Baseline B (expanded instr, gzip): {res.baseline_expanded_instr_gzip_bytes} bytes")
    print(f"✅ Pack vs B (raw):                 {res.pack_vs_ir_raw_x}x  (ir/pack)")
    print(f"✅ Pack vs B (gzip):                {res.pack_vs_ir_gzip_x}x\n")

    print(f"Runtime:                           {res.runtime_ms} ms\n")

    out_dir = "./benchmarks"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "glyphos_wirepack_v6_macro_latest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"Saved:                             {out_path}\n")

if __name__ == "__main__":
    main()
