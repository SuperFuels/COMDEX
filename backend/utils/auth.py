# backend/utils/auth.py

import os
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models.user import User

# ─── JWT configuration ───────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# ─── SIWE nonces ──────────────────────────────────
_NONCE_STORE: dict[str, float] = {}  # simple in-memory: nonce -> timestamp
NONCE_TTL = 5 * 60  # 5 minutes

# ─── Password hashing context ─────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── HTTP Bearer scheme ──────────────────────────
security = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


get_password_hash = hash_password  # alias


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": str(subject), "role": role, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise ValueError()
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


def decodeJWT(token: str) -> Optional[dict]:
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if decoded.get("exp", 0) >= int(time.time()):
            return decoded
    except JWTError:
        pass
    return None


# ─── SIWE / wallet-auth helpers ───────────────────

def generate_nonce() -> str:
    """Create a cryptographically secure nonce and store its timestamp."""
    nonce = secrets.token_urlsafe(16)
    _NONCE_STORE[nonce] = time.time()
    return nonce


def validate_nonce(nonce: str) -> bool:
    ts = _NONCE_STORE.pop(nonce, None)
    return ts is not None and (time.time() - ts) < NONCE_TTL


def verify_siwe(message: str, signature: str, db: Session) -> tuple[User, str]:
    """
    Given a raw SIWE message string and its signature, verify it, then
    lookup-or-create the User and return (User, role).
    """
    from siwe import SiweMessage  # pip install python-siwe

    siwe = SiweMessage(message)
    if not siwe.verify(signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid SIWE signature")

    if not validate_nonce(siwe.nonce):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired nonce")

    address = siwe.address.lower()
    # lookup or create user
    user = db.query(User).filter_by(address=address).first()
    if not user:
        user = User(address=address, role="buyer")  # default role
        db.add(user)
        db.commit()
        db.refresh(user)

    # return user + JWT token
    token = create_access_token(subject=user.id, role=user.role)
    return user, token
