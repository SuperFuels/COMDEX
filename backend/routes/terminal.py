from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..utils.terminal import run_query

router = APIRouter(
    prefix="/api/terminal",
    tags=["Terminal"],
)

class QueryRequest(BaseModel):
    prompt: str = Field(..., example="Tell me about whey protein")

class QueryResponse(BaseModel):
    analysisText: str
    visualPayload: dict

@router.post("/query", response_model=QueryResponse)
def terminal_query(
    req: QueryRequest,
    db: Session = Depends(get_db),
):
    """
    Run an “AI + DB” pipeline for a free‐form query.
    POST /api/terminal/query
    Body: { prompt: "..." }
    """
    try:
        result = run_query(req.prompt, db)
    except Exception as e:
        raise HTTPException(500, f"Terminal pipeline error: {e}")

    # validate returned shape:
    if not isinstance(result, dict) or \
       'analysisText' not in result or \
       'visualPayload' not in result:
        raise HTTPException(500, "Invalid terminal response format")

    return QueryResponse(
        analysisText=result['analysisText'],
        visualPayload=result['visualPayload'],
    )