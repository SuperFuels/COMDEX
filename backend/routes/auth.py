from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from utils.auth import generate_nonce, verify_siwe, create_access_token, SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/auth", tags=["auth"])

class SiweVerifyBody(BaseModel):
    message: str
    signature: str

class TokenRoleOut(BaseModel):
    token: str
    role: str

@router.get("/nonce")
def get_siwe_nonce(
    request: Request,
    address: str = Query(..., description="Wallet address")
):
    """
    Issue a SIWE nonce + message for front-end to sign.
    Returns { message: string } containing the full SIWE message to sign.
    """
    message = generate_nonce_message(request, address)
    return {"message": message}

@router.post("/verify", response_model=TokenRoleOut)
def verify_signature(
    body: SiweVerifyBody = Body(...),
    db: Session = Depends(get_db)
):
    """
    Verify SIWE signature, lookup/create user, and return JWT + role.
    """
    try:
        user, token = verify_siwe(
            message=body.message,
            signature=body.signature,
            db=db
        )
    except HTTPException as e:
        # propagate FastAPI errors
        raise e
    return {"token": token, "role": user.role}

# Helper to build SIWE message using our utils.generate_nonce
from urllib.parse import urlparse
import secrets
from datetime import datetime

def generate_nonce_message(request: Request, address: str) -> str:
    nonce = generate_nonce()
    origin = request.headers.get("origin") or f"http://{request.client.host}:{request.url.port}"
    parsed = urlparse(origin)
    domain = parsed.netloc
    issued = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    message = (
        f"{domain} wants you to sign in with your Ethereum account:\n"
        f"{address}\n\n"
        f"Sign in to STICKEY\n\n"
        f"URI: {origin}\n"
        f"Version: 1\n"
        f"Chain ID: 1\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued}"
    )
    return message
