# File: backend/routes/contracts.py

import os
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import openai
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models.contract import Contract
from backend.models.user import User
from backend.schemas.contract import ContractCreate, ContractOut
from backend.utils.auth import get_current_user

router = APIRouter(
    prefix="/contracts",
    tags=["Contracts"],
)

@router.get(
    "/",
    response_model=List[ContractOut],
    summary="List my contracts",
)
def list_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return all contracts owned by the current user.
    """
    return (
        db
        .query(Contract)
        .filter(Contract.owner_id == current_user.id)
        .all()
    )

@router.post(
    "/generate",
    response_model=ContractOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new contract",
)
def generate_contract(
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a draft contract via OpenAI, save it, and associate it
    with the current user.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing OPENAI_API_KEY environment variable",
        )
    openai.api_key = openai_key

    try:
        resp = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a legal contract drafting assistant."},
                {"role": "user",   "content": data.prompt},
            ],
            temperature=0.2,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI API error: {e}",
        )

    generated_text = resp.choices[0].message.content
    new_contract = Contract(
        prompt=data.prompt,
        generated_contract=f"<div>{generated_text}</div>",
        status="draft",
        owner_id=current_user.id,
    )
    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)
    return new_contract

@router.get(
    "/{contract_id}",
    response_model=ContractOut,
    summary="Get a single contract",
)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch a single contract by ID, only if it belongs to the current user.
    """
    contract = (
        db
        .query(Contract)
        .filter(
            Contract.id == contract_id,
            Contract.owner_id == current_user.id,
        )
        .first()
    )
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )
    return contract

@router.get(
    "/{contract_id}/pdf",
    summary="Download contract as PDF",
)
def download_contract_pdf(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Render the generated_contract HTML as a PDF and stream it back,
    only if the contract belongs to the current user.
    """
    contract = (
        db
        .query(Contract)
        .filter(
            Contract.id == contract_id,
            Contract.owner_id == current_user.id,
        )
        .first()
    )
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )

    try:
        from weasyprint import HTML
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WeasyPrint unavailable or missing native libs: " + str(e),
        )

    pdf_io = BytesIO()
    HTML(string=contract.generated_contract).write_pdf(pdf_io)
    pdf_io.seek(0)
    return StreamingResponse(
        pdf_io,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="contract_{contract_id}.pdf"'
        },
    )