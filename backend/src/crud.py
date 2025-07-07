from sqlalchemy.orm import Session
from . import models, schemas

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

def update_wallet_address(db: Session, wallet_address: str, user_id: int):
    # Fetch the user by their ID (this should be passed in the request)
    user = db.query(models.User).filter(models.User.id == user_id).first()

    # If the user doesn't exist, return None or raise an exception
    if not user:
        return None

    # Update the user's wallet address
    user.wallet_address = wallet_address
    db.commit()
    db.refresh(user)  # Refresh the user object with the updated values

    return user

