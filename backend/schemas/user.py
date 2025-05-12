from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "buyer"  # default to 'buyer'

class WalletUpdate(BaseModel):
    wallet_address: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    wallet_address: Optional[str] = None  # Include wallet in response if available

    class Config:
        from_attributes = True  # 👈 correct for Pydantic v2

