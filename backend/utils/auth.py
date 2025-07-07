import os
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ─── Attempt to import eth_account; if unavailable, fall back to None ────
try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
except ImportError:
    Account = None
    encode_defunct = None

from backend.database import get_db
from backend.models.user import User

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

# ─── OAuth2 scheme ───────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ─── Token creation & retrieval ───────────────────
def create_access_token(
    subject: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    expire    = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": str(subject), "role": role, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
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
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

# ─── SIWE parsing & verification ──────────────────
def verify_siwe(
    message: str,
    signature: str,
    db: Session = Depends(get_db)
) -> Tuple[User, str]:
    """
    Validate a SIWE message + signature. Auto-provision a 'buyer' user
    if wallet_address not in DB. Returns (user, jwt_token).
    """
    if Account is None or encode_defunct is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SIWE functionality is not available on this server."
        )

    # 1) parse & recover address
    msg = encode_defunct(text=message)
    signer = Account.recover_message(msg, signature=signature).lower()

    # (optional) here you could unpack a structured SIWE JSON and validate domain, nonce, etc.

    # 2) lookup or create user
    user = db.query(User).filter_by(wallet_address=signer).first()
    if not user:
        user = User(
            name=f"{signer[:6]}…",        # placeholder
            email="",
            password_hash="",
            role="buyer",
            wallet_address=signer,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3) issue JWT
    token = create_access_token(subject=user.id, role=user.role)
    return user, token