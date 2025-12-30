#!/usr/bin/env python3
"""
SRK-8 executable evidence runner (deterministic, no extra deps).

Writes:
  - docs/Artifacts/SRK8/ledger/SRK8_LINT_PROOF.log
  - docs/Artifacts/SRK8/ledger/SRK8_METRICS.json

Validates:
  - theorem_ledger.jsonl parses (JSON per line)
  - theorem_ledger_repaired.jsonl parses (JSON per line)
  - required SRK-8 artifact paths exist
  - computes AST_DEPTH_REDUCTION from SRK8_PIPELINE_FLOW.scene.json (⊕ binary tree depth)
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path("/workspaces/COMDEX")

# Canonical SRK-8 surface (prefer these)
SRK8_DIR = REPO / "docs/Artifacts/SRK8"
LEDGER_DIR = SRK8_DIR / "ledger"
QFC_SCENE = SRK8_DIR / "qfc" / "SRK8_PIPELINE_FLOW.scene.json"
ALT_SCENE = SRK8_DIR / "scenes" / "SRK8_PIPELINE_FLOW.scene.json"

LEDGER_CANON = LEDGER_DIR / "theorem_ledger.jsonl"
REPAIRED_CANON = LEDGER_DIR / "theorem_ledger_repaired.jsonl"

# Some repos have duplicates at SRK8 root; we will fall back if needed
LEDGER_FALLBACK = SRK8_DIR / "theorem_ledger.jsonl"
REPAIRED_FALLBACK = SRK8_DIR / "theorem_ledger_repaired.jsonl"

OUT_LOG = LEDGER_DIR / "SRK8_LINT_PROOF.log"
OUT_METRICS = LEDGER_DIR / "SRK8_METRICS.json"


# ────────────────────────────────────────────────────────────────
# Minimal expression parser for "(B ⊕ A) ⊕ C" and "A ⊕ (B ⊕ C)"
# Tokens: identifiers, '⊕', '(', ')'
# Grammar:
#   expr := term ( '⊕' term )*
#   term := IDENT | '(' expr ')'
# We compute depth as:
#   depth(IDENT) = 1
#   depth(OP(left,right)) = 1 + max(depth(left), depth(right))
# ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Node:
    kind: str  # 'id' or 'op'
    value: str
    left: Optional["Node"] = None
    right: Optional["Node"] = None

def tokenize(expr: str) -> List[str]:
    expr = expr.replace("⊕", " ⊕ ").replace("(", " ( ").replace(")", " ) ")
    toks = [t for t in expr.split() if t]
    return toks

def parse_expr(tokens: List[str]) -> Tuple[Node, List[str]]:
    node, tokens = parse_term(tokens)
    while tokens and tokens[0] == "⊕":
        tokens = tokens[1:]  # consume ⊕
        rhs, tokens = parse_term(tokens)
        node = Node(kind="op", value="⊕", left=node, right=rhs)
    return node, tokens

def parse_term(tokens: List[str]) -> Tuple[Node, List[str]]:
    if not tokens:
        raise ValueError("unexpected end of tokens")
    t = tokens[0]
    if t == "(":
        node, rest = parse_expr(tokens[1:])
        if not rest or rest[0] != ")":
            raise ValueError("missing closing ')'")
        return node, rest[1:]
    if t in (")", "⊕"):
        raise ValueError(f"unexpected token: {t}")
    # identifier
    return Node(kind="id", value=t), tokens[1:]

def ast_depth(node: Node) -> int:
    if node.kind == "id":
        return 1
    if node.kind == "op":
        assert node.left is not None and node.right is not None
        return 1 + max(ast_depth(node.left), ast_depth(node.right))
    raise ValueError(f"unknown node kind: {node.kind}")


# ────────────────────────────────────────────────────────────────
# JSONL lint + hashing
# ────────────────────────────────────────────────────────────────

@dataclass
class JsonlReport:
    path: Path
    exists: bool
    entries: int
    parse_errors: int
    first_error: Optional[str]
    file_sha256: Optional[str]
    nonempty_hash_fields: Optional[int]
    empty_hash_fields: Optional[int]

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def read_jsonl(path: Path) -> JsonlReport:
    if not path.exists():
        return JsonlReport(
            path=path,
            exists=False,
            entries=0,
            parse_errors=0,
            first_error=None,
            file_sha256=None,
            nonempty_hash_fields=None,
            empty_hash_fields=None,
        )

    raw = path.read_bytes()
    file_hash = sha256_bytes(raw)

    entries = 0
    parse_errors = 0
    first_error = None
    nonempty_hash_fields = 0
    empty_hash_fields = 0

    # tolerate blank lines and comment-ish lines starting with '#'
    for i, line in enumerate(raw.splitlines(), start=1):
        s = line.decode("utf-8", errors="replace").strip()
        if not s or s.startswith("#"):
            continue
        try:
            obj = json.loads(s)
            entries += 1
            # soft-check "hash" fields if present (common in ledgers)
            if isinstance(obj, dict) and "hash" in obj:
                hv = obj.get("hash")
                if hv is None or (isinstance(hv, str) and hv.strip() == ""):
                    empty_hash_fields += 1
                else:
                    nonempty_hash_fields += 1
        except Exception as e:
            parse_errors += 1
            if first_error is None:
                first_error = f"line {i}: {type(e).__name__}: {e}"

    return JsonlReport(
        path=path,
        exists=True,
        entries=entries,
        parse_errors=parse_errors,
        first_error=first_error,
        file_sha256=file_hash,
        nonempty_hash_fields=nonempty_hash_fields,
        empty_hash_fields=empty_hash_fields,
    )

def pick_existing(primary: Path, fallback: Path) -> Path:
    return primary if primary.exists() else fallback


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def load_scene() -> Dict[str, Any]:
    scene_path = QFC_SCENE if QFC_SCENE.exists() else ALT_SCENE
    if not scene_path.exists():
        raise FileNotFoundError(f"SRK-8 scene not found at {QFC_SCENE} or {ALT_SCENE}")
    return json.loads(scene_path.read_text(encoding="utf-8"))

def compute_scene_metric(scene: Dict[str, Any]) -> Dict[str, Any]:
    inp = scene.get("input_expression")
    out = scene.get("canonical_output")
    metric = scene.get("metric", {}) or {}
    metric_name = metric.get("name", "AST_DEPTH_REDUCTION")

    if not isinstance(inp, str) or not isinstance(out, str):
        raise ValueError("scene missing input_expression or canonical_output strings")

    n1, rest1 = parse_expr(tokenize(inp))
    if rest1:
        raise ValueError(f"unparsed tokens remaining in input_expression: {rest1}")

    n2, rest2 = parse_expr(tokenize(out))
    if rest2:
        raise ValueError(f"unparsed tokens remaining in canonical_output: {rest2}")

    d_before = ast_depth(n1)
    d_after = ast_depth(n2)
    reduction = d_before - d_after

    return {
        "scene": scene.get("scene", "SRK8_PIPELINE_FLOW"),
        "metric_name": metric_name,
        "depth_before": d_before,
        "depth_after": d_after,
        "ast_depth_reduction": reduction,
        "input_expression": inp,
        "canonical_output": out,
    }

def main() -> int:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)

    ledger_path = pick_existing(LEDGER_CANON, LEDGER_FALLBACK)
    repaired_path = pick_existing(REPAIRED_CANON, REPAIRED_FALLBACK)

    ledger_rep = read_jsonl(ledger_path)
    repaired_rep = read_jsonl(repaired_path)

    required_paths = {
        "srk8_dir": str(SRK8_DIR),
        "ledger_dir": str(LEDGER_DIR),
        "scene_qfc": str(QFC_SCENE),
        "scene_alt": str(ALT_SCENE),
        "ledger": str(ledger_path),
        "ledger_repaired": str(repaired_path),
    }

    # Scene metric (deterministic)
    scene_ok = True
    scene_metric: Dict[str, Any] = {}
    scene_err: Optional[str] = None
    try:
        scene_metric = compute_scene_metric(load_scene())
    except Exception as e:
        scene_ok = False
        scene_err = f"{type(e).__name__}: {e}"

    # Decide pass/fail (strict about parsing; soft about content schema)
    ok = True
    reasons: List[str] = []

    if not ledger_rep.exists or ledger_rep.entries <= 0:
        ok = False
        reasons.append("missing_or_empty_theorem_ledger")
    if not repaired_rep.exists or repaired_rep.entries <= 0:
        ok = False
        reasons.append("missing_or_empty_theorem_ledger_repaired")

    if ledger_rep.parse_errors > 0:
        ok = False
        reasons.append("theorem_ledger_parse_errors")
    if repaired_rep.parse_errors > 0:
        ok = False
        reasons.append("theorem_ledger_repaired_parse_errors")

    if not scene_ok:
        ok = False
        reasons.append("scene_metric_failed")

    status = "PASS" if ok else "FAIL"

    # Metrics JSON (machine readable)
    metrics = {
        "lock_id": "SRK-8-v0.3",
        "timestamp_utc": utc_now_iso(),
        "status": status,
        "reasons": reasons,
        "required_paths": required_paths,
        "ledger": {
            "path": str(ledger_rep.path),
            "exists": ledger_rep.exists,
            "entries": ledger_rep.entries,
            "parse_errors": ledger_rep.parse_errors,
            "first_error": ledger_rep.first_error,
            "file_sha256": ledger_rep.file_sha256,
            "hash_fields_nonempty": ledger_rep.nonempty_hash_fields,
            "hash_fields_empty": ledger_rep.empty_hash_fields,
        },
        "ledger_repaired": {
            "path": str(repaired_rep.path),
            "exists": repaired_rep.exists,
            "entries": repaired_rep.entries,
            "parse_errors": repaired_rep.parse_errors,
            "first_error": repaired_rep.first_error,
            "file_sha256": repaired_rep.file_sha256,
            "hash_fields_nonempty": repaired_rep.nonempty_hash_fields,
            "hash_fields_empty": repaired_rep.empty_hash_fields,
        },
        "scene_metric": scene_metric if scene_ok else {"error": scene_err},
    }
    OUT_METRICS.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Human log (evidence)
    lines: List[str] = []
    lines.append("# SRK8_LINT_PROOF.log")
    lines.append("# Deterministic evidence log for SRK-8 ledger + scene metric.")
    lines.append("")
    lines.append(f"LOCK_ID: {metrics['lock_id']}")
    lines.append(f"TIMESTAMP_UTC: {metrics['timestamp_utc']}")
    lines.append(f"STATUS: {status}")
    if reasons:
        lines.append("REASONS:")
        for r in reasons:
            lines.append(f"  - {r}")
    lines.append("")
    lines.append("LEDGER:")
    lines.append(f"  path: {ledger_rep.path}")
    lines.append(f"  entries: {ledger_rep.entries}")
    lines.append(f"  parse_errors: {ledger_rep.parse_errors}")
    if ledger_rep.first_error:
        lines.append(f"  first_error: {ledger_rep.first_error}")
    if ledger_rep.file_sha256:
        lines.append(f"  sha256: {ledger_rep.file_sha256}")
    lines.append("")
    lines.append("LEDGER_REPAIRED:")
    lines.append(f"  path: {repaired_rep.path}")
    lines.append(f"  entries: {repaired_rep.entries}")
    lines.append(f"  parse_errors: {repaired_rep.parse_errors}")
    if repaired_rep.first_error:
        lines.append(f"  first_error: {repaired_rep.first_error}")
    if repaired_rep.file_sha256:
        lines.append(f"  sha256: {repaired_rep.file_sha256}")
    lines.append("")
    lines.append("SCENE_METRIC:")
    if scene_ok:
        lines.append(f"  scene: {scene_metric.get('scene')}")
        lines.append(f"  metric: {scene_metric.get('metric_name')}")
        lines.append(f"  depth_before: {scene_metric.get('depth_before')}")
        lines.append(f"  depth_after: {scene_metric.get('depth_after')}")
        lines.append(f"  AST_DEPTH_REDUCTION: {scene_metric.get('ast_depth_reduction')}")
        lines.append(f"  input_expression: {scene_metric.get('input_expression')}")
        lines.append(f"  canonical_output: {scene_metric.get('canonical_output')}")
    else:
        lines.append(f"  error: {scene_err}")

    OUT_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Console output (match your other runners)
    tag = "[PASS]" if ok else "[FAIL]"
    print(f"{tag} wrote: {OUT_LOG}")
    print(f"       wrote: {OUT_METRICS}")
    if scene_ok:
        print(
            f"       entries={ledger_rep.entries} repaired={repaired_rep.entries} "
            f"ast_depth_reduction={scene_metric.get('ast_depth_reduction')}"
        )
    else:
        print(f"       scene_metric_error={scene_err}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
