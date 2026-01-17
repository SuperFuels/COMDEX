from fastapi import APIRouter
from pydantic import BaseModel

# import your live demo runner
from backend.modules.sqi.tests.entangled_scheduler_live import run_entangled_scheduler

router = APIRouter(prefix="/api/sqi/demo", tags=["sqi-demo"])

class EntangledReq(BaseModel):
    policy: str = "p3"
    container_id: str = "sqi_demo"

@router.post("/entangled_scheduler")
def entangled_scheduler(req: EntangledReq):
    return run_entangled_scheduler(req.policy, req.container_id)