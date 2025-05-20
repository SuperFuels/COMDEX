# backend/utils/auth.py

import os
import time
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models.user import User

# ─── JWT configuration ──────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# ─── Password hashing context ────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── HTTP Bearer scheme ─────────────────────────────────────────────
security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    Hash a plaintext password for storage.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its bcrypt hash.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT with 'sub' set to the given subject (e.g. the user ID).
    """
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to retrieve the current user from the Bearer JWT.
    Expects the token's 'sub' claim to be the user's numeric ID.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed token: no subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(sub)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def decodeJWT(token: str) -> Optional[dict]:
    """
    Helper to decode/validate a token outside of a request context.
    Returns the payload if valid and unexpired; otherwise returns None.
    """
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # jose already checks exp, but double-check if you like:
        if decoded.get("exp", 0) >= int(time.time()):
            return decoded
    except JWTError:
        pass
    return None

