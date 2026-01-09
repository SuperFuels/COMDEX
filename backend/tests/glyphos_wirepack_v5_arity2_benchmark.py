from __future__ import annotations

import gzip
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

OPS = {"↔", "⊕", "⟲", "->", "⧖"}
OP_TAG = {"↔": 1, "⊕": 2, "⟲": 3, "->": 4, "⧖": 5}
TAG_OP_TO_SYM = {v: k for k, v in OP_TAG.items()}

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

# -----------------------------
# JSON helpers
# -----------------------------
def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

# -----------------------------
# Varint encode/decode
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

def _read_varint(buf: bytes, i: int) -> Tuple[int, int]:
    shift = 0
    val = 0
    while True:
        if i >= len(buf):
            raise ValueError("truncated varint")
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return val, i
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")

# -----------------------------
# GlyphPack v5: arity=2 elision + typed literals
# -----------------------------
# Byte layout:
#   OP arity=2 (common):  [0b1000TTTT]   where TTTT = op_tag (1..15)
#   OP arity!=2:          [0b1100TTTT][arity varint] then children...
#
#   LIT L{i}_{k}:         [0xA0][i varint][k varint]
#   LIT {Letter}{n}:      [0xA1][letter_id 1B][n varint]
#   LIT null:             [0xA2]
#   LIT utf8 fallback:    [0xA3][len varint][bytes]
#
OP2_BASE = 0x80  # 1000....
OPX_BASE = 0xC0  # 1100....

def _enc_lit(s: str) -> bytes:
    if s == "null":
        return bytes([0xA2])

    # L{i}_{k}
    if len(s) >= 4 and s[0] == "L" and "_" in s:
        try:
            i_str, k_str = s[1:].split("_", 1)
            ii = int(i_str)
            kk = int(k_str)
            if ii >= 0 and kk >= 0:
                return bytes([0xA0]) + _varint(ii) + _varint(kk)
        except Exception:
            pass

    # A1 / B2 / Z4 etc.
    if len(s) >= 2 and "A" <= s[0] <= "Z":
        try:
            letter_id = ord(s[0]) - ord("A")  # 0..25
            n = int(s[1:])
            if 0 <= letter_id <= 25 and n >= 0:
                return bytes([0xA1, letter_id]) + _varint(n)
        except Exception:
            pass

    b = s.encode("utf-8")
    return bytes([0xA3]) + _varint(len(b)) + b

def _enc_node(node: Any) -> bytes:
    if isinstance(node, str):
        return _enc_lit(node)

    if isinstance(node, dict):
        for op, v in node.items():
            tag = OP_TAG.get(op, 0)
            if tag == 0:
                raise ValueError(f"unknown op: {op}")
            children = v if isinstance(v, list) else [v]
            out = bytearray()

            if len(children) == 2:
                out.append(OP2_BASE | (tag & 0x0F))
            else:
                out.append(OPX_BASE | (tag & 0x0F))
                out += _varint(len(children))

            for ch in children:
                out += _enc_node(ch)
            return bytes(out)

    if isinstance(node, list):
        # encode list as sequence op
        children = node
        out = bytearray()
        tag = OP_TAG["->"]
        if len(children) == 2:
            out.append(OP2_BASE | (tag & 0x0F))
        else:
            out.append(OPX_BASE | (tag & 0x0F))
            out += _varint(len(children))
        for ch in children:
            out += _enc_node(ch)
        return bytes(out)

    return _enc_lit("null")

def to_glyphpack_v5(tree: Any) -> bytes:
    return b"GP5" + _enc_node(tree)

# -----------------------------
# Decoder (defensible roundtrip)
# -----------------------------
def _dec_lit(buf: bytes, i: int) -> Tuple[str, int]:
    if i >= len(buf):
        raise ValueError("truncated lit")
    t = buf[i]
    i += 1

    if t == 0xA2:
        return "null", i

    if t == 0xA0:
        ii, i = _read_varint(buf, i)
        kk, i = _read_varint(buf, i)
        return f"L{ii}_{kk}", i

    if t == 0xA1:
        if i >= len(buf):
            raise ValueError("truncated A1 lit")
        letter_id = buf[i]
        i += 1
        n, i = _read_varint(buf, i)
        return f"{chr(ord('A') + letter_id)}{n}", i

    if t == 0xA3:
        ln, i = _read_varint(buf, i)
        if i + ln > len(buf):
            raise ValueError("truncated utf8 lit")
        s = buf[i:i+ln].decode("utf-8")
        return s, i + ln

    raise ValueError(f"unknown lit tag: {hex(t)}")

