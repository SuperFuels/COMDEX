# backend/models/contract.py

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base

class Contract(Base):
    __tablename__ = "contracts"

    id                 = Column(Integer, primary_key=True, index=True)
    prompt             = Column(Text, nullable=False)
    generated_contract = Column(Text, nullable=False)
    status             = Column(String, default="draft")
    pdf_url            = Column(String, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<Contract("
            f"id={self.id!r}, status={self.status!r}, created_at={self.created_at!r}"
            f")>"
        )

