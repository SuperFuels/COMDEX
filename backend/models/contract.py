# backend/models/contract.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class Contract(Base):
    __tablename__ = "contracts"

    id         = Column(Integer, primary_key=True, index=True)
    deal_id    = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    terms      = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # optional back‐reference to the Deal
    deal = relationship("Deal", back_populates="contract", uselist=False)

    def __repr__(self):
        return (
            f"<Contract("
            f"id={self.id!r}, deal_id={self.deal_id!r}, created_at={self.created_at!r}"
            f")>"
        )