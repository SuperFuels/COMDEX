from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from utils.auth_guard import JWTBearer  # ✅ Your JWT bearer dependency
from utils.auth import decodeJWT         # ✅ JWT decoder
from database import get_db
from models.user import User
from schemas.user import WalletUpdate

router = APIRouter()  # ✅ Leave path prefix to main.py

@router.patch("/me/wallet", dependencies=[Depends(JWTBearer())])
def update_wallet_address(
    wallet_data: WalletUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    payload = decodeJWT(token)
    if not payload:
        raise HTTPException(status_code=403, detail="Invalid token")

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.wallet_address = wallet_data.wallet_address
    db.commit()
    db.refresh(user)
    return {"message": "✅ Wallet address updated", "wallet": user.wallet_address}

