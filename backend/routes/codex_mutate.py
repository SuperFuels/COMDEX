from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.symbolic.codex_ast_parser import parse_codex_ast_from_json
from backend.modules.utils.logger import log_info

from backend.modules.codex.codex_metrics import CodexMetrics

router = APIRouter()
executor = CodexExecutor()
metrics = CodexMetrics()

class MutationRequest(BaseModel):
    glyph: str
    ast: Dict[str, Any]
    context: Optional[Dict[str, Any]] = {}

@router.post("/api/codex/mutate")
async def codex_mutation(request: MutationRequest):
    try:
        ast = parse_codex_ast_from_json(request.ast)
        instruction_tree = encode_codex_ast_to_glyphs(ast)[0].to_instruction_tree()

        context = request.context or {}
        context.update({
            "glyph": request.glyph,
            "ast": ast,
            "source": "REST_API",
        })

        result = executor.execute_instruction_tree(instruction_tree, context=context)

        if result["status"] == "success" and result["result"].get("status") == "contradiction":
            suggestion = result["result"].get("suggestion")

            # ✅ Record mutation test benchmark
            metrics.record_mutation_test(
                glyph=request.glyph,
                suggestion=suggestion,
                success=True,
                context=context
            )

            return {
                "status": "contradiction",
                "suggestion": suggestion,
                "metadata": {
                    "glyph": request.glyph,
                    "container": context.get("container_id"),
                    "tags": ["rewrite", "api"]
                }
            }

        return {
            "status": result["status"],
            "result": result.get("result", {}),
            "cost": result.get("cost"),
            "elapsed": result.get("elapsed")
        }

    except Exception as e:
        log_info(f"❌ Mutation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))