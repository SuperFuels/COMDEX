# File: backend/routes/user.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.user import WalletUpdate, UserOut
from utils.auth import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.patch(
    "/me/wallet",
    response_model=UserOut,
    summary="Update current user's wallet address"
)
def update_wallet_address(
    wallet_data: WalletUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Bind or update the wallet address on the authenticated user's profile.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    current_user.wallet_address = wallet_data.wallet_address
    db.commit()
    db.refresh(current_user)

    return current_user