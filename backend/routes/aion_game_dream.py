# routes/aion_dream_test.py

from fastapi import APIRouter
from backend.modules.hexcore.dream_game_link import DreamGameLink

router = APIRouter()

@router.post("/aion/test-game-dream")
def test_game_dream():
    dream_link = DreamGameLink()
    result = dream_link.run_game_dream_cycle()
    return {"dream": result}