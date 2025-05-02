from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from utils.auth_guard import JWTBearer  # JWT bearer dependency for authentication
from utils.auth import decodeJWT  # JWT decoder
from database import get_db
from models.user import User
from schemas.user import WalletUpdate  # Schema to update the wallet address

router = APIRouter()

# ✅ PATCH endpoint to bind wallet address to the user's profile
@router.patch("/me/wallet", dependencies=[Depends(JWTBearer())])
def update_wallet_address(
    wallet_data: WalletUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())  # Get the JWT token from request
):
    # Decode the JWT token to get the user information
    payload = decodeJWT(token)
    if not payload:
        raise HTTPException(status_code=403, detail="Invalid token")

    # Fetch the user from the database using the decoded email (subject)
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update the user's wallet address
    user.wallet_address = wallet_data.wallet_address
    db.commit()
    db.refresh(user)

    return {"message": "✅ Wallet address updated", "wallet": user.wallet_address}

