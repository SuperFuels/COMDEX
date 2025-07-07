# File: backend/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, Body, status, Query
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.database import Base, engine, get_db
from backend.models.user import User
from backend.utils.auth import (
    hash_password,
    create_access_token,
    verify_password,
    get_current_user,
    generate_nonce,
    verify_siwe,
)

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ─── 1) Define Pydantic Schemas ──────────────────────────────────────────

class RegisterBody(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Literal["buyer", "supplier", "admi"]
    wallet_address: Optional[str] = None

    # supplier-only fields
    business_name: Optional[str] = None
    address: Optional[str] = None
    delivery_address: Optional[str] = None
    products: Optional[list[str]] = None  # product slugs

    # buyer-only fields
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

# ─── 2) Create APIRouter ─────────────────────────────────────────────────
router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/nonce")
def get_siwe_nonce(
    address: str = Query(..., description="Wallet address for SIWE")
) -> dict:
    return {"nonce": generate_nonce()}

@router.post(
    "/register",
    response_model=TokenRoleOut,
    status_code=status.HTTP_201_CREATED,
)
def register(
    body: RegisterBody = Body(...),
    db: Session = Depends(get_db),
):
    # Prevent duplicate email
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Normalize wallet and check uniqueness
    wallet = None
    if body.wallet_address:
        from web3 import Web3
        try:
            wallet = Web3.to_checksum_address(body.wallet_address)
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid wallet address format")

        if db.query(User).filter_by(wallet_address=wallet).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Wallet address already registered")

    # Create user base fields
    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        wallet_address=wallet,
        created_at=datetime.utcnow(),
    )

    # Role-specific validation
    if body.role == "supplier":
        if not body.business_name or not body.products:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Suppliers must provide business_name and products"
            )
        user.business_name = body.business_name
        user.address = body.address or ""
        user.delivery_address = body.delivery_address or ""
        user.products = body.products

    elif body.role == "buyer":
        user.monthly_spend = body.monthly_spend or ""

    elif body.role == "admi":
        # No extra fields required for admin
        pass

    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    # Persist user
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Registration failed: duplicate data")

    db.refresh(user)
    token = create_access_token(subject=user.id, role=user.role)
    return {"token": token, "role": user.role}

@router.post("/login", response_model=TokenRoleOut)
def login(
    body: LoginBody = Body(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(subject=user.id, role=user.role)
    return {"token": token, "role": user.role}

@router.post("/siwe", response_model=TokenRoleOut)
def siwe_login(
    body: SIWELogin = Body(...),
    db: Session = Depends(get_db),
):
    user, token = verify_siwe(body.message, body.signature, db)
    return {"token": token, "role": user.role}

@router.get("/profile", response_model=ProfileOut)
def profile(
    current_user: User = Depends(get_current_user),
):
    return current_user