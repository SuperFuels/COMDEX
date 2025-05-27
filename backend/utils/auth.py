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

from eth_account import Account
from eth_account.messages import encode_defunct

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

def _parse_siwe_raw(message: str) -> dict:
    """
    Minimal parser for standard EIP-4361 message:
    <domain> wants you to sign in with your Ethereum account:
    <address>

    <statement>

    URI: <uri>
    Version: <version>
    Chain ID: <chain_id>
    Nonce: <nonce>
    Issued At: <issued_at>
    """
    lines = message.splitlines()
    if len(lines) < 6:
        raise ValueError("Message too short")

    domain = lines[0].split(" wants you")[0].strip()
    address = lines[1].strip().lower()

    # grab first non-empty between address and URI:
    statement = None
    for ln in lines[2:]:
        if ln.strip() and not ln.startswith("URI:"):
            statement = ln.strip()
            break
    if not statement:
        raise ValueError("Missing statement")

    meta = {}
    for ln in lines:
        if ln.startswith("URI:"):
            meta["uri"] = ln.split("URI:",1)[1].strip()
        elif ln.startswith("Version:"):
            meta["version"] = ln.split("Version:",1)[1].strip()
        elif ln.startswith("Chain ID:"):
            meta["chain_id"] = int(ln.split("Chain ID:",1)[1].strip())
        elif ln.startswith("Nonce:"):
            meta["nonce"] = ln.split("Nonce:",1)[1].strip()
        elif ln.startswith("Issued At:"):
            meta["issued_at"] = ln.split("Issued At:",1)[1].strip()

    return {
        "domain": domain,
        "address": address,
        "statement": statement,
        **meta
    }

# ─── SIWE verification ────────────────────────────
def verify_siwe(
    message: str,
    signature: str,
    db: Session
) -> Tuple[User, str]:
    """
    1) Parse & validate raw SIWE message text
    2) Verify signature
    3) Check nonce freshness
    4) Lookup-or-create User
    5) Return (User, JWT)
    """
    # 1) parse
    try:
        parsed = _parse_siwe_raw(message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed SIWE message: {e}"
        )

    # 2) verify signature on the exact raw text
    eth_msg = encode_defunct(text=message)
    try:
        recovered = Account.recover_message(eth_msg, signature=signature)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid SIWE signature")
    if recovered.lower() != parsed["address"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Signature does not match address")

    # 3) nonce
    if not validate_nonce(parsed["nonce"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired nonce")

    # 4) user record
    user = db.query(User).filter_by(address=parsed["address"]).first()
    if not user:
        user = User(address=parsed["address"], role="buyer")
        db.add(user)
        db.commit()
        db.refresh(user)

    # 5) mint JWT
    token = create_access_token(subject=user.id, role=user.role)
    return user, token
