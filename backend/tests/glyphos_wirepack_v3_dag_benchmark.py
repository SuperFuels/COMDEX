from __future__ import annotations

import gzip
import json
import os
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

OPS = {"↔", "⊕", "⟲", "->", "⧖"}
OP_TAG = {"↔": 1, "⊕": 2, "⟲": 3, "->": 4, "⧖": 5}

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
# Typed string encoding (tight)
# -----------------------------
def _enc_str(s: str) -> bytes:
    # tags:
    # 0x00: L{i}_{k} => varint(i), varint(k)
    # 0x01: {Letter}{n} => byte(letter_id), varint(n)
    # 0x02: raw utf8 => varint(len), bytes
    # 0x03: null literal
    if s == "null":
        return bytes([0x03])

    if len(s) >= 3 and s[0] == "L" and "_" in s:
        try:
            i_str, k_str = s[1:].split("_", 1)
            i = int(i_str)
            k = int(k_str)
            return bytes([0x00]) + _varint(i) + _varint(k)
        except Exception:
            pass

    if len(s) >= 2 and "A" <= s[0] <= "Z":
        # A1, Z12 etc.
        try:
            letter_id = ord(s[0]) - ord("A")
            n = int(s[1:])
            return bytes([0x01, letter_id]) + _varint(n)
        except Exception:
            pass

    b = s.encode("utf-8")
    return bytes([0x02]) + _varint(len(b)) + b

# -----------------------------
# Canonical hash for subtree dedup
# -----------------------------
def _hash_node(node: Any) -> bytes:
    h = hashlib.blake2s(digest_size=16)
    def walk(n: Any):
        if isinstance(n, str):
            h.update(b"S")
            h.update(_enc_str(n))
            return
        if isinstance(n, dict):
            # single-key in this benchmark
            for op, v in n.items():
                h.update(b"O")
                h.update(bytes([OP_TAG.get(op, 0)]))
                children = v if isinstance(v, list) else [v]
                h.update(_varint(len(children)))
                for ch in children:
                    walk(ch)
                return
        if isinstance(n, list):
            h.update(b"L")
            h.update(_varint(len(n)))
            for ch in n:
                walk(ch)
            return
        h.update(b"N")
    walk(node)
    return h.digest()

# -----------------------------
# GlyphPack v3: DAG encoding (DEF/REF)
# -----------------------------
# File format:
#  "GP3" magic
#  varint(num_nodes)
#  varint(root_id)
#  Then for each node_id in [0..num_nodes-1], an entry:
#    [kind byte]
#      0x10 = LIT   then enc_str(...)
#      0x11 = OP    then op_tag(1 byte) + arity(varint) + child_id(varint)...
#
# The trick is: we deduplicate identical subtrees by hashing. This is where you can get real wins.

K_LIT = 0x10
K_OP  = 0x11

def to_glyphpack_v3_dag(tree: Any) -> bytes:
    # map hash->node_id
    hid_to_id: Dict[bytes, int] = {}
    nodes: List[Any] = []

    def intern(n: Any) -> int:
        hid = _hash_node(n)
        if hid in hid_to_id:
            return hid_to_id[hid]
        node_id = len(nodes)
        hid_to_id[hid] = node_id
        nodes.append(n)
        # ensure children are interned too (postorder-ish)
        if isinstance(n, dict):
            for op, v in n.items():
                children = v if isinstance(v, list) else [v]
                for ch in children:
                    intern(ch)
        elif isinstance(n, list):
            for ch in n:
                intern(ch)
        return node_id

    root_id = intern(tree)

    out = bytearray()
    out += b"GP3"
    out += _varint(len(nodes))
    out += _varint(root_id)

    # Emit nodes in id order (stable)
    for n in nodes:
        if isinstance(n, str):
            out.append(K_LIT)
            out += _enc_str(n)
            continue

        if isinstance(n, dict):
            for op, v in n.items():
                tag = OP_TAG.get(op, 0)
                if tag == 0:
                    raise ValueError(f"unknown op: {op}")
                children = v if isinstance(v, list) else [v]
                out.append(K_OP)
                out.append(tag)
                out += _varint(len(children))
                for ch in children:
                    out += _varint(intern(ch))
                break
            continue

        if isinstance(n, list):
            out.append(K_OP)
            out.append(OP_TAG["->"])
            out += _varint(len(n))
            for ch in n:
                out += _varint(intern(ch))
            continue

        out.append(K_LIT)
        out += _enc_str("null")

    return bytes(out)

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
    glyphpack_v3_bytes: int
    glyphpack_v3_gzip_bytes: int
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
    nodes_deduped: int

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

def run_benchmark(depth_steps: int = 30) -> BenchResult:
    t0 = time.perf_counter()
    tree = make_glyph_tree(depth_steps)

    j = to_wire_json_bytes(tree)
    jgz = gzip_bytes(j)

    p = to_glyphpack_v3_dag(tree)
    pgz = gzip_bytes(p)

    ast = to_wire_json_bytes(make_verbose_ast(tree))
    astgz = gzip_bytes(ast)

    ir = to_wire_json_bytes(make_expanded_instructions(tree))
    irgz = gzip_bytes(ir)

    def sx(a: int, b: int) -> float:
        return round((a / b) if b else 0.0, 4)

    dur_ms = (time.perf_counter() - t0) * 1000.0

    # quick parse: num_nodes is varint right after "GP3"
    # (best-effort, for display only)
    nodes_count = 0
    i = 3
    shift = 0
    while i < len(p):
        b = p[i]
        nodes_count |= (b & 0x7F) << shift
        i += 1
        if not (b & 0x80):
            break
        shift += 7

    return BenchResult(
        timestamp=datetime.now(timezone.utc).isoformat(),
        depth_steps=depth_steps,
        glyph_json_bytes=len(j),
        glyph_json_gzip_bytes=len(jgz),
        glyphpack_v3_bytes=len(p),
        glyphpack_v3_gzip_bytes=len(pgz),
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
        nodes_deduped=nodes_count,
    )

def main() -> None:
    depth_steps = int(os.environ.get("GLYPHOS_BENCH_DEPTH", "30"))
    res = run_benchmark(depth_steps)

    print("\n=== ✅ GlyphOS WirePack Benchmark (GlyphPack v3 DAG) ===")
    print(f"Depth steps used:                 {res.depth_steps}")
    print(f"DAG node count (deduped):         {res.nodes_deduped}\n")

    print(f"Glyph (wire JSON):                 {res.glyph_json_bytes} bytes")
    print(f"Glyph (wire JSON, gzip):           {res.glyph_json_gzip_bytes} bytes\n")

    print(f"GlyphPack v3 (DAG):                {res.glyphpack_v3_bytes} bytes")
    print(f"GlyphPack v3 (DAG, gzip):          {res.glyphpack_v3_gzip_bytes} bytes\n")

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
    out_path = "./benchmarks/glyphos_wirepack_v3_dag_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"Saved:                             {out_path}\n")

if __name__ == "__main__":
    main()
