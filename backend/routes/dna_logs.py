from fastapi import APIRouter
import json
import os

router = APIRouter()

@router.get("/aion/dna-logs")
def get_dna_logs():
    log_path = "backend/modules/dna_chain/dna_log.json"
    if not os.path.exists(log_path):
        return {"logs": []}
    with open(log_path, "r", encoding="utf-8") as f:
        logs = json.load(f)
    return {"logs": logs}