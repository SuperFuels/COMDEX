# backend/api/ast_hologram_api.py
from __future__ import annotations

from typing import Any, Dict, List, Literal

import ast as pyast
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.symbolic.codex_ast_types import CodexAST
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.symbolic.codex_ast_parser import parse_codexlang_to_ast
from backend.modules.symbolic.natural_language_parser import parse_nl_to_ast

try:
    # Photon parser is optional; we’ll degrade gracefully if not present
    from backend.modules.photonlang.parser import parse_source as parse_photon_source
except Exception:  # pragma: no cover
    parse_photon_source = None  # type: ignore[assignment]

try:
    # Field compiler is optional; attach ψ–κ–T-style tensors when available
    from backend.modules.qwave.ghx_field_compiler import compile_field_tensor
except Exception:  # pragma: no cover
    compile_field_tensor = None  # type: ignore[assignment]

# NOTE: no "/api" here – main.py mounts with prefix="/api"
# final path is: POST /api/ast/hologram
router = APIRouter(tags=["ast-hologram"])

Language = Literal["python", "photon", "codex", "nl"]


class AstHologramRequest(BaseModel):
    source: str
    language: Language


class GhxLikeHologram(BaseModel):
    ghx_version: str = "1.0"
    origin: str
    container_id: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}


class AstHologramResponse(BaseModel):
    ast: Dict[str, Any]
    kind: Language
    glyphs: List[Dict[str, Any]]
    ghx: GhxLikeHologram
    mermaid: str | None = None


# ---------- helpers ----------


def _ensure_codex_ast(obj: Any) -> CodexAST:
    if isinstance(obj, CodexAST):
        return obj
    if isinstance(obj, dict):
        return CodexAST.from_dict(obj)
    raise TypeError(f"Unsupported AST type: {type(obj)}")


def _python_source_to_codex_ast(src: str) -> CodexAST:
    """Mirror the adapter from ast_api so hologram path sees the same tree."""
    try:
        tree = pyast.parse(src)
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Python parse error: {e}")

    def node_to_dict(node: Any) -> Any:
        if isinstance(node, pyast.AST):
            result: Dict[str, Any] = {"type": node.__class__.__name__}
            for field, value in pyast.iter_fields(node):
                if isinstance(value, list):
                    result[field] = [node_to_dict(v) for v in value]
                else:
                    result[field] = node_to_dict(value)
            return result
        if isinstance(node, (str, int, float, bool)) or node is None:
            return node
        return str(node)

    root_dict = node_to_dict(tree)
    inner = {"root": root_dict, "args": []}
    return CodexAST.from_dict(
        {
            "ast": inner,
            "metadata": {"origin": "python_builtin_ast"},
        }
    )


def _parse_to_codex_ast(src: str, lang: Language) -> CodexAST:
    if not src.strip():
        raise HTTPException(status_code=400, detail="Empty source.")

    if lang == "python":
        return _python_source_to_codex_ast(src)

    if lang == "codex":
        return _ensure_codex_ast(parse_codexlang_to_ast(src))

    if lang == "nl":
        return _ensure_codex_ast(parse_nl_to_ast(src))

    if lang == "photon":
        if parse_photon_source is None:
            raise HTTPException(
                status_code=501,
                detail="Photon parser not available in this build.",
            )
        program = parse_photon_source(src)
        return CodexAST({"type": "photon_program", "root": program.__dict__})

    raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")


def _codex_ast_to_mermaid(ast_obj: CodexAST) -> str:
    """
    Same simple AST → Mermaid flowchart as in ast_api.
    """
    from collections import deque

    root = ast_obj.ast or {}
    lines: List[str] = ["flowchart TD"]
    queue = deque()
    counter = 0

    def new_id() -> str:
        nonlocal counter
        counter += 1
        return f"n{counter}"

    def enqueue(node: Any, parent_id: str | None = None):
        nid = new_id()
        label = str(node.get("type", "node")) if isinstance(node, dict) else str(node)
        label = label.replace('"', "'")
        lines.append(f'  {nid}["{label}"]')
        if parent_id:
            lines.append(f"  {parent_id} --> {nid}")
        queue.append((nid, node))

    enqueue(root, None)

    while queue:
        nid, node = queue.popleft()
        if not isinstance(node, dict):
            continue

        child_keys = [
            "root",
            "left",
            "right",
            "value",
            "body",
            "args",
            "operands",
            "children",
            "targets",
            "test",
            "iter",
        ]
        for key in child_keys:
            val = node.get(key)
            if val is None:
                continue
            if isinstance(val, list):
                for c in val:
                    enqueue(c, nid)
            else:
                enqueue(val, nid)

    return "\n".join(lines)

def _compute_field_tensor_stub(codex_ast: CodexAST) -> Dict[str, Any]:
    """
    Very small, cheap placeholder for a ψ–κ–T-like field tensor.

    This is intentionally simple so it never chokes:
    - counts nodes
    - estimates max depth
    - records language / origin-ish hints
    """
    data = codex_ast.to_dict()
    root = (data.get("ast") or {}).get("root") or {}
    language = (data.get("metadata") or {}).get("language", "unknown")

    total_nodes = 0
    max_depth = 0

    def walk(node: Any, depth: int = 0) -> None:
        nonlocal total_nodes, max_depth
        if not isinstance(node, dict):
            return
        total_nodes += 1
        if depth > max_depth:
            max_depth = depth
        for v in node.values():
            if isinstance(v, dict):
                walk(v, depth + 1)
            elif isinstance(v, list):
                for c in v:
                    if isinstance(c, dict):
                        walk(c, depth + 1)

    walk(root, 0)

    return {
        "version": "0.1-stub",
        "language": language,
        "total_nodes": total_nodes,
        "max_depth": max_depth,
        # these names mirror ψ–κ–T but are just heuristics for now
        "psi": float(max_depth + 1),
        "kappa": float(total_nodes),
        "tau": float(total_nodes * (max_depth + 1)),
    }


