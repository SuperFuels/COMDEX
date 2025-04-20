from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    
    buyer_email = Column(String, nullable=False)
    supplier_email = Column(String, nullable=False)
    product_title = Column(String, nullable=False)

    quantity_kg = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String, default="negotiation")
    pdf_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Foreign keys
    product_id = Column(Integer, ForeignKey("products.id"))
    buyer_id = Column(Integer, ForeignKey("users.id"))
    supplier_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    product = relationship("Product", back_populates="deals")

    buyer = relationship(
        "User",
        back_populates="buyer_deals",
        foreign_keys=[buyer_id]
    )

    supplier = relationship(
        "User",
        back_populates="supplier_deals",
        foreign_keys=[supplier_id]
    )

    def __repr__(self):
        return f"<Deal(id={self.id}, buyer_email={self.buyer_email}, supplier_email={self.supplier_email}, product_title={self.product_title})>"

