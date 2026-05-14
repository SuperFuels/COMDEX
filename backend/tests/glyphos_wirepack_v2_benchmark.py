from __future__ import annotations

import gzip
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

OPS = {"↔", "⊕", "⟲", "->", "⧖"}

# 3-bit opcodes (0..7)
OP3 = {"↔": 0, "⊕": 1, "⟲": 2, "->": 3, "⧖": 4}

# -----------------------------
# Same generator
# -----------------------------
def make_glyph_tree(depth_steps: int = 30) -> Dict[str, Any]:
    branch1 = {"⊕": [{"⊕": ["A1", "B1"]}, {"⟲": ["A2", "B2"]}]}
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

def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

# -----------------------------
# Varint
# -----------------------------
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

# -----------------------------
# Typed string coding (same idea, but even tighter tags)
# -----------------------------
TAG_L = 0x00  # L{i}_k
TAG_SYM = 0x01  # {A..Z}{n}
TAG_UTF8 = 0x02  # raw utf8
TAG_NULL = 0x03  # null

_RE_L = re.compile(r"^L(\d+)_(\d+)$")
_RE_SYM = re.compile(r"^([A-Z])(\d+)$")

def _enc_str(s: str) -> bytes:
    if s == "null":
        return bytes([TAG_NULL])

    m = _RE_L.match(s)
    if m:
        i = int(m.group(1))
        k = int(m.group(2))
        return bytes([TAG_L]) + _varint(i) + _varint(k)

    m2 = _RE_SYM.match(s)
    if m2:
        letter_id = ord(m2.group(1)) - ord("A")
        n = int(m2.group(2))
        return bytes([TAG_SYM]) + _varint(letter_id) + _varint(n)

    b = s.encode("utf-8")
    return bytes([TAG_UTF8]) + _varint(len(b)) + b

# -----------------------------
# Pack v2: bytecode stream
# -----------------------------
# We encode the tree as a pre-order stream of "tokens".
#
# Token format (1 byte):
#   bits 0..2 : opcode (0..7)
#   bits 3..3 : arity_flag (0 => arity=2 implicit, 1 => explicit arity varint follows)
#   bits 4..7 : reserved (0)
#
# After token:
#   - if explicit arity: write varint(arity)
#   - then children recursively
#
# Leaves (strings) are not opnodes: they use a special escape opcode=7 with arity_flag=1 and arity=0,
# followed by typed string encoding. (Keeps token stream byte-aligned & simple.)
#
OP_ESCAPE = 7

def _enc_node(node: Any, out: bytearray) -> None:
    if isinstance(node, str):
        # escape token, explicit arity=0, then typed string
        out.append((OP_ESCAPE & 0x07) | (1 << 3))
        out += _varint(0)
        out += _enc_str(node)
        return

    if isinstance(node, dict):
        for op, v in node.items():
            code = OP3.get(op, None)
            if code is None:
                raise ValueError(f"unknown op: {op}")
            children = v if isinstance(v, list) else [v]
            ar = len(children)
            if ar == 2:
                out.append(code & 0x07)  # implicit arity=2
            else:
                out.append((code & 0x07) | (1 << 3))
                out += _varint(ar)
            for ch in children:
                _enc_node(ch, out)
            return

    if isinstance(node, list):
        # treat as sequence op
        code = OP3["->"]
        ar = len(node)
        if ar == 2:
            out.append(code & 0x07)
        else:
            out.append((code & 0x07) | (1 << 3))
            out += _varint(ar)
        for ch in node:
            _enc_node(ch, out)
        return

    # null/other
    _enc_node("null", out)

def to_glyphpack_v2(tree: Any) -> bytes:
    out = bytearray()
    # header magic + version
    out += b"GP"
    out.append(2)
    _enc_node(tree, out)
    return bytes(out)

# -----------------------------
# Baselines (reuse from v1.1 style)
# -----------------------------
def make_verbose_ast(node: Any, path: str = "$") -> Dict[str, Any]:
    if isinstance(node, dict):
        for k, v in node.items():
            children = [make_verbose_ast(x, f"{path}.{k}[{i}]") for i, x in enumerate(v if isinstance(v, list) else [v])]
            return {
                "node_type": "instruction_node",
                "path": f"{path}.{k}",
                "symbol": k,
                "telemetry": {"trace": True, "created_at": datetime.now(timezone.utc).isoformat()},
                "children": children,
            }
    if isinstance(node, str):
        return {"node_type": "literal", "path": path, "value": node}
    if isinstance(node, list):
        return {"node_type": "list", "path": path, "children": [make_verbose_ast(x, f"{path}[{i}]") for i, x in enumerate(node)]}
    return {"node_type": "literal", "path": path, "value": None}

