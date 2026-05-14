# backend/api/ast_api.py
from __future__ import annotations

from typing import Literal, Any, Dict, List

import ast as pyast
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.symbolic.codex_ast_types import CodexAST, make_unknown
from backend.modules.codex.codex_ast_encoder import (
    parse_python_file_to_codex_ast,  # kept for later if you want
    encode_codex_ast_to_glyphs,
)
from backend.modules.symbolic.codex_ast_parser import parse_codexlang_to_ast
from backend.modules.symbolic.natural_language_parser import parse_nl_to_ast
from backend.modules.photonlang.parser import parse_source as parse_photon_source

# NOTE: no "/api" here – main.py mounts with prefix="/api"
router = APIRouter(tags=["ast"])

# ---------- models ----------

Language = Literal["python", "photon", "codex", "nl"]


class AstRequest(BaseModel):
    source: str
    language: Language


class AstResponse(BaseModel):
    ast: Dict[str, Any]
    kind: Language
    glyphs: List[Dict[str, Any]] | None = None
    mermaid: str | None = None


class VisualizeRequest(BaseModel):
    ast: Dict[str, Any]


class VisualizeResponse(BaseModel):
    text: str


# ---------- helpers ----------

def _ensure_codex_ast(obj: Any) -> CodexAST:
    """Normalize whatever comes back into a CodexAST."""
    if isinstance(obj, CodexAST):
        return obj
    if isinstance(obj, dict):
        return CodexAST.from_dict(obj)
    # Fallback instead of hard crash
    return make_unknown()


def _python_source_to_codex_ast(src: str) -> CodexAST:
    """
    Parse Python with the stdlib `ast` module and wrap it in a CodexAST-
    compatible dict so Dev Tools can see a real tree instead of 'unknown'.
    """
    try:
        tree = pyast.parse(src)
    except SyntaxError as e:  # surface syntax errors nicely
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
        # Fallback for odd values
        return str(node)

    root_dict = node_to_dict(tree)

    # Match the shape you already saw: {"ast": {"root": ..., "args": []}, "metadata": {}}
    inner = {"root": root_dict, "args": []}
    return CodexAST.from_dict(
        {
            "ast": inner,
            "metadata": {"origin": "python_builtin_ast"},
        }
    )


def _codex_ast_to_mermaid(ast_obj: CodexAST) -> str:
    """
    Very simple generic AST → Mermaid flowchart.
    You can replace with something fancier later.
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

        # heuristic: follow common child fields
        child_keys = [
            "root",
            "left",
            "right",
            "value",
            "body",
            "args",
            "operands",
            "children",
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


# ---------- main endpoints ----------

@router.post("/ast", response_model=AstResponse)
def build_ast(req: AstRequest) -> AstResponse:
    try:
        # 1) parse into a CodexAST-ish object
        if req.language == "python":
            # New: use builtin AST adapter so we get real structure
            codex = _python_source_to_codex_ast(req.source)

        elif req.language == "codex":
            codex = parse_codexlang_to_ast(req.source)

        elif req.language == "nl":
            codex = parse_nl_to_ast(req.source)

        elif req.language == "photon":
            # photon parser returns its own Program; wrap in a dict
            program = parse_photon_source(req.source)
            codex = CodexAST(
                {
                    "type": "photon_program",
                    "root": getattr(program, "__dict__", {}),
                }
            )

        else:
            raise HTTPException(status_code=400, detail="Unsupported language")

        codex_ast = _ensure_codex_ast(codex)

        # 2) encode to glyphs
        try:
            raw_glyphs = encode_codex_ast_to_glyphs(codex_ast)
            glyphs: List[Dict[str, Any]] = []
            for g in raw_glyphs:
                if hasattr(g, "to_dict"):
                    glyphs.append(g.to_dict())  # type: ignore[arg-type]
                elif hasattr(g, "__dict__"):
                    glyphs.append(dict(g.__dict__))  # best-effort
                else:
                    glyphs.append({"value": str(g)})
        except Exception:
            glyphs = []

        # 3) mermaid preview
        mermaid = _codex_ast_to_mermaid(codex_ast)

        return AstResponse(
            ast=codex_ast.to_dict(),
            kind=req.language,
            glyphs=glyphs,
            mermaid=mermaid,
        )
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"AST build failed: {e}") from e


@router.post("/ast/visualize", response_model=VisualizeResponse)
def visualize_ast(req: VisualizeRequest) -> VisualizeResponse:
    codex_ast = _ensure_codex_ast(req.ast)
    text = _codex_ast_to_mermaid(codex_ast)
    return VisualizeResponse(text=text)