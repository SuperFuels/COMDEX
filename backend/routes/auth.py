# backend/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, Body, status
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
)

# ─── Schemas ────────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Literal["buyer", "supplier"]
    phone: Optional[str] = None
    business_name: Optional[str] = None
    address: Optional[str] = None
    delivery_address: Optional[str] = None
    products: Optional[list[str]] = None
    monthly_spend: Optional[str] = None
    wallet_address: Optional[str] = None

class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

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

router = APIRouter(prefix="/auth", tags=["Auth"])

# ─── REGISTER ───────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenRoleOut,
    status_code=status.HTTP_201_CREATED,
)
def register(
    body: RegisterBody = Body(...),
    db: Session     = Depends(get_db),
):
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Email already registered"
        )

    wallet = None
    if body.wallet_address:
        from web3 import Web3
        try:
            wallet = Web3.to_checksum_address(body.wallet_address)
        except Exception:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Invalid wallet address format"
            )

    user = User(
        name           = body.name,
        email          = body.email,
        password_hash  = hash_password(body.password),
        role           = body.role,
        phone          = body.phone,
        wallet_address = wallet,
        created_at     = datetime.utcnow(),
    )

    if body.role == "supplier":
        if not body.business_name or not body.products:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Suppliers must provide business_name and products"
            )
        user.business_name    = body.business_name
        user.address          = body.address or ""
        user.delivery_address = body.delivery_address or ""
        user.products         = body.products
    else:
        user.monthly_spend    = body.monthly_spend or ""

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id, role=user.role)
    return {"token": token, "role": user.role}

# ─── LOGIN ──────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenRoleOut)
def login(
    body: LoginBody = Body(...),
    db: Session     = Depends(get_db),
):
    user = db.query(User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password"
        )

    token = create_access_token(subject=user.id, role=user.role)
    return {"token": token, "role": user.role}

# ─── PROFILE ───────────────────────────────────────────────────────────

@router.get("/profile", response_model=ProfileOut)
def profile(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the current user's basic info (including role).
    """
    return current_user