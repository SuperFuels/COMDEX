from fastapi import APIRouter, Depends, HTTPException, Body, status
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..utils.auth import hash_password, create_access_token, verify_password

router = APIRouter(tags=["Auth"])

# Request body for registration
class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Literal["buyer", "supplier"]
    wallet_address: Optional[str] = None

# Request body for login
class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

# Response model for token + role
class TokenRoleOut(BaseModel):
    token: str
    role: str

@router.post("/register", response_model=TokenRoleOut, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterBody = Body(...),
    db: Session = Depends(get_db),
):
    # 1) prevent duplicate emails
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    # 2) optional wallet normalization
    wallet = None
    if body.wallet_address:
        from web3 import Web3
        try:
            wallet = Web3.to_checksum_address(body.wallet_address)
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid wallet address format")

    # 3) create user
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        wallet_address=wallet,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 4) issue JWT
    token = create_access_token(subject=user.id, role=user.role)
    return {"token": token, "role": user.role}

@router.post("/login", response_model=TokenRoleOut)
def login(
    body: LoginBody = Body(...),
    db: Session = Depends(get_db),
):
    # 1) find user
    user = db.query(User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    # 2) issue JWT
    token = create_access_token(subject=user.id, role=user.role)
    return {"token": token, "role": user.role}
