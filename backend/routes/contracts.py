# backend/routes/contracts.py

import os
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openai import OpenAI
from weasyprint import HTML

from database import get_db
from models.contract import Contract
from schemas.contract import ContractCreate, ContractOut
from utils.auth import get_current_user
from models.user import User

router = APIRouter(tags=["Contracts"])

# ─── Configure OpenAI client ──────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

client = OpenAI(api_key=OPENAI_API_KEY)


@router.get(
    "/", 
    response_model=List[ContractOut], 
    summary="List all contracts"
)
def list_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return all contracts the current user can see.
    """
    return db.query(Contract).all()


@router.post(
    "/generate",
    response_model=ContractOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new contract"
)
def generate_contract(
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a draft contract via OpenAI and save it to the database.
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a legal contract drafting assistant. Generate clear, concise, and professional contract text based on the user prompt."},
                {"role": "user", "content": data.prompt},
            ],
            temperature=0.2,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI API error: {e}"
        )

    generated_text = resp.choices[0].message.content
    new_contract = Contract(
        prompt=data.prompt,
        generated_contract=f"<div>{generated_text}</div>",
        status="draft",
    )
    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)
    return new_contract


@router.get(
    "/{contract_id}",
    response_model=ContractOut,
    summary="Get a single contract"
)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch a previously generated contract by ID.
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found."
        )
    return contract


@router.get(
    "/{contract_id}/pdf",
    summary="Download contract as PDF"
)
def download_contract_pdf(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Render the generated_contract HTML as a PDF and stream it back.
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found."
        )

    pdf_io = BytesIO()
    HTML(string=contract.generated_contract).write_pdf(pdf_io)
    pdf_io.seek(0)

    return StreamingResponse(
        pdf_io,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=contract_{contract_id}.pdf"
        },
    )

