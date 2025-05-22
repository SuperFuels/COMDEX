import os
import secrets
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Body,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from eth_account.messages import encode_defunct
from web3 import Web3

from database import get_db
from models.user import User
from utils.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    SECRET_KEY,
    ALGORITHM,
)

router = APIRouter(tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/verify")

# In-memory store for nonces (DEV only)
_nonces: Dict[str, str] = {}


class SiweVerifyBody(BaseModel):
    message: str
    signature: str


class RoleOut(BaseModel):
    role: str


class RegisterOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    class Config:
        orm_mode = True


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def get_web3() -> Web3:
    rpc_url = os.getenv("WEB3_PROVIDER_URL")
    if not rpc_url:
        raise RuntimeError("Missing WEB3_PROVIDER_URL in environment")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise RuntimeError(f"Cannot connect to Web3 provider at {rpc_url}")
    return w3


@router.get("/nonce", response_model=Dict[str, str])
def get_siwe_nonce(
    request: Request,
    address: str = Query(..., description="Wallet address")
):
    """DEV: Issue a SIWE nonce + message for front-end to sign."""
    nonce = secrets.token_urlsafe(16)
    _nonces[address.lower()] = nonce

    origin = (
        request.headers.get("origin")
        or request.headers.get("host")
        or "http://localhost:3000"
    )
    parsed = urlparse(origin)
    domain = parsed.netloc
    issued = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    message = (
        f"{domain} wants you to sign in with your Ethereum account:\n"
        f"{address}\n\n"
        "Sign in to STICKEY\n\n"
        f"URI: {origin}\n"
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
    """Verify SIWE signature and return JWT + role."""
    try:
        wallet = body.message.split("\n")[1].strip().lower()
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Malformed SIWE message")

    try:
        raw = next(l for l in body.message.splitlines() if l.startswith("Nonce:"))
        nonce = raw.split("Nonce:")[1].strip()
    except StopIteration:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nonce not found")

    if _nonces.get(wallet) != nonce:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid nonce")

    w3 = get_web3()
    msg = encode_defunct(text=body.message)
    try:
        signer = w3.eth.account.recover_message(msg, signature=body.signature)
    except Exception as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Signature recovery failed: {e}"
        )

    if signer.lower() != wallet:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Signature mismatch")

    user = db.query(User).filter(User.wallet_address == wallet).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    token = create_access_token(subject=str(user.id))
    return {"token": token, "role": user.role}


@router.post("/login", response_model=TokenOut, summary="Email/password login")
def login_user(
    form_data: LoginIn,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.email).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=str(user.id))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/role", response_model=RoleOut, summary="Get current user's role")
def get_user_role(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return RoleOut(role=user.role)


@router.post(
    "/register",
    response_model=RegisterOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
def register_user(
    name: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    """Register a new user (name, email, password, role)."""
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_pw = get_password_hash(password)
    new_user = User(
        name=name,
        email=email,
        password_hash=hashed_pw,
        role=role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
