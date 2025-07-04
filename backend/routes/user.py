# File: backend/routes/user.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models.user import User
from backend.schemas.user import WalletUpdate, UserOut, UserCreate
from backend.utils.auth import get_current_user

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

# Optional future endpoint example:
# @router.post("/", response_model=UserOut)
# def create_user(
#     user_data: UserCreate,
#     db: Session = Depends(get_db)
# ):
#     """
#     Admin-only: Create a new user manually.
#     """
#     new_user = User(
#         name=user_data.name,
#         email=user_data.email,
#         password_hash=hash_password(user_data.password),
#         role=user_data.role,
#         wallet_address=user_data.wallet_address,
#         business_name=user_data.business_name,
#         address=user_data.address,
#         delivery_address=user_data.delivery_address,
#         products=user_data.products,
#         monthly_spend=user_data.monthly_spend
#     )
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
#     return new_user