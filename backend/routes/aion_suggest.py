# backend/routes/aion_suggest.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

# Sample static suggestions - later this can be dynamic based on AION state or memory
STATIC_COMMANDS = [
    "run dream cycle",
    "show boot progress",
    "list goals",
    "clear memory cache",
    "analyze emotion graph",
    "start planning module",
    "show identity profile",
    "run milestone tracker",
    "sync state",
    "shutdown safe mode"
]

class SuggestRequest(BaseModel):
    query: str

class SuggestResponse(BaseModel):
    suggestions: List[str]

@router.post("/api/aion/suggest", response_model=SuggestResponse)
def get_command_suggestions(req: SuggestRequest):
    filtered = [cmd for cmd in STATIC_COMMANDS if req.query.lower() in cmd.lower()]
    return SuggestResponse(suggestions=filtered)