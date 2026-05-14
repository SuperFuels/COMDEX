# backend/routes/aion_homeostasis_alias.py
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.api.aion_dashboard import dashboard_get

router = APIRouter(tags=["AION Homeostasis"])

@router.get("/api/homeostasis")
def api_homeostasis(refresh: int = Query(0, description="1 = recompute aggregator now")) -> JSONResponse:
    return dashboard_get(refresh=refresh)