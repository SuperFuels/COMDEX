# ============================================================
# 🧭 Deprecated Redirect Stub — SCI Commit Atom API
# ============================================================
# This file has been superseded by:
#   → backend/api/sci_commit_atom.py
#
# It remains as a lightweight redirect layer to avoid import errors
# or broken routes in older modules that may still reference it.

from fastapi import APIRouter, HTTPException
from backend.api.sci_commit_atom import commit_atom  # re-export unified version

router = APIRouter(prefix="/api/sci", tags=["SCI (redirect)"])

@router.post("/commit_atom")
async def commit_atom_redirect(*args, **kwargs):
    """
    🚧 Deprecated endpoint.  
    Delegates to the unified /api/sci/commit_atom route.
    """
    try:
        return await commit_atom(*args, **kwargs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redirect failed: {e}")