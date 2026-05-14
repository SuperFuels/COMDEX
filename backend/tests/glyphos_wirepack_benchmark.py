# 📁 backend/tests/glyphos_wirepack_benchmark.py
from __future__ import annotations

import gzip
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Keep identical OPS set to stay comparable
OPS = {"↔", "⊕", "⟲", "->", "⧖"}
OP_TAG = {"↔": 1, "⊕": 2, "⟲": 3, "->": 4, "⧖": 5}

# -----------------------------
# Reuse your generator verbatim
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
# Existing JSON helpers
# -----------------------------
def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

# -----------------------------
# GlyphPack v1.1: compact binary encoding (lossless)
# -----------------------------
# Tags (single byte)
TAG_TABLE     = 0xF0  # string table header
TAG_OPNODE    = 0xD0  # op-node: [TAG_OPNODE][op_tag][arity(varint)]{child}...
TAG_STR_RAW   = 0xA0  # raw string: [TAG_STR_RAW][len(varint)][utf8...]
TAG_STR_REF   = 0xA1  # string table ref: [TAG_STR_REF][idx(varint)]
TAG_L_LABEL   = 0xB0  # L{i}_k pattern: [TAG_L_LABEL][i(varint)][k(varint)]
TAG_SYM_LABEL = 0xB1  # {A..Z}{n} pattern: [TAG_SYM_LABEL][letter_id(varint)][n(varint)]
TAG_NULL      = 0xC0  # null sentinel (rare)

# Pattern encoders for dramatic improvement (still reversible)
_RE_L = re.compile(r"^L(\d+)_(\d+)$")
_RE_SYM = re.compile(r"^([A-Z])(\d+)$")

def _varint(n: int) -> bytes:
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

def _collect_strings(node: Any, out: Dict[str, int]) -> None:
    """
    Collect strings that are NOT covered by typed encodings (L-label or Sym-label),
    so the optional string table is only used when needed.
    """
    if isinstance(node, str):
        if _RE_L.match(node) or _RE_SYM.match(node) or node == "null":
            return
        out.setdefault(node, 0)
        return
    if isinstance(node, list):
        for x in node:
            _collect_strings(x, out)
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, list):
                for x in v:
                    _collect_strings(x, out)
            else:
                _collect_strings(v, out)

def _encode_string(s: str, table_index: Optional[Dict[str, int]]) -> bytes:
    """
    Lossless, typed string encoding:
      - L{i}_k -> TAG_L_LABEL + varint(i) + varint(k)
      - {A..Z}{n} -> TAG_SYM_LABEL + varint(letter_id) + varint(n)
      - "null" -> TAG_NULL
      - else -> string-table ref (if present) else raw utf-8
    """
    if s == "null":
        return bytes([TAG_NULL])

    m = _RE_L.match(s)
    if m:
        i = int(m.group(1))
        k = int(m.group(2))
        return bytes([TAG_L_LABEL]) + _varint(i) + _varint(k)

    m2 = _RE_SYM.match(s)
    if m2:
        letter = m2.group(1)
        n = int(m2.group(2))
        letter_id = ord(letter) - ord("A")  # 0..25
        return bytes([TAG_SYM_LABEL]) + _varint(letter_id) + _varint(n)

    if table_index is not None and s in table_index:
        return bytes([TAG_STR_REF]) + _varint(table_index[s])

    b = s.encode("utf-8")
    return bytes([TAG_STR_RAW]) + _varint(len(b)) + b

def _encode_node(node: Any, table_index: Optional[Dict[str, int]]) -> bytes:
    if isinstance(node, str):
        return _encode_string(node, table_index)

    if isinstance(node, dict):
        # Single-key op nodes in this benchmark.
        for op, v in node.items():
            tag = OP_TAG.get(op, 0)
            if tag == 0:
                raise ValueError(f"unknown op: {op}")
            children = v if isinstance(v, list) else [v]

            out = bytearray()
            out.append(TAG_OPNODE)
            out.append(tag)
            out += _varint(len(children))
            for ch in children:
                out += _encode_node(ch, table_index)
            return bytes(out)

    if isinstance(node, list):
        # Should not occur as a standalone node in this generator,
        # but we support it by encoding a synthetic "sequence" op.
        out = bytearray()
        out.append(TAG_OPNODE)
        out.append(OP_TAG["->"])
        out += _varint(len(node))
        for ch in node:
            out += _encode_node(ch, table_index)
        return bytes(out)

    # null/other
    return bytes([TAG_NULL])

def to_glyphpack_v1_1(tree: Any, build_string_table: bool = False) -> bytes:
    """
    build_string_table defaults to False because typed encodings already cover
    all strings in this benchmark generator (L*, A/B/Z*).
    Turn it on if you introduce arbitrary strings in future benchmarks.
    """
    table_index: Optional[Dict[str, int]] = None
    header = b""

    if build_string_table:
        strings: Dict[str, int] = {}
        _collect_strings(tree, strings)

        uniq = sorted(strings.keys(), key=lambda x: (len(x), x))
        table_index = {s: i for i, s in enumerate(uniq)}

        h = bytearray()
        h.append(TAG_TABLE)
        h += _varint(len(uniq))
        for s in uniq:
            sb = s.encode("utf-8")
            h += _varint(len(sb))
            h += sb
        header = bytes(h)

    payload = _encode_node(tree, table_index)
    return header + payload

# -----------------------------
# Baselines (reuse simplified variants)
# -----------------------------
def make_verbose_ast(node: Any, path: str = "$", parent_id: str = "root") -> Dict[str, Any]:
    # Heavy-ish baseline semantics (kept minimal but metadata-bearing)
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

    # v1.1 uses typed labels; string-table off by default (not needed for this generator)
    build_table = os.environ.get("GLYPHOS_PACK_TABLE", "0") == "1"
    glyphpack = to_glyphpack_v1_1(tree, build_string_table=build_table)
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

    print("\n=== ✅ GlyphOS WirePack Benchmark (JSON vs GlyphPack v1.1) ===")
    print(f"Depth steps used:                 {res.depth_steps}")
    print(f"String table enabled:             {os.environ.get('GLYPHOS_PACK_TABLE','0') == '1'}\n")

    print(f"Glyph (wire JSON):                 {res.glyph_json_bytes} bytes")
    print(f"Glyph (wire JSON, gzip):           {res.glyph_json_gzip_bytes} bytes\n")

    print(f"GlyphPack v1.1 (binary):           {res.glyphpack_bytes} bytes")
    print(f"GlyphPack v1.1 (binary, gzip):     {res.glyphpack_gzip_bytes} bytes\n")

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

    print(f"Runtime:                           {res.runtime_ms} ms")

    out_dir = "./benchmarks"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "glyphos_wirepack_latest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"Saved:                             {out_path}\n")

if __name__ == "__main__":
    main()
