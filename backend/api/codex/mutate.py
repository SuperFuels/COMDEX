from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.codexlang.codex_ast import parse_codex_ast_from_json
from backend.modules.codexlang.codex_ast_utils import safe_serialize_ast
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.utils.logger import log_info
from backend.modules.codex.code_metrics import CodexMetrics

router = APIRouter()
executor = CodexExecutor()
metrics = CodexMetrics()

class GoalMutationRequest(BaseModel):
    ast: Dict[str, Any]
    goal: str
    context: Optional[Dict[str, Any]] = {}

@router.post("/api/codex/mutate_goal")
async def codex_mutate_goal(request: GoalMutationRequest):
    try:
        ast = parse_codex_ast_from_json(request.ast)
        instruction_tree = encode_codex_ast_to_glyphs(ast)[0].to_instruction_tree()

        context = request.context or {}
        context.update({
            "goal": request.goal,
            "source": "GOAL_REWRITE_API",
            "ast": ast
        })

        result = executor.execute_instruction_tree(instruction_tree, context=context)

        glyph_before = context.get("glyph", "?")
        glyph_after = result.get("result", {}).get("suggestion", "?")
        score = result.get("result", {}).get("goal_match_score", 0.0)
        success = score > 0.6

        # Metrics
        metrics.record_mutation_test(
            glyph=glyph_before,
            suggestion=glyph_after,
            success=success,
            context=context
        )

        return {
            "status": "success",
            "goal_match_score": score,
            "suggestion": glyph_after,
            "metadata": {
                "original_glyph": glyph_before,
                "goal": request.goal,
                "success": success,
                "dc_container": context.get("container_id")
            }
        }

    except Exception as e:
        log_info(f"❌ Goal-based mutation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))