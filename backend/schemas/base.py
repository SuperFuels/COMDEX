# backend/schemas/base.py

from pydantic import BaseModel, EmailStr

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file


# ─── User Schemas ─────────────────────────────
class UserCreate(BaseModel):
    name:     str
    email:    EmailStr
    password: str