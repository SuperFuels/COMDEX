# backend/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, Body, status, Query
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..utils.auth import (
    hash_password,
    create_access_token,
    verify_password,
    get_current_user,
    generate_nonce,
    verify_siwe,
)

# ─── Schemas ────────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Literal["buyer", "supplier"]
    wallet_address: Optional[str] = None

    # supplier fields
    business_name: Optional[str] = None
    address: Optional[str] = None
    delivery_address: Optional[str] = None
    products: Optional[list[str]] = None  # list of slugs

    # buyer fields
    monthly_spend: Optional[str] = None


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class SIWELogin(BaseModel):
    message: str
    signature: str


class TokenRoleOut(BaseModel):
    token: str
    role: str


class ProfileOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    wallet_address: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Router Setup ────────────────────────────────────────────────────────

# We prefix every route here with "/api/auth"
router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.get("/nonce")
def get_siwe_nonce(
    address: str = Query(..., description="Wallet address for SIWE")
) -> dict:
    """
    GET /api/auth/nonce?address=<wallet_address>
    """
    nonce = generate_nonce()
    return {"nonce": nonce}


@router.post(
    "/register",
    response_model=TokenRoleOut,
    status_code=status.HTTP_201_CREATED,
)
def register(
    body: RegisterBody = Body(...),
    db: Session = Depends(get_db),
):
    """
    POST /api/auth/register
    """
    # 1) Prevent duplicate email
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    # 2) Normalize wallet if provided
    wallet = None
    if body.wallet_address:
        from web3 import Web3
        try:
            wallet = Web3.to_checksum_address(body.wallet_address)
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid wallet address format")

    # 3) Create user record
    user = User(
        name            = body.name,
        email           = body.email,
        password_hash   = hash_password(body.password),
        role            = body.role,
        wallet_address  = wallet,
        created_at      = datetime.utcnow(),
    )

    # 4) Role-specific fields
    if body.role == "supplier":
        if not body.business_name or not body.products:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Suppliers must provide both business_name and products"
            )
        user.business_name    = body.business_name
        user.address          = body.address or ""
        user.delivery_address = body.delivery_address or ""
        user.products         = body.products
    else:  # buyer
        user.monthly_spend = body.monthly_spend or ""

    # 5) Persist & issue JWT
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id, role=user.role)
    return {"token": token, "role": user.role}


@router.post("/login", response_model=TokenRoleOut)
def login(
    body: LoginBody = Body(...),
    db: Session = Depends(get_db),
):
    """
    POST /api/auth/login
    """
    user = db.query(User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token(subject=user.id, role=user.role)
    return {"token": token, "role": user.role}


@router.post("/siwe", response_model=TokenRoleOut)
def siwe_login(
    body: SIWELogin = Body(...),
    db: Session = Depends(get_db),
):
    """
    POST /api/auth/siwe
    """
    user, token = verify_siwe(body.message, body.signature, db)
    return {"token": token, "role": user.role}


@router.get("/profile", response_model=ProfileOut)
def profile(
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/auth/profile
    """
    return current_user