from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional, List

from backend.modules.symbolic.symbolic_ingestion_engine import SymbolicIngestionEngine
from backend.modules.codex.codex_ast_encoder import parse_codexlang_to_ast, encode_codex_ast_to_glyphs
from backend.modules.consciousness.prediction_engine import run_prediction_on_ast

router = APIRouter()

class SymbolicIngestPayload(BaseModel):
    op: str
    args: Optional[Any] = None
    codexlang: Optional[str] = None
    glyph: Optional[Dict[str, Any]] = None
    domain: Optional[str] = "general"
    source: Optional[str] = "external"
    tags: Optional[List[str]] = []

@router.post("/api/ingest-symbolic")
async def symbolic_ingest(payload: SymbolicIngestPayload):
    try:
        # Option 1: handle CodexLang prediction via AST
        if payload.op == "ingest_codexlang" and payload.codexlang:
            ast = parse_codexlang_to_ast(payload.codexlang)
            prediction = run_prediction_on_ast(ast)
            return {
                "status": "ok",
                "message": "CodexLang parsed and predicted successfully",
                "ast": ast,
                "prediction": prediction,
            }

        # Option 2: fallback to SymbolicIngestionEngine
        engine = SymbolicIngestionEngine()
        result = engine.dispatch_ingest(
            op=payload.op,
            args=payload.args,
            codexlang=payload.codexlang,
            domain=payload.domain,
            source=payload.source,
        )

        return {
            "status": "ok",
            "message": f"Successfully ingested: {payload.op}",
            "result": result
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})