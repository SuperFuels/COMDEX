# backend/routes/auth.py

import os
import secrets
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict

from fastapi import APIRouter, Depends, Query, Body, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from eth_account.messages import encode_defunct
from web3 import Web3

from database import get_db
from models.user import User
from utils.auth import create_access_token, SECRET_KEY, ALGORITHM

router = APIRouter(tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/verify")

# DEV-only in-memory nonce store
_nonces: Dict[str, str] = {}

# Your one “supplier” wallet for testing
DEV_SUPPLIER_WALLET = "0x70997970c51812dc3a010c7d01b50e0d17dc79c8".lower()


def get_web3() -> Web3:
    """
    Lazily instantiate a Web3 HTTPProvider from env.
    """
    rpc_url = os.getenv("WEB3_PROVIDER_URL")
    if not rpc_url:
        raise RuntimeError("Missing WEB3_PROVIDER_URL in environment")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise RuntimeError(f"Cannot connect to Web3 provider at {rpc_url}")

    return w3


class SiweVerifyBody(BaseModel):
    message: str
    signature: str


@router.get("/nonce", response_model=Dict[str, str])
def get_siwe_nonce(address: str = Query(..., description="Wallet address")):
    """
    DEV: Issue a SIWE nonce + message for the front-end to sign.
    """
    nonce = secrets.token_urlsafe(16)
    _nonces[address.lower()] = nonce

    frontend = "http://localhost:3000"
    domain = urlparse(frontend).netloc
    issued = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    message = (
        f"{domain} wants you to sign in with your Ethereum account:\n"
        f"{address}\n\n"
        "Sign in to STICKEY\n\n"
        f"URI: {frontend}\n"
        "Version: 1\n"
        "Chain ID: 1\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued}"
    )
    return {"nonce": nonce, "message": message}


@router.post("/verify", response_model=Dict[str, str])
def verify_siwe(
    body: SiweVerifyBody = Body(...),
    db: Session = Depends(get_db),
):
    """
    Verify a SIWE message and signature. Return a JWT.
    """
    # 1) Extract wallet
    try:
        wallet = body.message.split("\n")[1].strip().lower()
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed SIWE message: cannot extract wallet address"
        )

    # 2) Validate nonce
    try:
        raw = next(
            line
            for line in body.message.splitlines()
            if line.startswith("Nonce:")
        )
        nonce = raw.split("Nonce:")[1].strip()
    except StopIteration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nonce not found in SIWE message"
        )

    if _nonces.get(wallet) != nonce:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid nonce"
        )

    # 3) Recover signature using Web3
    try:
        w3 = get_web3()
        msg = encode_defunct(text=body.message)
        signer = w3.eth.account.recover_message(msg, signature=body.signature)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signature recovery failed: {e}"
        )

    if signer.lower() != wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signature mismatch"
        )

    # 4) Find user in DB
    user = db.query(User).filter(User.wallet_address == wallet).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found for this wallet—insert one first"
        )

    # 5) Create JWT
    token = create_access_token(subject=str(user.id))
    return {"token": token, "role": user.role}


@router.get("/role", response_model=Dict[str, str])
def get_user_role(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Extracts user role from the JWT.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return {"role": user.role}

