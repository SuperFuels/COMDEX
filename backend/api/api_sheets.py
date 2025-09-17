# File: backend/api/api_sheets.py
# 📁 Lists available .sqs.json files for selection in frontend UI

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from jsonschema import validate, ValidationError
import json

router = APIRouter()
security = HTTPBearer()

# 🔍 Default directory for .sqs.json files (configurable via env)
SHEET_DIR = Path(os.getenv("SHEET_DIR", "backend/data/sheets"))

# ✅ Basic .sqs.json structure validation
SQS_SCHEMA = {
    "type": "object",
    "required": ["cells"],
    "properties": {
        "cells": {"type": "array"},
        "metadata": {"type": "object"}
    },
    "additionalProperties": False
}

@router.get("/api/sheets/list", dependencies=[Depends(security)])
def list_available_sheets(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # 🔐 Basic token authentication
    if credentials.credentials != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")

    if not SHEET_DIR.exists() or not SHEET_DIR.is_dir():
        raise HTTPException(status_code=500, detail=f"⚠️ Sheet directory not found: {SHEET_DIR}")

    sheets = []

    for f in SHEET_DIR.glob("*.sqs.json"):
        if f.is_file():
            try:
                with open(f, "r") as file:
                    data = json.load(file)
                    validate(instance=data, schema=SQS_SCHEMA)
                    sheets.append({
                        "name": f.name,
                        "title": data.get("metadata", {}).get("title", f.name)
                    })
            except (json.JSONDecodeError, ValidationError) as e:
                print(f"⚠️ Skipping invalid file {f.name}: {str(e)}")
                continue

    return JSONResponse(content={"files": sorted(sheets, key=lambda x: x["name"])})