def make_expanded_instructions(tree: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    def emit(sym: str, args: List[int], value: Any = None) -> int:
        pc = len(out)
        instr = {"pc": pc, "symbol": sym, "args": args, "argc": len(args)}
        if value is not None:
            instr["value"] = value
        out.append(instr)
        return pc

    def walk(n: Any) -> int:
        if isinstance(n, str):
            return emit("lit", [], value=n)
        if isinstance(n, dict):
            for k, v in n.items():
                regs = [walk(x) for x in (v if isinstance(v, list) else [v])]
                return emit(k, regs)
        if isinstance(n, list):
            regs = [walk(x) for x in n]
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
    glyphpack_v2_bytes: int
    glyphpack_v2_gzip_bytes: int
    baseline_ast_bytes: int
    baseline_ast_gzip_bytes: int
    baseline_ir_bytes: int
    baseline_ir_gzip_bytes: int
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

    j = to_wire_json_bytes(tree)
    jgz = gzip_bytes(j)

    p = to_glyphpack_v2(tree)
    pgz = gzip_bytes(p)

    ast = to_wire_json_bytes(make_verbose_ast(tree))
    astgz = gzip_bytes(ast)

    ir = to_wire_json_bytes(make_expanded_instructions(tree))
    irgz = gzip_bytes(ir)

    def sx(a: int, b: int) -> float:
        return round((a / b) if b else 0.0, 4)

    dur_ms = (time.perf_counter() - t0) * 1000.0

    return BenchResult(
        timestamp=datetime.now(timezone.utc).isoformat(),
        depth_steps=depth_steps,
        glyph_json_bytes=len(j),
        glyph_json_gzip_bytes=len(jgz),
        glyphpack_v2_bytes=len(p),
        glyphpack_v2_gzip_bytes=len(pgz),
        baseline_ast_bytes=len(ast),
        baseline_ast_gzip_bytes=len(astgz),
        baseline_ir_bytes=len(ir),
        baseline_ir_gzip_bytes=len(irgz),
        json_vs_pack_raw_x=sx(len(j), len(p)),
        json_vs_pack_gzip_x=sx(len(jgz), len(pgz)),
        pack_vs_ast_raw_x=sx(len(ast), len(p)),
        pack_vs_ir_raw_x=sx(len(ir), len(p)),
        pack_vs_ast_gzip_x=sx(len(astgz), len(pgz)),
        pack_vs_ir_gzip_x=sx(len(irgz), len(pgz)),
        runtime_ms=round(dur_ms, 3),
    )

def main() -> None:
    depth_steps = int(os.environ.get("GLYPHOS_BENCH_DEPTH", "30"))
    res = run_benchmark(depth_steps)

    print("\n=== ✅ GlyphOS WirePack Benchmark (GlyphPack v2 bytecode) ===")
    print(f"Depth steps used:                 {res.depth_steps}\n")

    print(f"Glyph (wire JSON):                 {res.glyph_json_bytes} bytes")
    print(f"Glyph (wire JSON, gzip):           {res.glyph_json_gzip_bytes} bytes\n")

    print(f"GlyphPack v2 (bytecode):           {res.glyphpack_v2_bytes} bytes")
    print(f"GlyphPack v2 (bytecode, gzip):     {res.glyphpack_v2_gzip_bytes} bytes\n")

    print(f"✅ JSON vs Pack (raw):              {res.json_vs_pack_raw_x}x  (json/pack)")
    print(f"✅ JSON vs Pack (gzip):             {res.json_vs_pack_gzip_x}x  (json_gz/pack_gz)\n")

    print(f"Baseline A (verbose AST):          {res.baseline_ast_bytes} bytes")
    print(f"Baseline A (verbose AST, gzip):    {res.baseline_ast_gzip_bytes} bytes")
    print(f"✅ Pack vs A (raw):                 {res.pack_vs_ast_raw_x}x  (ast/pack)")
    print(f"✅ Pack vs A (gzip):                {res.pack_vs_ast_gzip_x}x\n")

    print(f"Baseline B (expanded instr):       {res.baseline_ir_bytes} bytes")
    print(f"Baseline B (expanded instr, gzip): {res.baseline_ir_gzip_bytes} bytes")
    print(f"✅ Pack vs B (raw):                 {res.pack_vs_ir_raw_x}x  (ir/pack)")
    print(f"✅ Pack vs B (gzip):                {res.pack_vs_ir_gzip_x}x\n")

    print(f"Runtime:                           {res.runtime_ms} ms\n")

    os.makedirs("./benchmarks", exist_ok=True)
    out_path = "./benchmarks/glyphos_wirepack_v2_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"Saved:                             {out_path}\n")

if __name__ == "__main__":
    main()
