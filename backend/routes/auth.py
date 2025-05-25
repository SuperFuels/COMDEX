from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

from database import get_db
from models.user import User
from utils.auth import generate_nonce, verify_siwe

router = APIRouter(tags=["Auth"])
logger = logging.getLogger("routes.auth")
logging.basicConfig(level=logging.DEBUG)

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
    Returns { message: string } containing the full EIP-4361 SIWE message.
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
    # Log and normalize the incoming SIWE message
    raw_message = body.message or ""
    # Normalize CRLF to LF to avoid parsing issues
    normalized_message = raw_message.replace("\r\n", "\n")
    # Debug logging of the exact message received
    logger.debug(f"Raw SIWE message received: {repr(normalized_message)}")

    try:
        user, token = verify_siwe(
            message=normalized_message,
            signature=body.signature,
            db=db
        )
    except HTTPException as e:
        # Re-raise HTTPExceptions from verify_siwe
        logger.error("SIWE verification failed", exc_info=True)
        raise

    return {"token": token, "role": user.role}

# Helper to build the standard EIP-4361 message using our generate_nonce
from urllib.parse import urlparse
from datetime import datetime

def generate_nonce_message(request: Request, address: str) -> str:
    nonce = generate_nonce()
    origin = request.headers.get("origin") or f"http://{request.client.host}:{request.url.port}"
    parsed = urlparse(origin)
    domain = parsed.netloc
    issued = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    return (
        f"{domain} wants you to sign in with your Ethereum account:\n"
        f"{address}\n\n"
        f"Sign in to STICKEY\n\n"
        f"URI: {origin}\n"
        f"Version: 1\n"
        f"Chain ID: 1\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued}"
    )
