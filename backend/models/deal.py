from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    buyer_email = Column(String, nullable=False)
    supplier_email = Column(String, nullable=False)
    product_title = Column(String, nullable=False)
    quantity_kg = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    # Relationship to link the deal with the product
    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product", back_populates="deals")

    # Relationship to link the deal with the user (buyer)
    buyer_id = Column(Integer, ForeignKey("users.id"))
    buyer = relationship(
        "User",
        back_populates="buyer_deals",
        foreign_keys=[buyer_id]
    )

    # Relationship to link the deal with the user (supplier)
    supplier_id = Column(Integer, ForeignKey("users.id"))
    supplier = relationship(
        "User",
        back_populates="supplier_deals",
        foreign_keys=[supplier_id]
    )

    def __repr__(self):
        return f"<Deal(id={self.id}, buyer_email={self.buyer_email}, supplier_email={self.supplier_email}, product_title={self.product_title})>"