def _dec_node(buf: bytes, i: int) -> Tuple[Any, int]:
    if i >= len(buf):
        raise ValueError("truncated node")
    b0 = buf[i]
    i += 1

    # OP arity=2
    if (b0 & 0xF0) == OP2_BASE:
        tag = b0 & 0x0F
        op = TAG_OP_TO_SYM.get(tag)
        if not op:
            raise ValueError(f"bad op tag: {tag}")
        c1, i = _dec_node(buf, i)
        c2, i = _dec_node(buf, i)
        return {op: [c1, c2]}, i

    # OP arity!=2
    if (b0 & 0xF0) == OPX_BASE:
        tag = b0 & 0x0F
        op = TAG_OP_TO_SYM.get(tag)
        if not op:
            raise ValueError(f"bad op tag: {tag}")
        ar, i = _read_varint(buf, i)
        children = []
        for _ in range(ar):
            ch, i = _dec_node(buf, i)
            children.append(ch)
        return {op: children}, i

    # Otherwise: treat as literal tag byte (we already consumed it)
    # Rewind one byte and decode as lit
    return _dec_lit(buf, i - 1)

def decode_glyphpack_v5(p: bytes) -> Any:
    if not p.startswith(b"GP5"):
        raise ValueError("bad magic")
    tree, idx = _dec_node(p, 3)
    if idx != len(p):
        raise ValueError("trailing bytes")
    return tree

# -----------------------------
# Baselines (light)
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

    pack_bytes: int
    pack_gzip_bytes: int

    ast_bytes: int
    ast_gzip_bytes: int
    ir_bytes: int
    ir_gzip_bytes: int

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

    p = to_glyphpack_v5(tree)
    # defensible: roundtrip check
    rt = decode_glyphpack_v5(p)
    assert rt == tree, "GlyphPack v5 roundtrip mismatch"

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

        pack_bytes=len(p),
        pack_gzip_bytes=len(pgz),

        ast_bytes=len(ast),
        ast_gzip_bytes=len(astgz),
        ir_bytes=len(ir),
        ir_gzip_bytes=len(irgz),

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

    print("\n=== ✅ GlyphOS WirePack Benchmark (GlyphPack v5 arity=2 elision) ===")
    print(f"Depth steps used:                 {res.depth_steps}\n")

    print(f"Glyph (wire JSON):                 {res.glyph_json_bytes} bytes")
    print(f"Glyph (wire JSON, gzip):           {res.glyph_json_gzip_bytes} bytes\n")

    print(f"GlyphPack v5 (arity2-elided):       {res.pack_bytes} bytes")
    print(f"GlyphPack v5 (arity2-elided, gzip): {res.pack_gzip_bytes} bytes\n")

    print(f"✅ JSON vs Pack (raw):              {res.json_vs_pack_raw_x}x  (json/pack)")
    print(f"✅ JSON vs Pack (gzip):             {res.json_vs_pack_gzip_x}x  (json_gz/pack_gz)\n")

    print(f"Baseline A (verbose AST):          {res.ast_bytes} bytes")
    print(f"Baseline A (verbose AST, gzip):    {res.ast_gzip_bytes} bytes")
    print(f"✅ Pack vs A (raw):                 {res.pack_vs_ast_raw_x}x  (ast/pack)")
    print(f"✅ Pack vs A (gzip):                {res.pack_vs_ast_gzip_x}x\n")

    print(f"Baseline B (expanded instr):       {res.ir_bytes} bytes")
    print(f"Baseline B (expanded instr, gzip): {res.ir_gzip_bytes} bytes")
    print(f"✅ Pack vs B (raw):                 {res.pack_vs_ir_raw_x}x  (ir/pack)")
    print(f"✅ Pack vs B (gzip):                {res.pack_vs_ir_gzip_x}x\n")

    print(f"Runtime:                           {res.runtime_ms} ms\n")

    os.makedirs("./benchmarks", exist_ok=True)
    out_path = "./benchmarks/glyphos_wirepack_v5_arity2_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"Saved:                             {out_path}\n")

if __name__ == "__main__":
    main()
