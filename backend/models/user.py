from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base
from models.deal import Deal  # Required for foreign_keys references

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="user")  # buyer, supplier, admin
    wallet_address = Column(String, nullable=True)  # 🦊 MetaMask wallet address

    # Deals where the user is the buyer
    buyer_deals = relationship(
        "Deal",
        back_populates="buyer",
        foreign_keys="[Deal.buyer_id]",
        cascade="all, delete-orphan"
    )

    # Deals where the user is the supplier
    supplier_deals = relationship(
        "Deal",
        back_populates="supplier",
        foreign_keys="[Deal.supplier_id]",
        cascade="all, delete-orphan"
    )

    # Products owned by the user (if supplier)
    products = relationship(
        "Product",
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email}, role={self.role})>"

