# backend/schemas/contract.py

from pydantic import BaseModel

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

