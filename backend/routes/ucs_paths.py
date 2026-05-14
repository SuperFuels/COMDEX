from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from modules.sqi.sqi_tessaris_bridge import choose_route, execute_route

router = APIRouter()

class Goal(BaseModel):
    id: str
    caps: List[str] = []
    tags: List[str] = []
    nodes: List[str] = []

@router.post("/route")
def route(goal: Goal):
    return choose_route(goal.dict())

@router.post("/execute")
def execute(plan: Dict[str, Any]):
    return execute_route(plan, ctx={})