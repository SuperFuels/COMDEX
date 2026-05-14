# routes/aion_dream_test.py

from fastapi import APIRouter
from backend.modules.hexcore.dream_game_link import DreamGameLink

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

@router.post("/aion/test-game-dream")
def test_game_dream():
    dream_link = DreamGameLink()
    result = dream_link.run_game_dream_cycle()
    return {"dream": result}