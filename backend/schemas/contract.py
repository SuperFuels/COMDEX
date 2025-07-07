# backend/schemas/contract.py

from pydantic import BaseModel

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class ContractCreate(BaseModel):
    prompt: str

class ContractOut(BaseModel):
    id: int
    prompt: str
    generated_contract: str   # HTML or Markdown
    status: str
    pdf_url: str | None = None

    class Config:
        orm_mode = True

