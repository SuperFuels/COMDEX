# backend/utils/auth.py

import os
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models.user import User

# ─── JWT configuration ───────────────────────────
SECRET_KEY                  = os.getenv("SECRET_KEY", "super-secret-123")
ALGORITHM                   = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# ─── Password hashing ─────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ─── SIWE nonces ──────────────────────────────────
_NONCE_STORE: dict[str, float] = {}
NONCE_TTL = 5 * 60  # 5 minutes

def generate_nonce() -> str:
    nonce = secrets.token_urlsafe(16)
    _NONCE_STORE[nonce] = time.time()
    return nonce

def validate_nonce(nonce: str) -> bool:
    ts = _NONCE_STORE.pop(nonce, None)
    return ts is not None and (time.time() - ts) < NONCE_TTL

# ─── HTTP Bearer scheme ──────────────────────────
security = HTTPBearer()

def create_access_token(
    subject: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    expire    = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": str(subject), "role": role, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub     = payload.get("sub")
        if sub is None:
            raise ValueError("Missing subject")
        user_id = int(sub)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user

# ─── SIWE verification ────────────────────────────
def verify_siwe(
    message: str,
    signature: str,
    db: Session
) -> Tuple[User, str]:
    """
    1) Parse & validate EIP-4361 SIWE message
    2) Check signature & nonce
    3) Lookup-or-create User
    4) Return (User, JWT)
    """
    from siwe import SiweMessage  # avoid circular import

    # 1) parse the raw EIP-4361 text using the library helper
    try:
        siwe = SiweMessage.parse_message(message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed SIWE message: {e}"
        )

    # 2a) verify the Ethereum signature
    if not siwe.verify(signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid SIWE signature")

    # 2b) check that the nonce is fresh
    if not validate_nonce(siwe.nonce):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired nonce")

    # 3) lookup-or-create the User
    address = siwe.address.lower()
    user = db.query(User).filter_by(address=address).first()
    if not user:
        user = User(address=address, role="buyer")  # default to buyer
        db.add(user)
        db.commit()
        db.refresh(user)

    # 4) mint a JWT for this user
    token = create_access_token(subject=user.id, role=user.role)
    return user, token