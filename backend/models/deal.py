from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.database import Base, engine, get_db

# ✅ Import Shipment early to resolve relationship()
from backend.models.shipment import Shipment  # Make sure this path is correct

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = { "extend_existing": True }

    id          = Column(Integer, primary_key=True, index=True)
    product_id  = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    buyer_id    = Column(Integer, ForeignKey("users.id",   ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("users.id",   ondelete="CASCADE"), nullable=False, index=True)

    # ─── New fields for volumes & price-history ─────────────────────────────
    quantity_kg = Column(Float, nullable=False, default=0.0)
    total_price = Column(Float, nullable=False, default=0.0)

    # ─── Existing price/status/timestamps ──────────────────────────────────
    price       = Column(Float,   nullable=False)  # e.g. per-kg price
    status      = Column(String,  nullable=False, server_default="pending")
    created_at  = Column(DateTime, nullable=False, default=datetime.utcnow)

    # ─── ORM relationships ────────────────────────────────────────────────
    product    = relationship("Product",  back_populates="deals")
    buyer      = relationship("User",     back_populates="buyer_deals",    foreign_keys=[buyer_id])
    supplier   = relationship("User",     back_populates="supplier_deals", foreign_keys=[supplier_id])
    contract   = relationship("Contract", back_populates="deal", uselist=False)

    # <-── reciprocal side of Shipment⇄Deal
    shipments  = relationship(
        "Shipment",
        back_populates="deal",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
        return (
            f"<Deal("
            f"id={self.id!r}, product_id={self.product_id!r}, "
            f"buyer_id={self.buyer_id!r}, supplier_id={self.supplier_id!r}, "
            f"quantity_kg={self.quantity_kg!r}, total_price={self.total_price!r}, "
            f"price={self.price!r}, status={self.status!r}"
            f")>"
        )