def _compute_psi_kappa_tau_signature_stub(field_tensor: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derive a tiny 'signature' vector from the stub field tensor.
    Later this can become a proper ψ–κ–T object.
    """
    psi = float(field_tensor.get("psi", 0.0))
    kappa = float(field_tensor.get("kappa", 0.0))
    tau = float(field_tensor.get("tau", 0.0))

    magnitude = (psi ** 2 + kappa ** 2 + tau ** 2) ** 0.5 or 1.0

    return {
        "version": "0.1-stub",
        "psi": psi,
        "kappa": kappa,
        "tau": tau,
        "norm": magnitude,
        "psi_norm": psi / magnitude,
        "kappa_norm": kappa / magnitude,
        "tau_norm": tau / magnitude,
    }

def _codex_ast_to_ghx_graph(
    ast_obj: CodexAST,
    max_nodes: int = 128,
    max_depth: int = 8,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Build a tree-shaped GHX graph directly from the CodexAST.

    - One node per *structural* AST node
    - Hard cap on nodes and depth so we don't nuke the viewer
    """

    data = ast_obj.to_dict()
    root = (data.get("ast") or {}).get("root")

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    counter = 0

    def add_node(node: Any, parent_id: str | None = None, depth: int = 0) -> str | None:
        nonlocal counter
        if counter >= max_nodes:
            return None
        if depth > max_depth:
            return None

        node_id = f"n{counter}"
        counter += 1

        if isinstance(node, dict):
            label = str(node.get("type", "node"))
        else:
            label = str(node)

        nodes.append(
            {
                "id": node_id,
                "data": {
                    "label": label,
                    "ast": node,
                },
            }
        )

        if parent_id is not None:
            edges.append(
                {
                    "id": f"e{parent_id}-{node_id}",
                    "source": parent_id,
                    "target": node_id,
                    "kind": "ast_child",
                }
            )

        # leaves are done
        if not isinstance(node, dict):
            return node_id

        # Only follow *structural* links; do NOT follow "value" recursively,
        # otherwise we get chains of synthetic "value" nodes.
        structural_keys = [
            "body",
            "test",
            "target",
            "iter",
            "left",
            "right",
            "elts",
            "args",
            "func",
            # "value",  # intentionally omitted to avoid value→value chains
        ]

        for key, val in node.items():
            if key in (
                "type",
                "ctx",
                "kind",
                "lineno",
                "col_offset",
                "end_lineno",
                "end_col_offset",
            ):
                continue

            if key not in structural_keys:
                continue

            if isinstance(val, dict):
                add_node(val, node_id, depth + 1)
            elif isinstance(val, list):
                for child in val:
                    if isinstance(child, dict):
                        add_node(child, node_id, depth + 1)
                    elif child is not None:
                        add_node({"type": key, "value": child}, node_id, depth + 1)
            elif val is not None:
                add_node({"type": key, "value": val}, node_id, depth + 1)

        return node_id

    if root is not None:
        add_node(root, None, 0)

    return nodes, edges


# ---------- main endpoint ----------
@router.post("/ast/hologram", response_model=AstHologramResponse)
def build_ast_hologram(req: AstHologramRequest) -> AstHologramResponse:
    # 1) Parse text → CodexAST
    codex_ast = _parse_to_codex_ast(req.source, req.language)

    # 2) CodexAST → glyph list (best-effort, no 500s)
    glyphs_json: List[Dict[str, Any]] = []
    try:
        raw_glyphs = encode_codex_ast_to_glyphs(codex_ast)
    except Exception as e:  # pragma: no cover
        print(f"[ast_hologram] glyph encoding failed: {e}", flush=True)
        raw_glyphs = []

    for g in raw_glyphs:
        if hasattr(g, "to_dict"):
            glyphs_json.append(g.to_dict())  # type: ignore[call-arg]
        elif hasattr(g, "__dict__"):
            glyphs_json.append(dict(getattr(g, "__dict__")))
        else:
            glyphs_json.append({"value": str(g)})

    # 3) AST → GHX graph (tree-shaped)
    nodes, edges = _codex_ast_to_ghx_graph(codex_ast)

    # 3.5) Cheap field tensor + ψκT signature (stub for now)
    field_tensor = _compute_field_tensor_stub(codex_ast)
    psi_kappa_tau_signature = _compute_psi_kappa_tau_signature_stub(field_tensor)

    ghx = GhxLikeHologram(
        origin=f"ast:{req.language}",
        container_id="devtools-ast-hologram",
        nodes=nodes,
        edges=edges,
        metadata={
            "kind": "ast_hologram",
            "language": req.language,
            "glyph_count": len(glyphs_json),
            "node_count": len(nodes),
            "field_tensor": field_tensor,
            "psi_kappa_tau_signature": psi_kappa_tau_signature,
        },
    )

    # 4) Mermaid text (for Dev Tools AST panel)
    mermaid = _codex_ast_to_mermaid(codex_ast)

    return AstHologramResponse(
        ast=codex_ast.to_dict(),
        kind=req.language,
        glyphs=glyphs_json,
        ghx=ghx,
        mermaid=mermaid,
    )