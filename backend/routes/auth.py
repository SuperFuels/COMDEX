# backend/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, Request, Body, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from database import get_db
from models.user import User
from utils.auth import verify_siwe, generate_nonce, create_access_token
from siwe import SiweMessage  # EIP-4361 message builder

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
    # Derive domain from origin header
    origin = request.headers.get("origin") or f"http://{request.client.host}:{request.url.port}"
    domain = origin.replace("https://", "").replace("http://", "")

    # Generate a fresh nonce and timestamp
    nonce = generate_nonce()
    issued_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # Build the SIWE message
    siwe_msg = SiweMessage(
        domain=domain,
        address=address,
        statement="Sign in to STICKEY",
        uri=origin,
        version="1",
        chain_id=1,
        nonce=nonce,
        issued_at=issued_at,
    )
    message = siwe_msg.prepare_message()
    logger.debug(f"Generated SIWE message: {repr(message)}")
    return {"message": message}


@router.post("/verify", response_model=TokenRoleOut)
def verify_signature(
    body: SiweVerifyBody = Body(...),
    db: Session = Depends(get_db)
):
    """
    Verify SIWE signature, lookup/create user, and return JWT + role.
    """
    # Normalize newlines to exactly "\n"
    normalized_message = body.message.replace("\r\n", "\n")
    logger.debug(f"Raw SIWE message received: {repr(normalized_message)}")

    try:
        user, token = verify_siwe(
            message=normalized_message,
            signature=body.signature,
            db=db
        )
    except HTTPException:
        logger.error("SIWE verification failed", exc_info=True)
        raise

    return {"token": token, "role": user.role}


@router.post("/test-login", response_model=TokenRoleOut)
def test_login(
    db: Session = Depends(get_db)
):
    """
    🔧 DEV ONLY: issue a real JWT for the first user (or create one)
    so you can hit protected endpoints without SIWE.
    """
    user = db.query(User).first()
    if not user:
        # create a dummy user if none exists
        user = User(address="0xDEADBEEF", role="buyer")
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(subject=user.id, role=user.role)
    logger.debug(f"Issued test JWT for user {user.id}")
    return {"token": token, "role": user.role}